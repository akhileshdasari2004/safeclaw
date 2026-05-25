"""SafeClaw API — production FastAPI application."""

import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.database import engine
from app.routers import alerts, auth, billing, deploy, scans
from app.services.alerts import poll_cost_alerts
from app.utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.app_env)
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


_alert_task: asyncio.Task | None = None


async def _alerts_worker() -> None:
    from app.database import AsyncSessionLocal

    while True:
        try:
            async with AsyncSessionLocal() as db:
                sent = await poll_cost_alerts(db)
                await db.commit()
                if sent:
                    logger.info("alerts_poll_complete", notifications=sent)
        except Exception as e:
            logger.exception("alerts_poll_error", error=str(e))
        await asyncio.sleep(settings.alerts_poll_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _alert_task
    _alert_task = asyncio.create_task(_alerts_worker())
    logger.info("app_started", env=settings.app_env)
    yield
    if _alert_task:
        _alert_task.cancel()
    await engine.dispose()
    logger.info("app_stopped")


app = FastAPI(
    title="SafeClaw API",
    description="Hardened OpenClaw deployment platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(deploy.router, prefix="/api/v1")
app.include_router(scans.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("unhandled_error", request_id=request_id, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict:
    try:
        from sqlalchemy import text
        from app.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "not_ready", "error": str(e)})
