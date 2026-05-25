"""Incident system tests."""

import uuid

import pytest

from app.models.deployment import Deployment
from app.services import deployment_states as st
from app.services.incidents import list_user_incidents, open_incident, resolve_incident


@pytest.mark.asyncio
async def test_open_and_resolve_incident(db_session, test_user):
    dep = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        provider="hetzner",
        region="fsn1",
        server_name="inc-test",
        status="failed",
        provision_state=st.FAILED,
    )
    db_session.add(dep)
    await db_session.flush()

    inc = await open_incident(
        db_session,
        title="Test incident",
        deployment_id=dep.id,
        user_id=test_user.id,
        severity="high",
    )
    rows = await list_user_incidents(db_session, test_user.id, status="open")
    assert len(rows) >= 1

    resolved = await resolve_incident(db_session, inc.id)
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None
