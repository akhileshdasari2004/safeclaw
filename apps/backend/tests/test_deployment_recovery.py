import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.deployment import Deployment
from app.models.user import User
from app.services import deployment_states as st
from app.services.deployment_recovery import resume_deployment, rollback_deployment


@pytest.mark.asyncio
async def test_resume_rejects_completed(db_session, test_user: User):
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="done",
        status="completed",
        provision_state=st.COMPLETED,
    )
    db_session.add(dep)
    await db_session.flush()

    with pytest.raises(ValueError, match="Cannot resume"):
        await resume_deployment(db_session, dep.id)


@pytest.mark.asyncio
async def test_rollback_clears_server(db_session, test_user: User):
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="rb",
        status="failed",
        provision_state=st.FAILED,
        provider_server_id="srv-99",
        ip_address="203.0.113.1",
    )
    db_session.add(dep)
    await db_session.flush()

    mock_provider = MagicMock()
    with patch("app.services.deployment_recovery.get_provider", return_value=mock_provider):
        result = await rollback_deployment(db_session, dep.id)

    assert result.provision_state == st.ROLLED_BACK
    assert result.provider_server_id is None
    mock_provider.delete_server.assert_called_once_with("srv-99")
