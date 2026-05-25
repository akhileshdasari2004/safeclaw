"""Dashboard ops metrics API."""

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.models.deployment import Deployment
from app.models.scan import Scan
from app.utils.security import create_access_token


@pytest.mark.asyncio
async def test_ops_dashboard_metrics(client: AsyncClient, db_session, test_user):
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="ops-test",
        status="completed",
        monthly_cost=Decimal("10.00"),
    )
    db_session.add(dep)
    await db_session.flush()
    db_session.add(
        Scan(
            deployment_id=dep.id,
            score=85,
            grade="B",
            findings_json={"findings": []},
        )
    )
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    r = await client.get(
        "/api/v1/ops/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["deployments_total"] == 1
    assert body["deployments_completed"] == 1
    assert body["estimated_monthly_spend_usd"] == 10.0
    assert body["avg_security_score"] == 85.0
