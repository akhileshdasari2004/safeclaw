"""Multi-tenant authorization — deployments, events, logs."""

import uuid

import pytest
from httpx import AsyncClient

from app.models.deployment import Deployment
from app.utils.security import create_access_token


@pytest.mark.asyncio
async def test_other_user_cannot_fetch_deployment(client: AsyncClient, db_session, test_user):
    other_id = uuid.uuid4()
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=other_id,
        provider="hetzner",
        region="fsn1",
        server_name="private",
        status="completed",
    )
    db_session.add(dep)
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    r = await client.get(
        f"/api/v1/deployments/{dep.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_other_user_cannot_fetch_timeline(client: AsyncClient, db_session, test_user):
    other_id = uuid.uuid4()
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=other_id,
        provider="hetzner",
        region="fsn1",
        server_name="private",
        status="completed",
    )
    db_session.add(dep)
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    r = await client.get(
        f"/api/v1/deployments/{dep.id}/timeline",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_other_user_cannot_resume_deployment(client: AsyncClient, db_session, test_user):
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider="hetzner",
        region="fsn1",
        server_name="private",
        status="failed",
        provision_state="FAILED",
    )
    db_session.add(dep)
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    r = await client.post(
        f"/api/v1/deployments/{dep.id}/resume",
        headers={"Authorization": f"Bearer {token}"},
    )
    # 404 when not owned; 403 if license gate runs before ownership check
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_other_user_cannot_access_ops(client: AsyncClient, db_session, test_user):
    other = uuid.uuid4()
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=other,
        provider="hetzner",
        region="fsn1",
        server_name="ops-private",
        status="completed",
    )
    db_session.add(dep)
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    r = await client.get("/api/v1/ops/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["deployments_total"] == 0


@pytest.mark.asyncio
async def test_other_user_cannot_resolve_foreign_incident(client: AsyncClient, db_session, test_user):
    from app.services.incidents import open_incident

    other = uuid.uuid4()
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=other,
        provider="hetzner",
        region="fsn1",
        server_name="inc",
        status="failed",
    )
    db_session.add(dep)
    await db_session.flush()
    inc = await open_incident(
        db_session,
        title="Foreign",
        user_id=other,
        deployment_id=dep.id,
    )
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    r = await client.post(
        f"/api/v1/incidents/{inc.id}/resolve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code in (403, 404)


@pytest.mark.asyncio
async def test_other_user_cannot_trigger_scan(client: AsyncClient, db_session, test_user):
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider="hetzner",
        region="fsn1",
        server_name="scan-private",
        status="completed",
        ip_address="203.0.113.1",
    )
    db_session.add(dep)
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    r = await client.post(
        f"/api/v1/scans/deployments/{dep.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
