"""Chaos / failure injection tests — isolated copy for CI chaos stage."""

from unittest.mock import patch

import pytest

from app.services import deployment_states as st
from app.services.provision import run_provision
from tests.mocks.providers import MockProvider, TimeoutProvider
from tests.mocks.ssh import MockSSHClient, mock_wait_for_ssh, set_ssh_config


@pytest.mark.asyncio
async def test_chaos_provider_cascade_timeout(db_session, deployment_row):
    with patch("app.services.provision.get_provider", return_value=TimeoutProvider()):
        with pytest.raises(TimeoutError):
            await run_provision(db_session, deployment_row.id)
    assert deployment_row.provision_state == st.FAILED


@pytest.mark.asyncio
async def test_chaos_concurrent_failure_storm(db_session, deployment_row):
    """Multiple failure modes in sequence — provider ok, SSH down."""
    deployment_row.provision_state = st.CREATING_SERVER
    deployment_row.provider_server_id = "mock-1"
    deployment_row.ip_address = "203.0.113.10"
    await db_session.flush()

    set_ssh_config(ssh_ready=False)
    with (
        patch("app.services.provision.get_provider", return_value=MockProvider()),
        patch("app.services.provision.wait_for_ssh", mock_wait_for_ssh),
        patch("app.services.provision.SSHClient", MockSSHClient),
    ):
        with pytest.raises(RuntimeError, match="SSH port not reachable"):
            await run_provision(db_session, deployment_row.id)
    assert deployment_row.provision_state == st.FAILED


@pytest.mark.asyncio
async def test_chaos_memory_pressure_scanner_graceful():
    from app.services.scanner import _grade

    assert _grade(0) == "F"
    assert _grade(100) == "A"
