"""Core provisioning engine — VPS create, SSH harden, Docker, OpenClaw."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.deployment import Deployment
from app.providers.factory import get_provider
from app.services.ssh_client import SSHClient, wait_for_ssh
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _append_log(deployment: Deployment, message: str) -> None:
    from datetime import datetime, timezone

    line = f"[{datetime.now(timezone.utc).isoformat()}] {message}\n"
    deployment.logs = (deployment.logs or "") + line


async def run_provision(
    db: AsyncSession,
    deployment_id: uuid.UUID,
    ssh_private_key_pem: str | None = None,
) -> Deployment:
    settings = get_settings()
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    if not deployment:
        raise ValueError("Deployment not found")

    provider = get_provider(deployment.provider)
    rollback_server_id: str | None = None

    try:
        deployment.status = "provisioning"
        _append_log(deployment, "Creating VPS via cloud provider API...")
        await db.flush()

        loop = asyncio.get_event_loop()
        # Provider SDK calls are sync — run in executor
        public_key = _extract_public_key_from_request(deployment)
        if not public_key:
            raise RuntimeError("SSH public key required for provisioning")

        server = await loop.run_in_executor(
            None,
            lambda: provider.create_server(
                name=deployment.server_name,
                region=deployment.region,
                plan_id=deployment.plan_id or "cx22",
                ssh_public_key=public_key,
            ),
        )

        deployment.provider_server_id = server.server_id
        deployment.ip_address = server.ip_address
        deployment.monthly_cost = Decimal(str(server.monthly_cost_usd))
        rollback_server_id = server.server_id
        _append_log(deployment, f"VPS ready at {server.ip_address}")
        await db.flush()

        deployment.status = "hardening"
        _append_log(deployment, "Waiting for SSH...")
        await db.flush()

        ssh_ready = await loop.run_in_executor(
            None,
            lambda: wait_for_ssh(server.ip_address, max_wait=300, interval=settings.provision_poll_interval),
        )
        if not ssh_ready:
            raise RuntimeError("SSH port not reachable within timeout")

        _append_log(deployment, "SSH available — starting hardening")
        await loop.run_in_executor(
            None,
            lambda: _ssh_provision(
                server.ip_address,
                ssh_private_key_pem,
                deployment,
            ),
        )

        deployment.status = "running"
        _append_log(deployment, "Deployment complete — OpenClaw is running")
        deployment.error_message = None
        await db.flush()
        logger.info("provision_complete", deployment_id=str(deployment_id))
        return deployment

    except Exception as e:
        logger.exception("provision_failed", deployment_id=str(deployment_id), error=str(e))
        deployment.status = "failed"
        deployment.error_message = str(e)[:2000]
        _append_log(deployment, f"FAILED: {e}")
        await db.flush()

        if rollback_server_id:
            try:
                await loop.run_in_executor(None, lambda: provider.delete_server(rollback_server_id))
                _append_log(deployment, "Rolled back cloud server after failure")
            except Exception as rb_err:
                _append_log(deployment, f"Rollback warning: {rb_err}")
            await db.flush()
        raise


def _extract_public_key_from_request(deployment: Deployment) -> str | None:
    """Public key stored in logs metadata during create — see deploy router."""
    if deployment.logs and "SSH_PUBLIC_KEY:" in deployment.logs:
        for line in deployment.logs.split("\n"):
            if line.startswith("SSH_PUBLIC_KEY:"):
                return line.split(":", 1)[1].strip()
    return None


def _ssh_provision(
    ip: str,
    private_key_pem: str | None,
    deployment: Deployment,
) -> None:
    settings = get_settings()
    ssh = SSHClient(host=ip, username="root", private_key_pem=private_key_pem)
    ssh.connect()
    try:
        log = ssh.upload_and_run_script("harden-ubuntu.sh", {"SAFECLAW_USER": "safeclaw"})
        _append_log(deployment, log)

        deployment.status = "installing"
        _append_log(deployment, "Installing Docker...")
        log = ssh.upload_and_run_script("install-docker.sh")
        _append_log(deployment, log)

        _append_log(deployment, "Installing OpenClaw...")
        log = ssh.upload_and_run_script(
            "install-openclaw.sh",
            {
                "OPENCLAW_IMAGE": settings.openclaw_image,
                "OPENCLAW_PORT": str(settings.openclaw_port),
            },
        )
        _append_log(deployment, log)
    finally:
        ssh.close()
