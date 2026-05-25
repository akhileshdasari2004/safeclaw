from uuid import UUID

from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class RecentFailure(BaseModel):
    deployment_id: UUID
    server_name: str
    error_message: str | None
    updated_at: str


class ScanGradeBucket(BaseModel):
    grade: str
    count: int


class AlertTriggerBucket(BaseModel):
    month: str
    count: int


class AnalyticsOpsResponse(BaseModel):
    scan_grades: list[ScanGradeBucket]
    scan_scores_recent: list[int]
    alert_triggers_by_month: list[AlertTriggerBucket]
    open_incidents: int
    avg_retry_count: float


class DashboardOpsResponse(BaseModel):
    deployments_total: int
    deployments_active: int
    deployments_completed: int
    deployments_failed: int
    success_rate_pct: float
    estimated_monthly_spend_usd: float
    avg_security_score: float | None
    scans_total: int
    alerts_enabled: int
    status_breakdown: list[StatusCount]
    recent_failures: list[RecentFailure]
