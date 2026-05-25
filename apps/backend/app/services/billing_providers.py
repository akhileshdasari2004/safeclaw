"""Provider billing adapters — month-to-date spend estimates."""

from __future__ import annotations

import httpx

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BillingAdapter:
    name: str

    def get_month_to_date_usd(self) -> float | None:
        raise NotImplementedError


class HetznerBillingAdapter(BillingAdapter):
    """
    Hetzner does not expose a simple public MTD billing REST in hcloud SDK.
    TODO: verify Hetzner billing API / Robot API for invoice totals if available.
    Falls back to server inventory cost estimate via CloudProvider.
    """

    name = "hetzner"

    def get_month_to_date_usd(self) -> float | None:
        try:
            from app.providers.hetzner import HetznerProvider

            settings = get_settings()
            if not settings.hetzner_api_token:
                return None
            return HetznerProvider(settings.hetzner_api_token).get_estimated_monthly_spend()
        except Exception as e:
            logger.warning("hetzner_billing_unavailable", error=str(e))
            return None


class DigitalOceanBillingAdapter(BillingAdapter):
    """
    DigitalOcean balance endpoint returns account billing snapshot.
    See: GET https://api.digitalocean.com/v2/customers/my/billing_history (invoices)
    TODO: verify DO billing API for precise MTD — using balance endpoint as approximation.
    """

    name = "digitalocean"

    def get_month_to_date_usd(self) -> float | None:
        settings = get_settings()
        if not settings.digitalocean_api_token:
            return None
        try:
            with httpx.Client(timeout=30.0) as client:
                # Account balance — documented in DO API v2
                resp = client.get(
                    "https://api.digitalocean.com/v2/customers/my/balance",
                    headers={"Authorization": f"Bearer {settings.digitalocean_api_token}"},
                )
                if resp.status_code == 404:
                    # Fallback: estimate from droplets
                    from app.providers.digitalocean import DigitalOceanProvider

                    return DigitalOceanProvider(
                        settings.digitalocean_api_token
                    ).get_estimated_monthly_spend()
                resp.raise_for_status()
                data = resp.json()
                # month_to_date_balance may be negative (credit); use absolute usage field if present
                mtd = data.get("month_to_date_usage") or data.get("month_to_date_balance")
                if mtd is not None:
                    return abs(float(mtd))
        except Exception as e:
            logger.warning("do_billing_unavailable", error=str(e))
        try:
            from app.providers.digitalocean import DigitalOceanProvider

            return DigitalOceanProvider(settings.digitalocean_api_token).get_estimated_monthly_spend()
        except Exception:
            return None


def get_billing_adapters() -> list[BillingAdapter]:
    return [HetznerBillingAdapter(), DigitalOceanBillingAdapter()]
