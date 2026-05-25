import asyncio
import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("JWT_SECRET", "test-secret-key-minimum-32-characters-long")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-for-unit-tests!!")

from app.database import Base, get_db
from app.main import app
from app.models.alert_history import AlertHistory  # noqa: F401
from app.models.audit_event import AuditEvent  # noqa: F401
from app.models.billing_snapshot import BillingSnapshot  # noqa: F401
from app.models.deployment_event import DeploymentEvent  # noqa: F401
from app.models.incident_event import IncidentEvent  # noqa: F401
from app.models.provision_job import ProvisionJob  # noqa: F401
from app.models.license import License
from app.models.user import User
from app.utils.security import hash_password

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(id=uuid.uuid4(), email="test@example.com", hashed_password=hash_password("password123"))
    db_session.add(user)
    lic = License(user_id=user.id, key="SC-TEST-TEST-TEST-TEST", tier="pro", active=True)
    db_session.add(lic)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def deployment_row(db_session: AsyncSession, test_user: User):
    from app.models.deployment import Deployment
    from app.services import deployment_states as st

    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="integration-test",
        plan_id="cx22",
        status="queued",
        provision_state=st.QUEUED,
        logs="SSH_PUBLIC_KEY:ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7test mock-key safeclaw@example.com\n",
    )
    db_session.add(dep)
    await db_session.flush()
    return dep


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_user: User) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
