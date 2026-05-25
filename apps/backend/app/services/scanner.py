"""Security scanner — remote checks over SSH."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment
from app.models.scan import Scan
from app.services.ssh_client import SSHClient
from app.utils.logging import get_logger

logger = get_logger(__name__)

DANGEROUS_PORTS = {23, 135, 139, 445, 3389, 5900}


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _run_checks(ip: str, private_key_pem: str | None) -> dict:
    issues: list[dict] = []
    score = 100

    ssh = SSHClient(host=ip, username="root", private_key_pem=private_key_pem)
    ssh.connect()
    try:
        checks = [
            ("ufw status | grep -i active", "UFW firewall enabled", "critical",
             "sudo ufw enable && sudo ufw default deny incoming"),
            ("systemctl is-active fail2ban", "fail2ban active", "high",
             "sudo systemctl enable --now fail2ban"),
            ("grep -E '^PermitRootLogin' /etc/ssh/sshd_config.d/99-safeclaw.conf 2>/dev/null || grep PermitRootLogin /etc/ssh/sshd_config",
             "Root login restricted", "high",
             "Set PermitRootLogin prohibit-password in /etc/ssh/sshd_config.d/99-safeclaw.conf"),
            ("grep -E '^PasswordAuthentication no' /etc/ssh/sshd_config.d/99-safeclaw.conf 2>/dev/null",
             "Password authentication disabled", "critical",
             "Set PasswordAuthentication no in SSH config"),
            ("systemctl is-active docker", "Docker running", "medium",
             "sudo systemctl enable --now docker"),
            ("test -f /etc/apt/apt.conf.d/20auto-upgrades && grep -q Unattended-Upgrade /etc/apt/apt.conf.d/20auto-upgrades",
             "Unattended upgrades enabled", "medium",
             "sudo apt install -y unattended-upgrades"),
        ]

        for cmd, desc, severity, remediation in checks:
            code, out, _ = ssh.run(cmd)
            ok = code == 0 and ("active" in out.lower() or "yes" in out.lower() or "prohibit" in out.lower() or "no" in out.lower())
            if not ok:
                penalty = {"critical": 20, "high": 15, "medium": 10, "low": 5}.get(severity, 5)
                score = max(0, score - penalty)
                issues.append({
                    "severity": severity,
                    "description": f"Check failed: {desc}",
                    "remediation": remediation,
                })

        code, out, _ = ssh.run("ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null")
        if code == 0:
            for port in DANGEROUS_PORTS:
                if f":{port} " in out or f":{port}\n" in out:
                    score = max(0, score - 10)
                    issues.append({
                        "severity": "high",
                        "description": f"Dangerous port {port} appears open",
                        "remediation": f"Close port {port} via firewall: sudo ufw deny {port}/tcp",
                    })

        code, out, _ = ssh.run("df -h / | tail -1 | awk '{print $5}' | tr -d '%'")
        if code == 0 and out.strip().isdigit():
            usage = int(out.strip())
            if usage > 90:
                score = max(0, score - 15)
                issues.append({
                    "severity": "high",
                    "description": f"Disk usage critical: {usage}%",
                    "remediation": "Free disk space: sudo apt autoremove -y && docker system prune -af",
                })
            elif usage > 80:
                score = max(0, score - 5)
                issues.append({
                    "severity": "medium",
                    "description": f"Disk usage elevated: {usage}%",
                    "remediation": "Monitor disk and prune unused Docker images",
                })

        code, out, _ = ssh.run("free | awk '/Mem:/ {printf \"%.0f\", $3/$2 * 100}'")
        if code == 0 and out.strip().isdigit():
            mem = int(out.strip())
            if mem > 90:
                score = max(0, score - 10)
                issues.append({
                    "severity": "medium",
                    "description": f"Memory pressure: {mem}% used",
                    "remediation": "Restart heavy services or upgrade instance size",
                })
    finally:
        ssh.close()

    return {"score": score, "grade": _grade(score), "issues": issues}


async def run_scan(
    db: AsyncSession,
    deployment_id: uuid.UUID,
    user_id: uuid.UUID,
    private_key_pem: str | None,
) -> Scan:
    result = await db.execute(
        select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.user_id == user_id,
        )
    )
    deployment = result.scalar_one_or_none()
    if not deployment or not deployment.ip_address:
        raise ValueError("Deployment not found or not ready")
    if deployment.status != "running":
        raise ValueError("Deployment must be running to scan")

    loop = asyncio.get_event_loop()
    findings = await loop.run_in_executor(
        None,
        lambda: _run_checks(deployment.ip_address, private_key_pem),
    )

    scan = Scan(
        deployment_id=deployment.id,
        score=findings["score"],
        grade=findings["grade"],
        findings_json=findings,
    )
    db.add(scan)
    await db.flush()
    logger.info("scan_complete", deployment_id=str(deployment_id), score=findings["score"])
    return scan
