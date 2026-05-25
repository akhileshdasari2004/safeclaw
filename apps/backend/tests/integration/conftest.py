"""Shared fixtures for integration tests."""

import uuid

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deployment import Deployment
from app.models.user import User
from app.services import deployment_states as st

SSH_PUBLIC = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7test mock-key safeclaw@example.com"


@pytest_asyncio.fixture
async def deployment_row(db_session: AsyncSession, test_user: User) -> Deployment:
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="integration-test",
        plan_id="cx22",
        status="queued",
        provision_state=st.QUEUED,
        logs=f"SSH_PUBLIC_KEY:{SSH_PUBLIC}\n",
    )
    db_session.add(dep)
    await db_session.flush()
    return dep
