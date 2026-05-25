"""Request/response structured logging with deployment correlation."""

from __future__ import annotations

import re
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics.collector import metrics
from app.utils.logging import get_logger

logger = get_logger(__name__)

_DEPLOYMENT_PATH = re.compile(
    r"/api/v1/deployments/([0-9a-fA-F-]{36})"
)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        deployment_id: str | None = None
        match = _DEPLOYMENT_PATH.search(request.url.path)
        if match:
            deployment_id = match.group(1)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            deployment_id=deployment_id,
        )

        metrics.inc("http_requests_total")
        logger.info("http_request_started")

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            metrics.observe("http_request_duration_ms", duration_ms)
            logger.exception("http_request_failed", duration_ms=round(duration_ms, 2))
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        metrics.observe("http_request_duration_ms", duration_ms)
        logger.info(
            "http_request_completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
