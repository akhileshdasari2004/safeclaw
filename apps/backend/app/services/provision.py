"""Core provisioning engine — resumable state-machine driven flow."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.deployment import Deployment
from app.providers.factory import get_provider
from app.services import deployment_events as events
from app.services import deployment_states as st
from app.services.deployment_logs import log_broadcaster
from app.services.deployment_events import transition_state
from app.services.ssh_client import SSHClient, wait_for_ssh
from app.utils.logging import get_logger

logger = get_logger(__name__)


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

    await events.ensure_correlation_id(deployment)
    if not deployment.provision_state or deployment.provision_state == st.FAILED:
        deployment.provision_state = (
            st.WAITING_FOR_SSH if deployment.provider_server_id and deployment.ip_address else st.QUEUED
        )
    await db.flush()
    await log_broadcaster.ensure_stream(deployment_id)

    provider = get_provider(deployment.provider)
    loop = asyncio.get_event_loop()
    server_ip: str | None = deployment.ip_address

    try:
        # --- CREATING_SERVER ---
        if not st.has_passed(deployment.provision_state, st.CREATING_SERVER):
            await transition_state(db, deployment, st.CREATING_SERVER, "Creating VPS via cloud provider API...")
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
            server_ip = server.ip_address
            await events.emit(
                db,
                deployment,
                step="creating_server",
                message=f"VPS ready at {server.ip_address}",
                metadata={"ip_address": server.ip_address, "server_id": server.server_id},
            )
            await db.flush()

        if not server_ip and deployment.ip_address:
            server_ip = deployment.ip_address
        if not server_ip:
            raise RuntimeError("No server IP available — cannot continue provisioning")

        # --- WAITING_FOR_SSH ---
        if not st.has_passed(deployment.provision_state, st.WAITING_FOR_SSH):
            await transition_state(db, deployment, st.WAITING_FOR_SSH, "Waiting for SSH port to become reachable...")
            ssh_ready = await loop.run_in_executor(
                None,
                lambda: wait_for_ssh(
                    server_ip,
                    max_wait=300,
                    interval=settings.provision_poll_interval,
                ),
            )
            if not ssh_ready:
                raise RuntimeError("SSH port not reachable within timeout")
            await events.emit(db, deployment, step="waiting_for_ssh", message="SSH available")

        # --- HARDENING ---
        if not st.has_passed(deployment.provision_state, st.HARDENING):
            await transition_state(db, deployment, st.HARDENING, "Applying security hardening (UFW, fail2ban, SSH)...")
            log = await loop.run_in_executor(
                None,
                lambda: _run_ssh_script(server_ip, ssh_private_key_pem, "harden-ubuntu.sh", {"SAFECLAW_USER": "safeclaw"}),
            )
            await events.emit(db, deployment, step="hardening", message=log[:1500])

        # --- INSTALLING_DOCKER ---
        if not st.has_passed(deployment.provision_state, st.INSTALLING_DOCKER):
            await transition_state(db, deployment, st.INSTALLING_DOCKER, "Installing Docker Engine...")
            log = await loop.run_in_executor(
                None,
                lambda: _run_ssh_script(server_ip, ssh_private_key_pem, "install-docker.sh"),
            )
            await events.emit(db, deployment, step="installing_docker", message=log[:1500])

        # --- INSTALLING_OPENCLAW ---
        if not st.has_passed(deployment.provision_state, st.INSTALLING_OPENCLAW):
            await transition_state(db, deployment, st.INSTALLING_OPENCLAW, "Installing OpenClaw container...")
            log = await loop.run_in_executor(
                None,
                lambda: _run_ssh_script(
                    server_ip,
                    ssh_private_key_pem,
                    "install-openclaw.sh",
                    {
                        "OPENCLAW_IMAGE": settings.openclaw_image,
                        "OPENCLAW_PORT": str(settings.openclaw_port),
                    },
                ),
            )
            await events.emit(db, deployment, step="installing_openclaw", message=log[:1500])

        # --- VERIFYING ---
        if not st.has_passed(deployment.provision_state, st.VERIFYING):
            await transition_state(db, deployment, st.VERIFYING, "Verifying OpenClaw container health...")
            verified = await loop.run_in_executor(
                None,
                lambda: _verify_openclaw_health(server_ip, ssh_private_key_pem, settings.openclaw_port),
            )
            if not verified:
                raise RuntimeError("OpenClaw health check failed")

        deployment.error_message = None
        await transition_state(
            db,
            deployment,
            st.COMPLETED,
            "Deployment complete — OpenClaw is running",
            metadata={"ip_address": server_ip},
        )
        await log_broadcaster.close_stream(deployment.id, step="completed", message="Stream closed", level="INFO")
        await db.flush()
        logger.info(
            "provision_complete",
            deployment_id=str(deployment_id),
            correlation_id=deployment.correlation_id,
        )
        return deployment

    except Exception as e:
        logger.exception(
            "provision_failed",
            deployment_id=str(deployment_id),
            correlation_id=deployment.correlation_id,
            error=str(e),
        )
        deployment.provision_state = st.FAILED
        deployment.status = st.legacy_status(st.FAILED)
        deployment.error_message = str(e)[:2000]
        await events.emit(
            db,
            deployment,
            step="failed",
            message=f"Deployment failed: {e}",
            level="ERROR",
            status="failed",
            metadata={"error": str(e)[:500], "provision_state": st.FAILED},
        )
        await db.flush()

        if deployment.provider_server_id:
            try:
                await loop.run_in_executor(
                    None,
                    lambda: provider.delete_server(deployment.provider_server_id),
                )
                await events.emit(
                    db,
                    deployment,
                    step="failed",
                    message="Rolled back cloud server after failure",
                    level="WARN",
                )
            except Exception as rb_err:
                await events.emit(
                    db,
                    deployment,
                    step="failed",
                    message=f"Rollback warning: {rb_err}",
                    level="WARN",
                )
            await db.flush()

        await log_broadcaster.close_stream(deployment.id, step="failed", message=str(e)[:500], level="ERROR")

        try:
            from app.services.incidents import open_provision_failure_incident

            await open_provision_failure_incident(
                db,
                deployment.id,
                deployment.user_id,
                str(e),
                correlation_id=deployment.correlation_id,
            )
        except Exception:
            logger.warning("incident_create_failed", deployment_id=str(deployment_id))

        raise


def _extract_public_key_from_request(deployment: Deployment) -> str | None:
    if deployment.logs and "SSH_PUBLIC_KEY:" in deployment.logs:
        for line in deployment.logs.split("\n"):
            if line.startswith("SSH_PUBLIC_KEY:"):
                return line.split(":", 1)[1].strip()
    return None


def _run_ssh_script(
    ip: str,
    private_key_pem: str | None,
    script_name: str,
    env: dict[str, str] | None = None,
) -> str:
    ssh = SSHClient(host=ip, username="root", private_key_pem=private_key_pem)
    ssh.connect()
    try:
        return ssh.upload_and_run_script(script_name, env)
    finally:
        ssh.close()


def _verify_openclaw_health(ip: str, private_key_pem: str | None, port: int) -> bool:
    ssh = SSHClient(host=ip, username="root", private_key_pem=private_key_pem)
    ssh.connect()
    try:
        code, out, _ = ssh.run(
            f"curl -sf http://127.0.0.1:{port}/ -o /dev/null 2>/dev/null || "
            f"curl -sf http://127.0.0.1:{port}/health -o /dev/null 2>/dev/null || "
            "docker ps --filter name=openclaw --filter status=running -q | grep -q ."
        )
        return code == 0
    finally:
        ssh.close()
