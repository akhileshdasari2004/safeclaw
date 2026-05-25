"""Deployment recovery — resume, rollback, orphan cleanup."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment
from app.providers.factory import get_provider
from app.services import deployment_events as events
from app.services import deployment_states as st
from app.utils.logging import get_logger

logger = get_logger(__name__)

STUCK_AFTER_HOURS = 2
MAX_AUTO_RETRIES = 5


async def resume_deployment(
    db: AsyncSession,
    deployment_id: uuid.UUID,
    ssh_private_key_pem: str | None = None,
) -> Deployment:
    """Continue provisioning from last persisted provision_state."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise ValueError("Deployment not found")

    if deployment.provision_state in st.TERMINAL_STATES and deployment.provision_state != st.FAILED:
        raise ValueError(f"Cannot resume deployment in state {deployment.provision_state}")

    if deployment.provision_state not in st.RESUMABLE_STATES:
        raise ValueError(f"State {deployment.provision_state} is not resumable")

    if deployment.retry_count >= MAX_AUTO_RETRIES:
        raise ValueError("Maximum retry attempts exceeded")

    deployment.retry_count += 1
    deployment.error_message = None

    if deployment.provision_state == st.FAILED:
        # Resume from last incomplete step inferred from server presence
        if deployment.provider_server_id and deployment.ip_address:
            if not deployment.provision_state or deployment.provision_state == st.FAILED:
                deployment.provision_state = st.WAITING_FOR_SSH
        else:
            deployment.provision_state = st.QUEUED

    await events.transition_state(
        db,
        deployment,
        deployment.provision_state,
        f"Resuming deployment (attempt {deployment.retry_count})",
        metadata={"retry_count": deployment.retry_count},
    )
    await db.flush()

    from app.services.provision import run_provision

    return await run_provision(db, deployment_id, ssh_private_key_pem)


async def rollback_deployment(
    db: AsyncSession,
    deployment_id: uuid.UUID,
) -> Deployment:
    """Delete cloud server and mark deployment rolled back."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise ValueError("Deployment not found")

    await events.transition_state(db, deployment, st.ROLLING_BACK, "Starting rollback — removing cloud resources")

    if deployment.provider_server_id:
        try:
            provider = get_provider(deployment.provider)
            loop_import = __import__("asyncio").get_event_loop()
            await loop_import.run_in_executor(
                None,
                lambda: provider.delete_server(deployment.provider_server_id),
            )
            await events.emit(
                db,
                deployment,
                step="rolling_back",
                message=f"Deleted provider server {deployment.provider_server_id}",
            )
        except Exception as e:
            await events.emit(
                db,
                deployment,
                step="rolling_back",
                message=f"Rollback delete warning: {e}",
                level="WARN",
            )

    deployment.provider_server_id = None
    deployment.ip_address = None
    deployment.provision_state = st.ROLLED_BACK
    deployment.status = st.legacy_status(st.ROLLED_BACK)
    deployment.error_message = "Rolled back by user"
    await events.emit(
        db,
        deployment,
        step="rolled_back",
        message="Deployment rolled back",
        status=deployment.status,
        terminal=True,
    )
    await db.flush()
    return deployment


async def recover_orphaned_resources(db: AsyncSession) -> list[uuid.UUID]:
    """
    Mark long-stuck in-progress deployments as FAILED so operators can resume/rollback.
    Called on worker tick / app startup.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=STUCK_AFTER_HOURS)
    active_states = [
        st.CREATING_SERVER,
        st.WAITING_FOR_SSH,
        st.HARDENING,
        st.INSTALLING_DOCKER,
        st.INSTALLING_OPENCLAW,
        st.VERIFYING,
    ]
    result = await db.execute(
        select(Deployment).where(
            Deployment.provision_state.in_(active_states),
            Deployment.updated_at < cutoff,
        )
    )
    recovered: list[uuid.UUID] = []
    for dep in result.scalars().all():
        dep.provision_state = st.FAILED
        dep.status = st.legacy_status(st.FAILED)
        dep.error_message = "Marked failed: provisioning stalled (orphan recovery)"
        await events.emit(
            db,
            dep,
            step="failed",
            message=dep.error_message,
            level="WARN",
            status="failed",
            metadata={"recovered_orphan": True},
        )
        recovered.append(dep.id)
        logger.warning("orphan_deployment_recovered", deployment_id=str(dep.id))
    if recovered:
        await db.flush()
    return recovered
