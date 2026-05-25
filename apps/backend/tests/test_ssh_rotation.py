"""SSH rotation service tests."""

import uuid
from unittest.mock import patch

import pytest

from app.models.deployment import Deployment
from app.services.ssh_rotation import _rotate_on_server


def test_rotate_on_server_mock():
    with patch("app.services.ssh_rotation.SSHClient") as mock_ssh_cls:
        inst = mock_ssh_cls.return_value
        inst.run.return_value = (0, "rotated_ok\n", "")
        out = _rotate_on_server("203.0.113.1", "fake-pem", "ssh-rsa AAAA test")
        assert "rotated_ok" in out
        inst.connect.assert_called_once()
        inst.close.assert_called_once()


@pytest.mark.asyncio
async def test_rotate_endpoint_requires_completed(client, db_session, test_user):
    from app.utils.security import create_access_token, encrypt_secret

    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="rot-test",
        status="queued",
        ip_address=None,
    )
    db_session.add(dep)
    await db_session.commit()

    token = create_access_token(str(test_user.id))
    r = await client.post(
        f"/api/v1/deployments/{dep.id}/rotate-ssh",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "new_public_key": "ssh-rsa " + "A" * 50 + " user@host",
            "new_private_key": "-----BEGIN RSA PRIVATE KEY-----\n" + "x" * 50,
        },
    )
    assert r.status_code == 400
