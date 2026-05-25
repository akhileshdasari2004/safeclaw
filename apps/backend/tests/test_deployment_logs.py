import uuid

import pytest  # noqa: I001

from app.services.deployment_logs import DeploymentLogBroadcaster


@pytest.mark.asyncio
async def test_broadcaster_publish_and_subscribe():
    broadcaster = DeploymentLogBroadcaster()
    dep_id = uuid.uuid4()

    ev1 = await broadcaster.publish(dep_id, step="creating_server", message="Starting")
    ev1.event_id = str(uuid.uuid4())
    ev2 = await broadcaster.publish(dep_id, step="completed", message="Done", terminal=True)
    ev2.event_id = str(uuid.uuid4())
    await broadcaster.close_stream(dep_id, step="completed", message="closed")

    events = []
    async for ev in broadcaster.subscribe(dep_id, replay=True):
        if ev.step != "heartbeat":
            events.append(ev.step)
        if ev.step == "completed" and len(events) >= 2:
            break

    assert "creating_server" in events
