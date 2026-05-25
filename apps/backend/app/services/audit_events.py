"""Structured audit event persistence."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent


async def record_audit_event(
    db: AsyncSession,
    action: str,
    *,
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    row = AuditEvent(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        correlation_id=correlation_id,
        request_id=request_id,
        ip_address=ip_address,
        metadata_json=metadata,
    )
    db.add(row)
    await db.flush()
    return row
