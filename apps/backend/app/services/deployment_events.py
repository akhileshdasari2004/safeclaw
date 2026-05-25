"""Persistent deployment events — DB storage + live SSE broadcast."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment
from app.models.deployment_event import DeploymentEvent
from app.services import deployment_states as st
from app.services.deployment_logs import DeploymentLogEvent, log_broadcaster

DEFAULT_REPLAY_LIMIT = 500


def new_correlation_id() -> str:
    return f"dep-{secrets.token_hex(8)}"


async def transition_state(
    db: AsyncSession,
    deployment: Deployment,
    new_state: str,
    message: str,
    *,
    level: str = "INFO",
    metadata: dict[str, Any] | None = None,
) -> DeploymentEvent:
    """Persist provision state transition + legacy status + event."""
    deployment.provision_state = new_state
    deployment.status = st.legacy_status(new_state)
    return await emit(
        db,
        deployment,
        step=new_state.lower(),
        message=message,
        level=level,
        status=deployment.status,
        metadata={**(metadata or {}), "provision_state": new_state},
    )


async def ensure_correlation_id(deployment: Deployment) -> str:
    if not deployment.correlation_id:
        deployment.correlation_id = new_correlation_id()
    return deployment.correlation_id


async def emit(
    db: AsyncSession,
    deployment: Deployment,
    *,
    step: str,
    message: str,
    level: str = "INFO",
    status: str | None = None,
    metadata: dict[str, Any] | None = None,
    terminal: bool = False,
) -> DeploymentEvent:
    """Persist event, append legacy logs text, and broadcast to SSE subscribers."""
    correlation_id = await ensure_correlation_id(deployment)
    if status:
        deployment.status = status
        metadata = {**(metadata or {}), "status": status}

    row = DeploymentEvent(
        deployment_id=deployment.id,
        correlation_id=correlation_id,
        timestamp=datetime.now(timezone.utc),
        level=level,
        step=step,
        message=message[:8000],
        metadata_json=metadata,
    )
    db.add(row)
    await db.flush()

    log_event = DeploymentLogEvent(
        event_id=str(row.id),
        timestamp=row.timestamp.isoformat(),
        deployment_id=str(deployment.id),
        correlation_id=correlation_id,
        level=level,
        step=step,
        message=message[:8000],
    )
    await log_broadcaster.publish_event(log_event, terminal=terminal)

    deployment.logs = (deployment.logs or "") + log_broadcaster.format_for_db(log_event)
    return row


async def list_events(
    db: AsyncSession,
    deployment_id: uuid.UUID,
    *,
    after_id: uuid.UUID | None = None,
    limit: int = DEFAULT_REPLAY_LIMIT,
) -> list[DeploymentEvent]:
    q = (
        select(DeploymentEvent)
        .where(DeploymentEvent.deployment_id == deployment_id)
        .order_by(DeploymentEvent.timestamp.asc())
        .limit(min(limit, 1000))
    )
    if after_id:
        anchor = await db.get(DeploymentEvent, after_id)
        if anchor and anchor.deployment_id == deployment_id:
            q = q.where(DeploymentEvent.timestamp > anchor.timestamp)
    result = await db.execute(q)
    return list(result.scalars().all())


def build_timeline(
    deployment_id: uuid.UUID,
    events: list[DeploymentEvent],
    *,
    correlation_id: str | None = None,
    current_status: str | None = None,
) -> dict:
    steps: list[dict] = []
    prev_ts: datetime | None = None
    for ev in events:
        duration_ms: int | None = None
        if prev_ts is not None:
            duration_ms = int((ev.timestamp - prev_ts).total_seconds() * 1000)
        prev_ts = ev.timestamp
        steps.append({
            "event_id": ev.id,
            "step": ev.step,
            "level": ev.level,
            "message": ev.message,
            "timestamp": ev.timestamp,
            "duration_ms": duration_ms,
            "metadata": ev.metadata_json,
        })

    total_duration_ms: int | None = None
    if len(events) >= 2:
        total_duration_ms = int(
            (events[-1].timestamp - events[0].timestamp).total_seconds() * 1000
        )

    return {
        "deployment_id": deployment_id,
        "correlation_id": correlation_id or (events[0].correlation_id if events else None),
        "status": current_status,
        "total_duration_ms": total_duration_ms,
        "step_count": len(steps),
        "steps": steps,
    }


async def hydrate_broadcaster_from_db(
    db: AsyncSession,
    deployment_id: uuid.UUID,
    *,
    after_id: uuid.UUID | None = None,
) -> int:
    """Load persisted events into in-memory SSE history (for reconnect/restart)."""
    events = await list_events(db, deployment_id, after_id=after_id)
    count = 0
    for ev in events:
        log_event = DeploymentLogEvent(
            event_id=str(ev.id),
            timestamp=ev.timestamp.isoformat(),
            deployment_id=str(deployment_id),
            correlation_id=ev.correlation_id,
            level=ev.level,
            step=ev.step,
            message=ev.message,
        )
        await log_broadcaster.publish_event(log_event, terminal=False, skip_subscribers=True)
        count += 1
    return count
