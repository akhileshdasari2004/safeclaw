"""Operational dashboard metrics for the frontend."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.alert import Alert
from app.models.alert_history import AlertHistory
from app.models.deployment import Deployment
from app.models.incident_event import IncidentEvent
from app.models.scan import Scan
from app.schemas.ops import (
    AlertTriggerBucket,
    AnalyticsOpsResponse,
    DashboardOpsResponse,
    RecentFailure,
    ScanGradeBucket,
    StatusCount,
)
from app.services.incidents import STATUS_OPEN
from app.services import deployment_states as st

router = APIRouter(prefix="/ops", tags=["ops"])

ACTIVE_LEGACY = frozenset({
    "queued", "pending", "provisioning", "hardening", "installing", "verifying", "running",
})
ACTIVE_PROVISION = frozenset({
    st.QUEUED,
    st.CREATING_SERVER,
    st.WAITING_FOR_SSH,
    st.HARDENING,
    st.INSTALLING_DOCKER,
    st.INSTALLING_OPENCLAW,
    st.VERIFYING,
    st.ROLLING_BACK,
})


@router.get("/dashboard", response_model=DashboardOpsResponse)
async def get_dashboard_ops(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DashboardOpsResponse:
    dep_result = await db.execute(select(Deployment).where(Deployment.user_id == user.id))
    deployments = list(dep_result.scalars().all())

    status_counts: dict[str, int] = {}
    monthly_spend = Decimal("0")
    completed = 0
    failed = 0
    active = 0

    for d in deployments:
        status_counts[d.status] = status_counts.get(d.status, 0) + 1
        if d.status in ("completed", "running"):
            completed += 1
            if d.monthly_cost:
                monthly_spend += d.monthly_cost
        elif d.status == "failed" or d.provision_state == st.FAILED:
            failed += 1
        if d.status in ACTIVE_LEGACY or d.provision_state in ACTIVE_PROVISION:
            active += 1

    finished = completed + failed
    success_rate = round((completed / finished) * 100, 1) if finished else 0.0

    scan_avg = await db.execute(
        select(func.avg(Scan.score))
        .select_from(Scan)
        .join(Deployment, Scan.deployment_id == Deployment.id)
        .where(Deployment.user_id == user.id)
    )
    avg_score = scan_avg.scalar()
    scans_count = await db.execute(
        select(func.count(Scan.id))
        .select_from(Scan)
        .join(Deployment, Scan.deployment_id == Deployment.id)
        .where(Deployment.user_id == user.id)
    )
    alerts_count = await db.execute(
        select(func.count(Alert.id)).where(Alert.user_id == user.id, Alert.enabled.is_(True))
    )

    recent_failures: list[RecentFailure] = []
    for d in sorted(
        [x for x in deployments if x.status == "failed" or x.provision_state == st.FAILED],
        key=lambda x: x.updated_at,
        reverse=True,
    )[:5]:
        recent_failures.append(
            RecentFailure(
                deployment_id=d.id,
                server_name=d.server_name,
                error_message=d.error_message,
                updated_at=d.updated_at.isoformat(),
            )
        )

    return DashboardOpsResponse(
        deployments_total=len(deployments),
        deployments_active=active,
        deployments_completed=completed,
        deployments_failed=failed,
        success_rate_pct=success_rate,
        estimated_monthly_spend_usd=float(monthly_spend),
        avg_security_score=round(float(avg_score), 1) if avg_score is not None else None,
        scans_total=int(scans_count.scalar() or 0),
        alerts_enabled=int(alerts_count.scalar() or 0),
        status_breakdown=[
            StatusCount(status=k, count=v) for k, v in sorted(status_counts.items())
        ],
        recent_failures=recent_failures,
    )


@router.get("/analytics", response_model=AnalyticsOpsResponse)
async def get_ops_analytics(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOpsResponse:
    grade_rows = await db.execute(
        select(Scan.grade, func.count(Scan.id))
        .join(Deployment, Scan.deployment_id == Deployment.id)
        .where(Deployment.user_id == user.id)
        .group_by(Scan.grade)
    )
    scan_grades = [ScanGradeBucket(grade=g, count=c) for g, c in grade_rows.all()]

    recent_scores = await db.execute(
        select(Scan.score)
        .join(Deployment, Scan.deployment_id == Deployment.id)
        .where(Deployment.user_id == user.id)
        .order_by(Scan.created_at.desc())
        .limit(20)
    )
    scores = [int(s) for (s,) in recent_scores.all()]

    history_rows = await db.execute(
        select(AlertHistory.created_at).where(AlertHistory.user_id == user.id).order_by(AlertHistory.created_at.desc()).limit(100)
    )
    month_counts: dict[str, int] = {}
    for (created_at,) in history_rows.all():
        key = created_at.strftime("%Y-%m")
        month_counts[key] = month_counts.get(key, 0) + 1
    alert_triggers = [
        AlertTriggerBucket(month=k, count=v) for k, v in sorted(month_counts.items())
    ]

    open_inc = await db.execute(
        select(func.count(IncidentEvent.id)).where(
            IncidentEvent.user_id == user.id,
            IncidentEvent.status == STATUS_OPEN,
        )
    )
    retry_avg = await db.execute(
        select(func.avg(Deployment.retry_count)).where(Deployment.user_id == user.id)
    )
    avg_retry = retry_avg.scalar()

    return AnalyticsOpsResponse(
        scan_grades=scan_grades,
        scan_scores_recent=scores,
        alert_triggers_by_month=alert_triggers,
        open_incidents=int(open_inc.scalar() or 0),
        avg_retry_count=round(float(avg_retry), 2) if avg_retry is not None else 0.0,
    )
