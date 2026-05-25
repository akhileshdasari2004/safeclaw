"""Deployment event history and timeline APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.deployment import Deployment
from app.schemas.deployment_event import (
    DeploymentEventResponse,
    DeploymentTimelineResponse,
    TimelineStepResponse,
)
from app.services.deployment_events import build_timeline, list_events

router = APIRouter(prefix="/deployments", tags=["deployment-events"])


async def _get_owned_deployment(
    deployment_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession,
) -> Deployment:
    result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.user_id == user.id,
        )
    )
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


@router.get("/{deployment_id}/events", response_model=list[DeploymentEventResponse])
async def get_deployment_events(
    deployment_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    after_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=1000),
) -> list[DeploymentEventResponse]:
    await _get_owned_deployment(deployment_id, user, db)
    events = await list_events(db, deployment_id, after_id=after_id, limit=limit)
    return [DeploymentEventResponse.model_validate(e) for e in events]


@router.get("/{deployment_id}/timeline", response_model=DeploymentTimelineResponse)
async def get_deployment_timeline(
    deployment_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DeploymentTimelineResponse:
    deployment = await _get_owned_deployment(deployment_id, user, db)
    events = await list_events(db, deployment_id)
    timeline = build_timeline(
        deployment_id,
        events,
        correlation_id=deployment.correlation_id,
        current_status=deployment.status,
    )
    return DeploymentTimelineResponse(
        deployment_id=timeline["deployment_id"],
        correlation_id=timeline["correlation_id"],
        status=timeline["status"],
        provision_state=deployment.provision_state,
        retry_count=deployment.retry_count or 0,
        total_duration_ms=timeline["total_duration_ms"],
        step_count=timeline["step_count"],
        steps=[TimelineStepResponse(**s) for s in timeline["steps"]],
    )
