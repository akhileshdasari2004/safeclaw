import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.models.license import License
from app.models.user import User
from app.utils.security import create_access_token


@pytest.mark.asyncio
async def test_sse_requires_token(db_session, test_user: User):
    transport = ASGITransport(app=app)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    dep_id = uuid.uuid4()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/logs/{dep_id}/stream")
        assert resp.status_code == 422

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sse_ownership_denied(db_session, test_user: User):
    """Wrong deployment id returns 404."""
    token = create_access_token(str(test_user.id))
    transport = ASGITransport(app=app)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/logs/{uuid.uuid4()}/stream",
            params={"token": token},
        )
        assert resp.status_code == 404

    app.dependency_overrides.clear()
