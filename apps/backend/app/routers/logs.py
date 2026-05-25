"""SSE deployment log streaming with DB-backed replay."""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.deployment import Deployment
from app.models.user import User
from app.services.deployment_events import list_events
from app.services.deployment_logs import DeploymentLogEvent, log_broadcaster
from app.utils.security import decode_token

router = APIRouter(prefix="/logs", tags=["logs"])


async def get_user_from_sse_token(
    token: str = Query(..., description="JWT access token (EventSource cannot send Authorization header)"),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == uuid.UUID(sub)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def _row_to_log_event(deployment_id: uuid.UUID, ev) -> DeploymentLogEvent:
    return DeploymentLogEvent(
        event_id=str(ev.id),
        timestamp=ev.timestamp.isoformat(),
        deployment_id=str(deployment_id),
        correlation_id=ev.correlation_id,
        level=ev.level,
        step=ev.step,
        message=ev.message,
    )


@router.get("/{deployment_id}/stream")
async def stream_deployment_logs(
    deployment_id: uuid.UUID,
    user: User = Depends(get_user_from_sse_token),
    db: AsyncSession = Depends(get_db),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    last_event_id_query: str | None = Query(default=None, alias="last_event_id"),
) -> StreamingResponse:
    result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.user_id == user.id,
        )
    )
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    resume_after: uuid.UUID | None = None
    resume_token = last_event_id or last_event_id_query
    if resume_token:
        try:
            resume_after = uuid.UUID(resume_token)
        except ValueError:
            pass

    await log_broadcaster.ensure_stream(deployment_id)
    if deployment.status in ("completed", "failed"):
        await log_broadcaster.mark_terminal(deployment_id)

    async def event_generator():
        yield f"event: connected\ndata: {json.dumps({'deployment_id': str(deployment_id), 'correlation_id': deployment.correlation_id})}\n\n"

        persisted = await list_events(db, deployment_id, after_id=resume_after)
        for ev in persisted:
            if ev.step == "heartbeat":
                continue
            yield _row_to_log_event(deployment_id, ev).to_sse("log")

        try:
            async for event in log_broadcaster.subscribe(
                deployment_id,
                replay=False,
                last_event_id=resume_token,
            ):
                if event.step == "heartbeat":
                    yield event.to_sse("heartbeat")
                else:
                    yield event.to_sse("log")
            yield f"event: close\ndata: {json.dumps({'deployment_id': str(deployment_id)})}\n\n"
        except asyncio.CancelledError:
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
