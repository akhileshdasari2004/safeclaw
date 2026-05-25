"""Security scanner — SSH-based checks with weighted scoring."""

from __future__ import annotations

import asyncio
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment
from app.models.scan import Scan
from app.services.ssh_client import SSHClient
from app.utils.logging import get_logger

logger = get_logger(__name__)

DANGEROUS_PORTS = {23, 135, 139, 445, 3389, 5900}
PENALTIES = {"critical": 20, "high": 15, "medium": 10, "low": 5, "info": 2}
READY_STATUSES = frozenset({"completed", "running"})


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


def _parse_active(output: str) -> bool:
    low = output.lower().strip()
    return low in ("active", "enabled") or "active" in low


def _parse_grep_value(output: str, expect_substrings: tuple[str, ...]) -> bool:
    low = output.lower()
    return any(s in low for s in expect_substrings)


def _run_checks(ip: str, private_key_pem: str | None) -> dict:
    findings: list[dict] = []
    score = 100

    def add_finding(severity: str, title: str, description: str, remediation: str) -> None:
        nonlocal score
        penalty = PENALTIES.get(severity, 5)
        score = max(0, score - penalty)
        findings.append({
            "severity": severity,
            "title": title,
            "description": description,
            "remediation": remediation,
        })

    ssh = SSHClient(host=ip, username="root", private_key_pem=private_key_pem)
    ssh.connect()
    try:
        checks: list[tuple[str, str, str, str, tuple[str, ...] | None]] = [
            (
                "ufw status 2>/dev/null | head -5",
                "UFW firewall disabled",
                "Uncomplicated Firewall does not appear active.",
                "critical",
                ("sudo ufw default deny incoming && sudo ufw enable",),
            ),
            (
                "systemctl is-active fail2ban 2>/dev/null",
                "fail2ban inactive",
                "fail2ban service is not running.",
                "high",
                ("sudo systemctl enable --now fail2ban",),
            ),
            (
                "grep -hE '^PermitRootLogin' /etc/ssh/sshd_config.d/99-safeclaw.conf /etc/ssh/sshd_config 2>/dev/null | tail -1",
                "Root login not restricted",
                "SSH may still allow unrestricted root login.",
                "high",
                ("prohibit-password", "no", "without-password"),
            ),
            (
                "grep -hE '^PasswordAuthentication' /etc/ssh/sshd_config.d/99-safeclaw.conf /etc/ssh/sshd_config 2>/dev/null | tail -1",
                "Password authentication enabled",
                "SSH password authentication is still enabled.",
                "critical",
                ("passwordauthentication no",),
            ),
            (
                "systemctl is-active docker 2>/dev/null",
                "Docker not running",
                "Docker daemon is not active.",
                "medium",
                ("sudo systemctl enable --now docker",),
            ),
            (
                "test -f /etc/apt/apt.conf.d/20auto-upgrades && grep -qi Unattended-Upgrade /etc/apt/apt.conf.d/20auto-upgrades && echo ok",
                "Unattended upgrades disabled",
                "Automatic security updates may not be configured.",
                "medium",
                ("ok",),
            ),
        ]

        for cmd, title, desc, severity, expect in checks:
            code, out, err = ssh.run(cmd, timeout=60)
            ok = code == 0
            if expect:
                if "ufw" in cmd:
                    ok = ok and _parse_active(out)
                elif "fail2ban" in cmd or "docker" in cmd:
                    ok = ok and _parse_active(out)
                elif "PermitRootLogin" in cmd:
                    ok = ok and _parse_grep_value(out, expect)
                elif "PasswordAuthentication" in cmd:
                    ok = ok and _parse_grep_value(out, expect)
                elif "unattended" in cmd.lower():
                    ok = ok and "ok" in out.lower()
            if not ok:
                remediation = {
                    "UFW firewall disabled": "sudo ufw default deny incoming && sudo ufw allow 22/tcp && sudo ufw enable",
                    "fail2ban inactive": "sudo systemctl enable --now fail2ban",
                    "Root login not restricted": "echo 'PermitRootLogin prohibit-password' | sudo tee /etc/ssh/sshd_config.d/99-safeclaw.conf && sudo systemctl reload ssh",
                    "Password authentication enabled": "echo 'PasswordAuthentication no' | sudo tee -a /etc/ssh/sshd_config.d/99-safeclaw.conf && sudo systemctl reload ssh",
                    "Docker not running": "sudo systemctl enable --now docker",
                    "Unattended upgrades disabled": "sudo apt-get install -y unattended-upgrades && sudo dpkg-reconfigure -plow unattended-upgrades",
                }.get(title, err or out or "See SafeClaw hardening docs")
                add_finding(severity, title, desc, remediation.strip())

        code, out, _ = ssh.run("ss -tlnH 2>/dev/null || ss -tln 2>/dev/null || netstat -tln 2>/dev/null", timeout=30)
        if code == 0:
            for port in DANGEROUS_PORTS:
                if re.search(rf":{port}\b", out):
                    add_finding(
                        "high",
                        f"Dangerous port {port} exposed",
                        f"Port {port} appears to be listening.",
                        f"sudo ufw deny {port}/tcp",
                    )

        code, out, _ = ssh.run("df -P / 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%'", timeout=30)
        if code == 0 and out.strip().isdigit():
            usage = int(out.strip())
            if usage > 90:
                add_finding(
                    "high",
                    "Disk usage critical",
                    f"Root filesystem is {usage}% full.",
                    "sudo apt-get autoremove -y && docker system prune -af",
                )
            elif usage > 80:
                add_finding(
                    "medium",
                    "Disk usage elevated",
                    f"Root filesystem is {usage}% full.",
                    "Monitor disk usage and prune Docker images regularly.",
                )

        code, out, _ = ssh.run(
            "awk '/MemTotal/ {t=$2} /MemAvailable/ {a=$2} END {if(t>0) printf \"%.0f\", (t-a)/t*100; else print 0}' /proc/meminfo",
            timeout=30,
        )
        if code == 0 and out.strip().isdigit():
            mem = int(out.strip())
            if mem > 90:
                add_finding(
                    "medium",
                    "Memory pressure",
                    f"Estimated memory use is {mem}%.",
                    "Restart heavy containers or upgrade instance size.",
                )
    finally:
        ssh.close()

    critical = sum(1 for f in findings if f["severity"] == "critical")
    high = sum(1 for f in findings if f["severity"] == "high")
    risk_summary = (
        f"{len(findings)} finding(s): {critical} critical, {high} high."
        if findings
        else "No significant issues detected."
    )

    return {
        "score": score,
        "grade": _grade(score),
        "findings": findings,
        "risk_summary": risk_summary,
    }


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
    if deployment.status not in READY_STATUSES:
        raise ValueError("Deployment must be completed before scanning")

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
