from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ScanIssueSchema(BaseModel):
    severity: Literal["critical", "high", "medium", "low", "info"]
    description: str
    remediation: str


class ScanResultSchema(BaseModel):
    score: int
    grade: str
    issues: list[ScanIssueSchema]


class ScanResponse(BaseModel):
    id: UUID
    deployment_id: UUID
    score: int
    grade: str
    findings: ScanResultSchema
    created_at: datetime

    model_config = {"from_attributes": True}
