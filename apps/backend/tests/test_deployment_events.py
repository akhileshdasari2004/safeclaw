import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import Base, get_db
from app.main import app
from app.models.deployment import Deployment
from app.models.user import User
from app.services import deployment_events as ev_svc
from app.utils.security import create_access_token, hash_password


@pytest.mark.asyncio
async def test_emit_persists_event(db_session, test_user: User):
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="evt-test",
        status="queued",
    )
    db_session.add(dep)
    await db_session.flush()

    row = await ev_svc.emit(db_session, dep, step="creating_server", message="Test message")
    await db_session.commit()

    assert row.id is not None
    assert row.correlation_id == dep.correlation_id
    assert row.step == "creating_server"

    events = await ev_svc.list_events(db_session, dep.id)
    assert len(events) == 1
    assert events[0].message == "Test message"


@pytest.mark.asyncio
async def test_timeline_api(db_session, test_user: User):
    from datetime import datetime, timedelta, timezone

    from app.models.license import License

    lic = License(
        key="SC-TL-9999",
        tier="pro",
        active=True,
        user_id=test_user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="tl-test",
        status="provisioning",
    )
    db_session.add(lic)
    db_session.add(dep)
    await ev_svc.emit(db_session, dep, step="creating_server", message="a")
    await ev_svc.emit(db_session, dep, step="waiting_for_ssh", message="b")
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    transport = ASGITransport(app=app)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/deployments/{dep.id}/timeline",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["step_count"] == 2
        assert len(body["steps"]) == 2

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_events_cross_tenant_denied(db_session, test_user: User):
    other = User(id=uuid.uuid4(), email="other@example.com", hashed_password=hash_password("pass12345"))
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=other.id,
        provider="hetzner",
        region="fsn1",
        server_name="private",
        status="queued",
    )
    db_session.add(other)
    db_session.add(dep)
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    transport = ASGITransport(app=app)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/deployments/{dep.id}/events",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    app.dependency_overrides.clear()
