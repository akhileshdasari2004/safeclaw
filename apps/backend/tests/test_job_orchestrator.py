"""Job orchestrator maintenance tests."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.models.deployment import Deployment
from app.services import deployment_states as st
from app.services.job_orchestrator import detect_stuck_deployments, run_scheduled_maintenance


@pytest.mark.asyncio
async def test_detect_stuck_deployments(db_session, test_user):
    stale = Deployment(
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="stuck",
        provision_state=st.HARDENING,
        status="hardening",
        updated_at=datetime.now(timezone.utc) - timedelta(hours=5),
    )
    db_session.add(stale)
    await db_session.flush()

    stuck = await detect_stuck_deployments(db_session, stale_hours=2.0)
    assert len(stuck) >= 1
    assert stuck[0].server_name == "stuck"


@pytest.mark.asyncio
async def test_run_scheduled_maintenance(db_session):
    with (
        patch("app.services.job_orchestrator.recover_orphaned_resources", return_value=[]),
        patch("app.services.job_orchestrator.capture_billing_snapshots", return_value=[]),
    ):
        summary = await run_scheduled_maintenance(db_session)
    assert "orphans_recovered" in summary
    assert summary["orphans_recovered"] == 0
