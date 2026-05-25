"""Transactional email via Resend."""

from __future__ import annotations

import resend

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _send(to: str, subject: str, html: str) -> None:
    settings = get_settings()
    if not settings.resend_api_key:
        logger.warning("resend_skipped", reason="RESEND_API_KEY not set", to=to, subject=subject)
        return
    resend.api_key = settings.resend_api_key
    resend.Emails.send({
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "html": html,
    })
    logger.info("email_sent", to=to, subject=subject)


def send_license_email(to: str, license_key: str, tier: str) -> None:
    html = f"""
    <div style="font-family: system-ui, sans-serif; max-width: 560px; margin: 0 auto;">
      <h1 style="color: #0f172a;">Welcome to SafeClaw</h1>
      <p>Your <strong>{tier}</strong> license is ready.</p>
      <p style="background: #f1f5f9; padding: 16px; border-radius: 8px; font-family: monospace; font-size: 18px;">
        {license_key}
      </p>
      <p>Sign in at your dashboard and start the deploy wizard to launch a hardened OpenClaw instance.</p>
      <p style="color: #64748b; font-size: 14px;">Keep this key private. Do not share it publicly.</p>
    </div>
    """
    _send(to, "Your SafeClaw license key", html)


def send_deployment_success_email(to: str, server_name: str, ip_address: str) -> None:
    html = f"""
    <div style="font-family: system-ui, sans-serif; max-width: 560px;">
      <h1>Deployment successful</h1>
      <p>Server <strong>{server_name}</strong> is live at <code>{ip_address}</code>.</p>
      <p>Open your dashboard to run a security scan or configure cost alerts.</p>
    </div>
    """
    _send(to, f"SafeClaw: {server_name} is live", html)


def send_cost_alert_email(
    to: str,
    current_spend: float,
    threshold: float,
    *,
    provider: str | None = None,
    test: bool = False,
) -> None:
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    title = "SafeClaw cost alert (test)" if test else "SafeClaw cost threshold exceeded"
    html = f"""
    <div style="font-family: system-ui, sans-serif; max-width: 560px;">
      <h1 style="color: #dc2626;">{title}</h1>
      <table style="width:100%; border-collapse: collapse; margin: 16px 0;">
        <tr><td style="padding:8px 0;color:#64748b;">Current spend</td>
            <td style="padding:8px 0;"><strong>${current_spend:.2f}/mo est.</strong></td></tr>
        <tr><td style="padding:8px 0;color:#64748b;">Threshold</td>
            <td style="padding:8px 0;"><strong>${threshold:.2f}</strong></td></tr>
        <tr><td style="padding:8px 0;color:#64748b;">Provider</td>
            <td style="padding:8px 0;">{provider or "all"}</td></tr>
        <tr><td style="padding:8px 0;color:#64748b;">Time</td>
            <td style="padding:8px 0;">{ts}</td></tr>
      </table>
      <p>Review deployments and alert settings in your SafeClaw dashboard.</p>
    </div>
    """
    _send(to, title, html)
