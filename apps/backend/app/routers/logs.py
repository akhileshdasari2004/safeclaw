"""SSE deployment log streaming."""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.deployment import Deployment
from app.models.user import User
from app.services.deployment_logs import log_broadcaster
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


async def _seed_history_from_db(deployment: Deployment) -> None:
    """One-time hydration of in-memory history from persisted logs."""
    dep_id = deployment.id
    state = await log_broadcaster.ensure_stream(dep_id)
    if state.history:
        return
    if not deployment.logs:
        return
    for line in deployment.logs.split("\n"):
        if not line.strip() or line.startswith("SSH_PUBLIC_KEY:"):
            continue
        await log_broadcaster.publish(
            dep_id,
            level="INFO",
            step="historical",
            message=line.strip()[:2000],
        )


@router.get("/{deployment_id}/stream")
async def stream_deployment_logs(
    deployment_id: uuid.UUID,
    user: User = Depends(get_user_from_sse_token),
    db: AsyncSession = Depends(get_db),
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

    await _seed_history_from_db(deployment)

    if deployment.status in ("completed", "failed"):
        await log_broadcaster.mark_terminal(deployment_id)

    async def event_generator():
        yield f"event: connected\ndata: {json.dumps({'deployment_id': str(deployment_id)})}\n\n"
        try:
            async for event in log_broadcaster.subscribe(deployment_id, replay=True):
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
