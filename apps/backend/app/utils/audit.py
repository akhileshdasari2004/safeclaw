import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    action: str,
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    details: str | None = None,
    *,
    request_id: str | None = None,
    correlation_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    from app.services.audit_events import record_audit_event

    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        details=details,
    )
    db.add(entry)
    meta = dict(metadata or {})
    if details:
        meta["details"] = details
    await record_audit_event(
        db,
        action,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        request_id=request_id,
        correlation_id=correlation_id,
        metadata=meta or None,
    )
