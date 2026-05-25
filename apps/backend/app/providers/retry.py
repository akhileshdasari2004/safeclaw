"""Exponential backoff for transient provider API failures."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from app.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")

RETRYABLE_MARKERS = ("429", "503", "502", "504", "timeout", "timed out", "connection")


def is_retryable(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if isinstance(exc, TimeoutError):
        return True
    return any(m in msg for m in RETRYABLE_MARKERS)


def call_with_backoff(
    fn: Callable[[], T],
    *,
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
) -> T:
    last: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            if attempt >= max_attempts or not is_retryable(e):
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            logger.warning("provider_retry", attempt=attempt, delay_sec=delay, error=str(e))
            time.sleep(delay)
    raise last  # type: ignore[misc]
