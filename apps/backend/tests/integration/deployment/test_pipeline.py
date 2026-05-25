"""Full deployment pipeline simulation — no real providers or SSH."""

from unittest.mock import patch

import pytest

from app.services import deployment_states as st
from app.services.deployment_events import list_events
from app.services.provision import run_provision
from tests.mocks.providers import MockProvider
from tests.mocks.ssh import MockSSHClient, mock_wait_for_ssh, set_ssh_config


@pytest.mark.asyncio
async def test_full_provision_pipeline_simulation(db_session, deployment_row):
    set_ssh_config(ssh_ready=True, health_ok=True)
    provider = MockProvider()

    with (
        patch("app.services.provision.get_provider", return_value=provider),
        patch("app.services.provision.wait_for_ssh", mock_wait_for_ssh),
        patch("app.services.provision.SSHClient", MockSSHClient),
        patch("app.services.provision._verify_openclaw_health", return_value=True),
    ):
        result = await run_provision(db_session, deployment_row.id)
        await db_session.commit()

    assert result.provision_state == st.COMPLETED
    assert result.ip_address == "203.0.113.10"
    assert result.provider_server_id == "mock-1"

    events = await list_events(db_session, deployment_row.id)
    steps = {e.step for e in events}
    assert "creating_server" in steps or "queued" in steps
    assert "completed" in steps or any(e.step == "completed" for e in events)


@pytest.mark.asyncio
async def test_resume_after_interrupted_hardening(db_session, deployment_row):
    """Simulate failure mid-pipeline then resume from WAITING_FOR_SSH."""
    set_ssh_config(ssh_ready=True, health_ok=True)
    deployment_row.provider_server_id = "mock-1"
    deployment_row.ip_address = "203.0.113.10"
    deployment_row.provision_state = st.WAITING_FOR_SSH
    deployment_row.status = "hardening"
    await db_session.flush()

    with (
        patch("app.services.provision.get_provider", return_value=MockProvider()),
        patch("app.services.provision.wait_for_ssh", mock_wait_for_ssh),
        patch("app.services.provision.SSHClient", MockSSHClient),
        patch("app.services.provision._verify_openclaw_health", return_value=True),
    ):
        result = await run_provision(db_session, deployment_row.id)
        await db_session.commit()

    assert result.provision_state == st.COMPLETED
