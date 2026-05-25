"""Incident management API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.schemas.incident import IncidentResponse
from app.services.incidents import list_user_incidents, resolve_incident

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentResponse])
async def get_incidents(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
) -> list[IncidentResponse]:
    rows = await list_user_incidents(db, user.id, status=status)
    return [IncidentResponse.model_validate(r) for r in rows]


@router.post("/{incident_id}/resolve", response_model=IncidentResponse)
async def resolve_incident_endpoint(
    incident_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    from sqlalchemy import select
    from app.models.incident_event import IncidentEvent

    result = await db.execute(
        select(IncidentEvent).where(
            IncidentEvent.id == incident_id,
            IncidentEvent.user_id == user.id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")
    try:
        resolved = await resolve_incident(db, incident_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return IncidentResponse.model_validate(resolved)
