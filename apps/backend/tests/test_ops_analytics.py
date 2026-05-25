"""Ops analytics endpoint."""

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.models.deployment import Deployment
from app.models.scan import Scan
from app.utils.security import create_access_token


@pytest.mark.asyncio
async def test_ops_analytics(client: AsyncClient, db_session, test_user):
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="analytics-test",
        status="completed",
        monthly_cost=Decimal("5.00"),
        retry_count=1,
    )
    db_session.add(dep)
    await db_session.flush()
    db_session.add(Scan(deployment_id=dep.id, score=90, grade="A", findings_json={}))
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    r = await client.get("/api/v1/ops/analytics", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["scan_grades"][0]["grade"] == "A"
    assert body["avg_retry_count"] == 1.0
