"""Billing snapshot capture tests."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.models.deployment import Deployment
from app.services.billing_snapshots import capture_billing_snapshots, sum_active_deployment_costs, validate_snapshot_accuracy


class FakeAdapter:
    def __init__(self, name: str, mtd: float):
        self.name = name
        self._mtd = mtd

    def get_month_to_date_usd(self) -> float:
        return self._mtd


@pytest.mark.asyncio
async def test_capture_billing_snapshots(db_session, test_user):
    dep = Deployment(
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="bill-test",
        status="completed",
        monthly_cost=Decimal("6.49"),
    )
    db_session.add(dep)
    await db_session.flush()

    with patch(
        "app.services.billing_snapshots.get_billing_adapters",
        return_value=[FakeAdapter("hetzner", 6.49)],
    ):
        snaps = await capture_billing_snapshots(db_session)
        await db_session.commit()

    assert len(snaps) == 1
    assert snaps[0].provider == "hetzner"
    assert float(snaps[0].month_to_date_usd) == 6.49
    assert float(snaps[0].deployment_sum_usd or 0) == 6.49


@pytest.mark.asyncio
async def test_sum_active_deployment_costs(db_session, test_user):
    db_session.add(
        Deployment(
            user_id=test_user.id,
            provider="hetzner",
            region="fsn1",
            server_name="a",
            status="completed",
            monthly_cost=Decimal("10.00"),
        )
    )
    db_session.add(
        Deployment(
            user_id=test_user.id,
            provider="hetzner",
            region="fsn1",
            server_name="b",
            status="failed",
            monthly_cost=Decimal("99.00"),
        )
    )
    await db_session.flush()
    total = await sum_active_deployment_costs(db_session)
    assert total == Decimal("10.00")


def test_validate_snapshot_accuracy():
    assert validate_snapshot_accuracy(6.0, 6.0) is True
    assert validate_snapshot_accuracy(20.0, 6.0, tolerance_ratio=2.0) is False
    assert validate_snapshot_accuracy(0.0, 0.0) is True
