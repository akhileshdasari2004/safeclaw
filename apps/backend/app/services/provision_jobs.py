"""DB-backed provision job queue."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment
from app.models.provision_job import ProvisionJob
from app.utils.logging import bind_deployment_context, get_logger

logger = get_logger(__name__)

JOB_PROVISION = "provision"
JOB_RESUME = "resume"
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
LOCK_MINUTES = 15


async def enqueue_provision_job(
    db: AsyncSession,
    deployment_id: uuid.UUID,
    job_type: str = JOB_PROVISION,
) -> ProvisionJob:
    job = ProvisionJob(
        deployment_id=deployment_id,
        job_type=job_type,
        status=STATUS_PENDING,
    )
    db.add(job)
    await db.flush()
    logger.info("provision_job_enqueued", deployment_id=str(deployment_id), job_id=str(job.id), job_type=job_type)
    return job


async def _get_private_key(deployment: Deployment) -> str | None:
    if not deployment.encrypted_ssh_private_key:
        return None
    from app.utils.security import decrypt_secret

    return decrypt_secret(deployment.encrypted_ssh_private_key)


async def execute_provision_job(db: AsyncSession, job: ProvisionJob) -> None:
    bind_deployment_context(str(job.deployment_id))
    job.status = STATUS_RUNNING
    job.started_at = datetime.now(timezone.utc)
    job.attempts += 1
    job.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCK_MINUTES)
    await db.flush()

    dep = await db.get(Deployment, job.deployment_id)
    if not dep:
        job.status = STATUS_FAILED
        job.last_error = "Deployment not found"
        job.completed_at = datetime.now(timezone.utc)
        await db.flush()
        return

    pk = await _get_private_key(dep)
    try:
        if job.job_type == JOB_RESUME:
            from app.services.deployment_recovery import resume_deployment

            await resume_deployment(db, dep.id, pk)
        else:
            from app.services.provision import run_provision

            await run_provision(db, dep.id, pk)
        job.status = STATUS_COMPLETED
        job.last_error = None
    except Exception as e:
        job.status = STATUS_FAILED if job.attempts >= job.max_attempts else STATUS_PENDING
        job.last_error = str(e)[:2000]
        if job.status == STATUS_PENDING:
            job.locked_until = datetime.now(timezone.utc) + timedelta(minutes=2**job.attempts)
        logger.warning(
            "provision_job_failed",
            job_id=str(job.id),
            deployment_id=str(job.deployment_id),
            attempt=job.attempts,
            error=str(e)[:500],
        )
    finally:
        job.completed_at = datetime.now(timezone.utc) if job.status in (STATUS_COMPLETED, STATUS_FAILED) else None
        await db.flush()


async def process_pending_jobs(db: AsyncSession, *, limit: int = 10) -> int:
    """Claim and run pending jobs not locked or past lock expiry."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ProvisionJob)
        .where(
            ProvisionJob.status == STATUS_PENDING,
            (ProvisionJob.locked_until.is_(None)) | (ProvisionJob.locked_until < now),
        )
        .order_by(ProvisionJob.scheduled_at.asc())
        .limit(limit)
    )
    jobs = list(result.scalars().all())
    for job in jobs:
        await execute_provision_job(db, job)
    if jobs:
        logger.info("provision_jobs_processed", count=len(jobs))
    return len(jobs)
