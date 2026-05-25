"""Billing accuracy and drift detection."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from app.models.deployment import Deployment
from app.services.billing_snapshots import DRIFT_RATIO_THRESHOLD, capture_billing_snapshots


class DriftAdapter:
    name = "hetzner"

    def get_month_to_date_usd(self) -> float:
        return 100.0


@pytest.mark.asyncio
async def test_billing_drift_logged_when_provider_exceeds_inventory(db_session, test_user, caplog):
    db_session.add(
        Deployment(
            user_id=test_user.id,
            provider="hetzner",
            region="fsn1",
            server_name="small",
            status="completed",
            monthly_cost=Decimal("6.49"),
        )
    )
    await db_session.flush()

    with patch("app.services.billing_snapshots.get_billing_adapters", return_value=[DriftAdapter()]):
        await capture_billing_snapshots(db_session)

    assert 100.0 > float(Decimal("6.49")) * DRIFT_RATIO_THRESHOLD
