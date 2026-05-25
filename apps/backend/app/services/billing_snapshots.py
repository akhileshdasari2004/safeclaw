"""Capture and validate billing snapshots against deployment inventory."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing_snapshot import BillingSnapshot
from app.models.deployment import Deployment
from app.services.billing_providers import get_billing_adapters
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Alert if provider MTD exceeds deployment sum by more than this ratio (e.g. orphaned servers)
DRIFT_RATIO_THRESHOLD = 1.25


async def sum_active_deployment_costs(db: AsyncSession) -> Decimal:
    result = await db.execute(
        select(Deployment).where(
            Deployment.status.in_(("completed", "running")),
            Deployment.monthly_cost.isnot(None),
        )
    )
    total = Decimal("0")
    for dep in result.scalars().all():
        if dep.monthly_cost:
            total += dep.monthly_cost
    return total


async def capture_billing_snapshots(db: AsyncSession) -> list[BillingSnapshot]:
    deployment_sum = await sum_active_deployment_costs(db)
    snapshots: list[BillingSnapshot] = []

    for adapter in get_billing_adapters():
        mtd = adapter.get_month_to_date_usd()
        if mtd is None:
            continue
        snap = BillingSnapshot(
            provider=adapter.name,
            month_to_date_usd=Decimal(str(round(mtd, 2))),
            deployment_sum_usd=deployment_sum,
            metadata_json={"source": adapter.__class__.__name__},
        )
        db.add(snap)
        snapshots.append(snap)

        if deployment_sum > 0 and Decimal(str(mtd)) > deployment_sum * Decimal(str(DRIFT_RATIO_THRESHOLD)):
            logger.warning(
                "billing_drift_detected",
                provider=adapter.name,
                mtd_usd=mtd,
                deployment_sum=float(deployment_sum),
            )

    if snapshots:
        await db.flush()
    return snapshots


def validate_snapshot_accuracy(
    provider_mtd: float,
    deployment_sum: float,
    *,
    tolerance_ratio: float = 1.5,
) -> bool:
    """Return True if provider spend is within expected bounds of deployment inventory."""
    if deployment_sum <= 0:
        return provider_mtd <= 0.01
    return provider_mtd <= deployment_sum * tolerance_ratio
