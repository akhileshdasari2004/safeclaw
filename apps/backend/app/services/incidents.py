"""Incident tracking for failed provisions and operator actions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident_event import IncidentEvent

SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"

STATUS_OPEN = "open"
STATUS_RESOLVED = "resolved"


async def open_incident(
    db: AsyncSession,
    *,
    title: str,
    description: str | None = None,
    deployment_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    severity: str = SEVERITY_MEDIUM,
    metadata: dict | None = None,
) -> IncidentEvent:
    incident = IncidentEvent(
        deployment_id=deployment_id,
        user_id=user_id,
        severity=severity,
        status=STATUS_OPEN,
        title=title,
        description=description,
        metadata_json=metadata,
    )
    db.add(incident)
    await db.flush()
    return incident


async def resolve_incident(db: AsyncSession, incident_id: uuid.UUID) -> IncidentEvent:
    incident = await db.get(IncidentEvent, incident_id)
    if not incident:
        raise ValueError("Incident not found")
    incident.status = STATUS_RESOLVED
    incident.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    return incident


async def list_user_incidents(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: str | None = None,
    limit: int = 50,
) -> list[IncidentEvent]:
    q = select(IncidentEvent).where(IncidentEvent.user_id == user_id).order_by(IncidentEvent.created_at.desc()).limit(limit)
    if status:
        q = q.where(IncidentEvent.status == status)
    result = await db.execute(q)
    return list(result.scalars().all())


async def open_provision_failure_incident(
    db: AsyncSession,
    deployment_id: uuid.UUID,
    user_id: uuid.UUID,
    error: str,
    *,
    correlation_id: str | None = None,
) -> IncidentEvent:
    return await open_incident(
        db,
        title="Provisioning failed",
        description=error[:2000],
        deployment_id=deployment_id,
        user_id=user_id,
        severity=SEVERITY_HIGH,
        metadata={"correlation_id": correlation_id, "type": "provision_failure"},
    )
