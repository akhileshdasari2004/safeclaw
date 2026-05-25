"""Deployment failure scenario simulations."""

from unittest.mock import patch

import pytest

from app.services import deployment_states as st
from app.services.provision import run_provision
from tests.mocks.providers import MockProvider, PartialCreateProvider, RateLimitProvider, TimeoutProvider
from tests.mocks.ssh import MockSSHClient, mock_wait_for_ssh, set_ssh_config


@pytest.mark.asyncio
async def test_ssh_never_ready(db_session, deployment_row):
    set_ssh_config(ssh_ready=False)
    deployment_row.provision_state = st.CREATING_SERVER
    deployment_row.provider_server_id = "mock-1"
    deployment_row.ip_address = "203.0.113.10"
    await db_session.flush()

    with (
        patch("app.services.provision.get_provider", return_value=MockProvider()),
        patch("app.services.provision.wait_for_ssh", mock_wait_for_ssh),
        patch("app.services.provision.SSHClient", MockSSHClient),
    ):
        with pytest.raises(RuntimeError, match="SSH port not reachable"):
            await run_provision(db_session, deployment_row.id)

    assert deployment_row.provision_state == st.FAILED


@pytest.mark.asyncio
async def test_provider_timeout(db_session, deployment_row):
    with patch("app.services.provision.get_provider", return_value=TimeoutProvider()):
        with pytest.raises(TimeoutError):
            await run_provision(db_session, deployment_row.id)
    assert deployment_row.provision_state == st.FAILED


@pytest.mark.asyncio
async def test_provider_rate_limit(db_session, deployment_row):
    with patch("app.services.provision.get_provider", return_value=RateLimitProvider()):
        with pytest.raises(RuntimeError, match="429"):
            await run_provision(db_session, deployment_row.id)
    assert deployment_row.provision_state == st.FAILED


@pytest.mark.asyncio
async def test_docker_install_failure(db_session, deployment_row):
    set_ssh_config(ssh_ready=True, script_failures={"install-docker.sh"})
    deployment_row.provision_state = st.HARDENING
    deployment_row.provider_server_id = "mock-1"
    deployment_row.ip_address = "203.0.113.10"
    await db_session.flush()

    with (
        patch("app.services.provision.get_provider", return_value=MockProvider()),
        patch("app.services.provision.wait_for_ssh", mock_wait_for_ssh),
        patch("app.services.provision.SSHClient", MockSSHClient),
    ):
        with pytest.raises(RuntimeError, match="install-docker"):
            await run_provision(db_session, deployment_row.id)

    assert deployment_row.provision_state == st.FAILED


@pytest.mark.asyncio
async def test_healthcheck_failure(db_session, deployment_row):
    set_ssh_config(ssh_ready=True, health_ok=False)
    deployment_row.provision_state = st.VERIFYING
    deployment_row.provider_server_id = "mock-1"
    deployment_row.ip_address = "203.0.113.10"
    await db_session.flush()

    with (
        patch("app.services.provision.get_provider", return_value=MockProvider()),
        patch("app.services.provision.wait_for_ssh", mock_wait_for_ssh),
        patch("app.services.provision.SSHClient", MockSSHClient),
        patch("app.services.provision._verify_openclaw_health", return_value=False),
    ):
        with pytest.raises(RuntimeError, match="health check failed"):
            await run_provision(db_session, deployment_row.id)

    assert deployment_row.provision_state == st.FAILED


@pytest.mark.asyncio
async def test_provider_partial_create_no_ip(db_session, deployment_row):
    with patch("app.services.provision.get_provider", return_value=PartialCreateProvider()):
        with pytest.raises(RuntimeError, match="No server IP"):
            await run_provision(db_session, deployment_row.id)

    assert deployment_row.provision_state == st.FAILED
