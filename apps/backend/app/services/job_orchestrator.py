"""DB-backed maintenance jobs — stuck deployments, billing snapshots, queue health."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment
from app.services import deployment_states as st
from app.services.billing_snapshots import capture_billing_snapshots
from app.services.deployment_recovery import recover_orphaned_resources
from app.services.provision_jobs import process_pending_jobs
from app.utils.logging import get_logger

logger = get_logger(__name__)

ACTIVE_STATES = {
    st.QUEUED,
    st.CREATING_SERVER,
    st.WAITING_FOR_SSH,
    st.HARDENING,
    st.INSTALLING_DOCKER,
    st.INSTALLING_OPENCLAW,
    st.VERIFYING,
    st.ROLLING_BACK,
}


async def detect_stuck_deployments(
    db: AsyncSession,
    *,
    stale_hours: float = 2.0,
) -> list[Deployment]:
    """Deployments in active provision states with no recent update."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=stale_hours)
    result = await db.execute(
        select(Deployment).where(
            Deployment.provision_state.in_(tuple(ACTIVE_STATES)),
            Deployment.updated_at < cutoff,
        )
    )
    return list(result.scalars().all())


async def run_scheduled_maintenance(db: AsyncSession) -> dict:
    """
    Single scheduler entry: orphan recovery, stuck detection, billing snapshots.
    Returns summary dict for structured logs.
    """
    orphans = await recover_orphaned_resources(db)
    stuck = await detect_stuck_deployments(db)
    snapshots = await capture_billing_snapshots(db)
    jobs_run = await process_pending_jobs(db)

    summary = {
        "orphans_recovered": len(orphans),
        "stuck_detected": len(stuck),
        "billing_snapshots": len(snapshots),
        "provision_jobs_run": jobs_run,
    }
    if stuck:
        logger.warning("stuck_deployments_detected", count=len(stuck), ids=[str(d.id) for d in stuck[:10]])
    logger.info("scheduled_maintenance_complete", **summary)
    return summary
