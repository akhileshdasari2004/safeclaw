"""In-memory deployment log broadcaster for SSE streaming."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from app.utils.logging import get_logger

logger = get_logger(__name__)

HEARTBEAT_INTERVAL_SEC = 15
STREAM_TTL_SEC = 3600
MAX_HISTORY = 500
MAX_SUBSCRIBERS_PER_DEPLOYMENT = 32


@dataclass
class DeploymentLogEvent:
    timestamp: str
    deployment_id: str
    level: str
    step: str
    message: str

    def to_sse(self, event_type: str = "log") -> str:
        payload = json.dumps(asdict(self))
        return f"event: {event_type}\ndata: {payload}\n\n"

    @classmethod
    def heartbeat(cls, deployment_id: uuid.UUID) -> DeploymentLogEvent:
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            deployment_id=str(deployment_id),
            level="DEBUG",
            step="heartbeat",
            message="ping",
        )


@dataclass
class _StreamState:
    history: deque[DeploymentLogEvent] = field(default_factory=lambda: deque(maxlen=MAX_HISTORY))
    subscribers: list[asyncio.Queue[DeploymentLogEvent | None]] = field(default_factory=list)
    last_activity: float = field(default_factory=time.time)
    terminal: bool = False


class DeploymentLogBroadcaster:
    """Async-safe in-memory log stream manager with reconnect replay."""

    def __init__(self) -> None:
        self._streams: dict[uuid.UUID, _StreamState] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    def start_cleanup(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_cleanup(self) -> None:
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(60)
                now = time.time()
                async with self._lock:
                    stale = [
                        dep_id
                        for dep_id, state in self._streams.items()
                        if (now - state.last_activity) > STREAM_TTL_SEC
                        and state.terminal
                        and not state.subscribers
                    ]
                    for dep_id in stale:
                        del self._streams[dep_id]
                        logger.debug("deployment_log_stream_cleaned", deployment_id=str(dep_id))
            except asyncio.CancelledError:
                break

    async def ensure_stream(self, deployment_id: uuid.UUID) -> _StreamState:
        async with self._lock:
            if deployment_id not in self._streams:
                self._streams[deployment_id] = _StreamState()
            state = self._streams[deployment_id]
            state.last_activity = time.time()
            return state

    async def publish(
        self,
        deployment_id: uuid.UUID,
        *,
        level: str = "INFO",
        step: str,
        message: str,
        terminal: bool = False,
    ) -> DeploymentLogEvent:
        event = DeploymentLogEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            deployment_id=str(deployment_id),
            level=level,
            step=step,
            message=message,
        )
        async with self._lock:
            state = self._streams.setdefault(deployment_id, _StreamState())
            state.history.append(event)
            state.last_activity = time.time()
            if terminal:
                state.terminal = True
            for queue in list(state.subscribers):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass
        return event

    async def subscribe(
        self, deployment_id: uuid.UUID, *, replay: bool = True
    ) -> AsyncIterator[DeploymentLogEvent]:
        state = await self.ensure_stream(deployment_id)
        queue: asyncio.Queue[DeploymentLogEvent | None] = asyncio.Queue(maxsize=256)
        async with self._lock:
            if len(state.subscribers) >= MAX_SUBSCRIBERS_PER_DEPLOYMENT:
                raise RuntimeError("Too many subscribers for this deployment")
            state.subscribers.append(queue)
            history = list(state.history) if replay else []

        try:
            for event in history:
                yield event
            while True:
                if state.terminal and queue.empty():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL_SEC)
                except asyncio.TimeoutError:
                    if state.terminal:
                        break
                    yield DeploymentLogEvent.heartbeat(deployment_id)
                    continue
                if item is None:
                    break
                yield item
                if state.terminal and item.step in ("completed", "failed"):
                    break
        finally:
            async with self._lock:
                if queue in state.subscribers:
                    state.subscribers.remove(queue)

    async def close_stream(self, deployment_id: uuid.UUID, *, step: str, message: str, level: str = "INFO") -> None:
        await self.publish(deployment_id, level=level, step=step, message=message, terminal=True)
        async with self._lock:
            state = self._streams.get(deployment_id)
            if not state:
                return
            for queue in state.subscribers:
                try:
                    queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass

    async def mark_terminal(self, deployment_id: uuid.UUID) -> None:
        async with self._lock:
            state = self._streams.setdefault(deployment_id, _StreamState())
            state.terminal = True
            for queue in list(state.subscribers):
                try:
                    queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass

    def format_for_db(self, event: DeploymentLogEvent) -> str:
        return f"[{event.timestamp}] [{event.level}] [{event.step}] {event.message}\n"


log_broadcaster = DeploymentLogBroadcaster()
