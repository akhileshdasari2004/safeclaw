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
from app.config import get_settings
from app.middleware.structured_logging import StructuredLoggingMiddleware
from app.database import engine
from app.routers import alerts, auth, billing, deploy, deployment_events, incidents, logs, ops, scans
from app.metrics.collector import metrics
from app.services.deployment_logs import log_broadcaster
from app.services.alerts import poll_cost_alerts
from app.utils.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.app_env)
logger = get_logger(__name__)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])


_scheduler = None


def _run_alert_poll_job() -> None:
    """APScheduler sync wrapper — runs async poll in fresh event loop."""
    from app.database import AsyncSessionLocal

    async def _inner() -> None:
        async with AsyncSessionLocal() as db:
            from app.services.job_orchestrator import run_scheduled_maintenance

            summary = await run_scheduled_maintenance(db)
            sent = await poll_cost_alerts(db)
            await db.commit()
            if summary.get("orphans_recovered"):
                logger.info("orphan_recovery_complete", count=summary["orphans_recovered"])
            if sent:
                logger.info("alerts_poll_complete", notifications=sent)

    asyncio.run(_inner())


def _start_scheduler() -> None:
    global _scheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_alert_poll_job,
        IntervalTrigger(seconds=settings.alerts_poll_interval_seconds),
        id="cost_alerts",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("alert_scheduler_started", interval_sec=settings.alerts_poll_interval_seconds)


def _stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _alert_task
    log_broadcaster.start_cleanup()
    _start_scheduler()
    logger.info("app_started", env=settings.app_env)
    yield
    _stop_scheduler()
    await log_broadcaster.stop_cleanup()
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

app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(deployment_events.router, prefix="/api/v1")
app.include_router(deploy.router, prefix="/api/v1")
app.include_router(scans.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")
app.include_router(ops.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")


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


@app.get("/metrics")
async def prometheus_style_metrics() -> dict:
    """Operational metrics snapshot (JSON)."""
    return metrics.snapshot()


@app.get("/live")
async def liveness() -> dict:
    return {"status": "alive"}


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
