"""SSH key rotation on live deployments."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment
from app.services.audit_events import record_audit_event
from app.services.deployment_events import emit
from app.services.ssh_client import SSHClient
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _extract_public_key(deployment: Deployment) -> str | None:
    if deployment.logs and "SSH_PUBLIC_KEY:" in deployment.logs:
        for line in deployment.logs.split("\n"):
            if line.startswith("SSH_PUBLIC_KEY:"):
                return line.split(":", 1)[1].strip()
    return None


def _rotate_on_server(
    ip: str,
    private_key_pem: str,
    new_public_key: str,
    username: str = "safeclaw",
) -> str:
    """Install new authorized_keys entry for safeclaw user; keep root access via current key."""
    ssh = SSHClient(host=ip, username="root", private_key_pem=private_key_pem)
    ssh.connect()
    try:
        safeclaw_line = new_public_key.strip()
        script = f"""
set -e
id -u {username} >/dev/null 2>&1 || useradd -m -s /bin/bash {username}
install -d -m 700 -o {username} -g {username} /home/{username}/.ssh
grep -qF '{safeclaw_line[:80]}' /home/{username}/.ssh/authorized_keys 2>/dev/null || \\
  echo '{safeclaw_line}' >> /home/{username}/.ssh/authorized_keys
chown {username}:{username} /home/{username}/.ssh/authorized_keys
chmod 600 /home/{username}/.ssh/authorized_keys
echo rotated_ok
"""
        code, out, err = ssh.run(script, timeout=120)
        if code != 0 or "rotated_ok" not in out:
            raise RuntimeError(err or out or "SSH rotation script failed")
        return out.strip()
    finally:
        ssh.close()


async def rotate_deployment_ssh_keys(
    db: AsyncSession,
    deployment: Deployment,
    new_public_key: str,
    private_key_pem: str,
    *,
    request_id: str | None = None,
    user_id: uuid.UUID | None = None,
) -> Deployment:
    if not deployment.ip_address:
        raise ValueError("Deployment has no IP — cannot rotate keys")
    if deployment.status not in ("completed", "running"):
        raise ValueError("SSH rotation requires a completed deployment")

    import asyncio

    loop = asyncio.get_event_loop()
    log = await loop.run_in_executor(
        None,
        lambda: _rotate_on_server(deployment.ip_address, private_key_pem, new_public_key),
    )

    deployment.ssh_key_version += 1
    deployment.ssh_rotated_at = datetime.now(timezone.utc)
    if deployment.logs:
        deployment.logs = deployment.logs.split("SSH_PUBLIC_KEY:")[0] + f"SSH_PUBLIC_KEY:{new_public_key.strip()}\n"
    else:
        deployment.logs = f"SSH_PUBLIC_KEY:{new_public_key.strip()}\n"

    await emit(
        db,
        deployment,
        step="ssh_rotation",
        message=f"SSH keys rotated to version {deployment.ssh_key_version}",
        metadata={"log": log[:500]},
    )
    await record_audit_event(
        db,
        "deployment.ssh_rotated",
        user_id=user_id,
        resource_type="deployment",
        resource_id=str(deployment.id),
        request_id=request_id,
        metadata={"version": deployment.ssh_key_version},
    )
    await db.flush()
    logger.info(
        "ssh_keys_rotated",
        deployment_id=str(deployment.id),
        version=deployment.ssh_key_version,
    )
    return deployment
