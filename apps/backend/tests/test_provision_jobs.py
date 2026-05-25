"""Provision job queue tests."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.deployment import Deployment
from app.services.provision_jobs import (
    STATUS_COMPLETED,
    STATUS_PENDING,
    enqueue_provision_job,
    execute_provision_job,
    process_pending_jobs,
)


@pytest.mark.asyncio
async def test_enqueue_and_process_job(db_session, test_user):
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="job-test",
        status="queued",
        provision_state="QUEUED",
        logs="SSH_PUBLIC_KEY:ssh-rsa test\n",
    )
    db_session.add(dep)
    await db_session.flush()

    job = await enqueue_provision_job(db_session, dep.id)
    assert job.status == STATUS_PENDING

    with patch("app.services.provision.run_provision", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = dep
        await execute_provision_job(db_session, job)

    assert job.status == STATUS_COMPLETED


@pytest.mark.asyncio
async def test_process_pending_jobs(db_session, test_user):
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="pending-job",
        status="queued",
        provision_state="QUEUED",
    )
    db_session.add(dep)
    await db_session.flush()
    await enqueue_provision_job(db_session, dep.id)
    await db_session.commit()

    with patch("app.services.provision_jobs.execute_provision_job", new_callable=AsyncMock) as mock_exec:
        n = await process_pending_jobs(db_session)
        assert n == 1
        mock_exec.assert_called_once()
