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
from app.services.deployment_logs import log_broadcaster
from app.services.ssh_client import SSHClient, wait_for_ssh
from app.utils.logging import get_logger

logger = get_logger(__name__)

ACTIVE_STATUSES = frozenset({
    "queued", "pending", "provisioning", "hardening", "installing", "verifying",
})


async def _emit(
    deployment: Deployment,
    step: str,
    message: str,
    *,
    level: str = "INFO",
    status: str | None = None,
) -> None:
    if status:
        deployment.status = status
    event = await log_broadcaster.publish(
        deployment.id,
        level=level,
        step=step,
        message=message,
    )
    deployment.logs = (deployment.logs or "") + log_broadcaster.format_for_db(event)


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

    await log_broadcaster.ensure_stream(deployment_id)
    provider = get_provider(deployment.provider)
    rollback_server_id: str | None = None

    try:
        deployment.status = "provisioning"
        await _emit(
            deployment,
            "creating_server",
            "Creating VPS via cloud provider API...",
            status="provisioning",
        )
        await db.flush()

        loop = asyncio.get_event_loop()
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
        await _emit(
            deployment,
            "creating_server",
            f"VPS ready at {server.ip_address}",
        )
        await db.flush()

        deployment.status = "hardening"
        await _emit(
            deployment,
            "waiting_for_ssh",
            "Waiting for SSH port to become reachable...",
            status="hardening",
        )
        await db.flush()

        ssh_ready = await loop.run_in_executor(
            None,
            lambda: wait_for_ssh(
                server.ip_address,
                max_wait=300,
                interval=settings.provision_poll_interval,
            ),
        )
        if not ssh_ready:
            raise RuntimeError("SSH port not reachable within timeout")

        await _emit(deployment, "waiting_for_ssh", "SSH available — starting hardening")
        ssh_log_entries = await loop.run_in_executor(
            None,
            lambda: _ssh_provision(server.ip_address, ssh_private_key_pem),
        )
        for step, message, level in ssh_log_entries:
            deployment.status = "installing" if step in ("docker_install", "openclaw_install") else "hardening"
            await _emit(deployment, step, message, level=level, status=deployment.status)

        deployment.status = "verifying"
        await _emit(
            deployment,
            "healthcheck",
            "Verifying OpenClaw container health...",
            status="verifying",
        )
        await db.flush()

        deployment.status = "completed"
        deployment.error_message = None
        await _emit(
            deployment,
            "completed",
            "Deployment complete — OpenClaw is running",
            status="completed",
        )
        await log_broadcaster.close_stream(
            deployment.id, step="completed", message="Stream closed", level="INFO"
        )
        await db.flush()
        logger.info("provision_complete", deployment_id=str(deployment_id))
        return deployment

    except Exception as e:
        logger.exception("provision_failed", deployment_id=str(deployment_id), error=str(e))
        deployment.status = "failed"
        deployment.error_message = str(e)[:2000]
        await _emit(deployment, "failed", f"Deployment failed: {e}", level="ERROR", status="failed")
        await db.flush()

        if rollback_server_id:
            try:
                await loop.run_in_executor(None, lambda: provider.delete_server(rollback_server_id))
                await _emit(deployment, "failed", "Rolled back cloud server after failure", level="WARN")
            except Exception as rb_err:
                await _emit(deployment, "failed", f"Rollback warning: {rb_err}", level="WARN")
            await db.flush()

        await log_broadcaster.close_stream(
            deployment.id, step="failed", message=str(e)[:500], level="ERROR"
        )
        raise


def _extract_public_key_from_request(deployment: Deployment) -> str | None:
    if deployment.logs and "SSH_PUBLIC_KEY:" in deployment.logs:
        for line in deployment.logs.split("\n"):
            if line.startswith("SSH_PUBLIC_KEY:"):
                return line.split(":", 1)[1].strip()
    return None


def _ssh_provision(
    ip: str,
    private_key_pem: str | None,
) -> list[tuple[str, str, str]]:
    """Returns list of (step, message, level) for async emission."""
    settings = get_settings()
    entries: list[tuple[str, str, str]] = []
    ssh = SSHClient(host=ip, username="root", private_key_pem=private_key_pem)
    ssh.connect()
    try:
        entries.append(("ufw_configuration", "Applying UFW, fail2ban, and SSH hardening...", "INFO"))
        log = ssh.upload_and_run_script("harden-ubuntu.sh", {"SAFECLAW_USER": "safeclaw"})
        entries.append(("ufw_configuration", log[:1500], "INFO"))

        entries.append(("docker_install", "Installing Docker Engine...", "INFO"))
        log = ssh.upload_and_run_script("install-docker.sh")
        entries.append(("docker_install", log[:1500], "INFO"))

        entries.append(("openclaw_install", "Installing OpenClaw container...", "INFO"))
        log = ssh.upload_and_run_script(
            "install-openclaw.sh",
            {
                "OPENCLAW_IMAGE": settings.openclaw_image,
                "OPENCLAW_PORT": str(settings.openclaw_port),
            },
        )
        entries.append(("openclaw_install", log[:1500], "INFO"))
    finally:
        ssh.close()
    return entries
