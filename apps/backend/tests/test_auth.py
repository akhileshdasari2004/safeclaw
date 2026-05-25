import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "securepass123"},
    )
    assert reg.status_code == 201
    assert "access_token" in reg.json()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "new@example.com", "password": "securepass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"
