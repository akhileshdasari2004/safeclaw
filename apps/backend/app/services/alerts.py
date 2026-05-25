"""Cost alert engine — APScheduler jobs, cooldown, history, provider billing."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.alert import Alert
from app.models.alert_history import AlertHistory
from app.models.deployment import Deployment
from app.models.user import User
from app.services.billing_providers import get_billing_adapters
from app.services.email_service import send_cost_alert_email
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def _estimate_user_spend(db: AsyncSession, user_id: uuid.UUID) -> float:
    result = await db.execute(
        select(Deployment).where(
            Deployment.user_id == user_id,
            Deployment.status.in_(("completed", "running")),
        )
    )
    deployments = result.scalars().all()
    total = Decimal("0")
    for d in deployments:
        if d.monthly_cost:
            total += d.monthly_cost
    return float(total)


async def _provider_spend_snapshot() -> dict[str, float]:
    spends: dict[str, float] = {}
    for adapter in get_billing_adapters():
        mtd = adapter.get_month_to_date_usd()
        if mtd is not None:
            spends[adapter.name] = mtd
    return spends


async def poll_cost_alerts(db: AsyncSession) -> int:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    sent = 0
    provider_spends = await _provider_spend_snapshot()

    result = await db.execute(
        select(Alert).where(Alert.enabled.is_(True)).options(selectinload(Alert.user))
    )
    alerts = result.scalars().all()

    for alert in alerts:
        user: User = alert.user
        cooldown = timedelta(hours=alert.cooldown_hours or settings.alert_cooldown_hours)
        if alert.last_triggered_at and (now - alert.last_triggered_at) < cooldown:
            continue

        spend = await _estimate_user_spend(db, user.id)
        # Include max provider MTD as conservative signal when higher than deployment sum
        if provider_spends:
            spend = max(spend, max(provider_spends.values()))

        if spend <= float(alert.threshold):
            continue

        # Duplicate suppression: skip if identical alert in cooldown window
        recent = await db.execute(
            select(AlertHistory)
            .where(
                AlertHistory.user_id == user.id,
                AlertHistory.alert_id == alert.id,
                AlertHistory.created_at >= now - cooldown,
            )
            .limit(1)
        )
        if recent.scalar_one_or_none():
            continue

        provider_name = max(provider_spends, key=provider_spends.get) if provider_spends else None
        send_cost_alert_email(
            user.email,
            spend,
            float(alert.threshold),
            provider=provider_name,
        )
        alert.last_triggered_at = now
        db.add(
            AlertHistory(
                user_id=user.id,
                alert_id=alert.id,
                provider=provider_name,
                current_spend=Decimal(str(round(spend, 2))),
                threshold=alert.threshold,
                message=f"Spend ${spend:.2f} exceeded threshold ${float(alert.threshold):.2f}",
            )
        )
        sent += 1
        logger.info(
            "cost_alert_sent",
            user_id=str(user.id),
            spend=spend,
            threshold=float(alert.threshold),
        )

    await db.flush()
    return sent


async def send_test_alert(db: AsyncSession, user_id: uuid.UUID, alert_id: uuid.UUID) -> dict:
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id).options(selectinload(Alert.user))
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise ValueError("Alert not found")
    spend = await _estimate_user_spend(db, user_id)
    send_cost_alert_email(
        alert.user.email,
        spend,
        float(alert.threshold),
        provider="test",
        test=True,
    )
    return {"status": "sent", "estimated_spend": spend, "threshold": float(alert.threshold)}
