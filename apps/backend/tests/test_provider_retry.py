"""Provider retry/backoff tests."""

import time
from unittest.mock import MagicMock

import pytest

from app.providers.resilient import ResilientCloudProvider
from app.providers.retry import call_with_backoff, is_retryable


def test_is_retryable():
    assert is_retryable(TimeoutError("timed out"))
    assert is_retryable(RuntimeError("429 Too Many Requests"))
    assert not is_retryable(ValueError("bad plan"))


def test_call_with_backoff_retries_then_succeeds():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise TimeoutError("timed out")
        return "ok"

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(time, "sleep", lambda _: None)
        assert call_with_backoff(flaky, max_attempts=3, base_delay=0.01) == "ok"
    assert calls["n"] == 2


def test_resilient_provider_wraps_create():
    from app.providers.base import ProvisionedServer

    inner = MagicMock()
    inner.name = "hetzner"
    inner.create_server.side_effect = [
        TimeoutError("timeout"),
        ProvisionedServer(server_id="s1", ip_address="1.2.3.4", monthly_cost_usd=1.0),
    ]
    wrapped = ResilientCloudProvider(inner)
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(time, "sleep", lambda _: None)
        wrapped.create_server("n", "fsn1", "cx22", "ssh-rsa key")
    assert inner.create_server.call_count == 2
