from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ScanFindingSchema(BaseModel):
    severity: Literal["critical", "high", "medium", "low", "info"]
    title: str
    description: str
    remediation: str


class ScanResultSchema(BaseModel):
    score: int
    grade: str
    findings: list[ScanFindingSchema] = Field(default_factory=list)
    risk_summary: str = ""


class ScanResponse(BaseModel):
    id: UUID
    deployment_id: UUID
    score: int
    grade: str
    findings: ScanResultSchema
    created_at: datetime

    model_config = {"from_attributes": True}
