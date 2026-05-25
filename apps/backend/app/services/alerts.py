"""Cost alert engine — hourly polling, cooldown, email notifications."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.alert import Alert
from app.models.deployment import Deployment
from app.models.user import User
from app.providers.factory import get_provider
from app.services.email_service import send_cost_alert_email
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def poll_cost_alerts(db: AsyncSession) -> int:
    """Check all enabled alerts; return count of notifications sent."""
    settings = get_settings()
    cooldown = timedelta(hours=settings.alert_cooldown_hours)
    now = datetime.now(timezone.utc)
    sent = 0

    result = await db.execute(
        select(Alert)
        .where(Alert.enabled.is_(True))
        .options(selectinload(Alert.user))
    )
    alerts = result.scalars().all()

    for alert in alerts:
        if alert.last_triggered_at and (now - alert.last_triggered_at) < cooldown:
            continue

        user: User = alert.user
        spend = await _estimate_user_spend(db, user.id)
        if spend <= float(alert.threshold):
            continue

        send_cost_alert_email(user.email, spend, float(alert.threshold))
        alert.last_triggered_at = now
        sent += 1
        logger.info(
            "cost_alert_sent",
            user_id=str(user.id),
            spend=spend,
            threshold=float(alert.threshold),
        )

    await db.flush()
    return sent


async def _estimate_user_spend(db: AsyncSession, user_id) -> float:
    result = await db.execute(
        select(Deployment).where(
            Deployment.user_id == user_id,
            Deployment.status == "running",
        )
    )
    deployments = result.scalars().all()
    total = Decimal("0")
    for d in deployments:
        if d.monthly_cost:
            total += d.monthly_cost
    return float(total)


async def poll_provider_account_spend() -> dict[str, float]:
    """Optional provider-level billing check."""
    spends: dict[str, float] = {}
    for name in ("hetzner", "digitalocean"):
        try:
            provider = get_provider(name)
            spends[name] = provider.get_estimated_monthly_spend()
        except Exception as e:
            logger.warning("provider_spend_check_failed", provider=name, error=str(e))
    return spends
