from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DeploymentEventResponse(BaseModel):
    id: UUID
    deployment_id: UUID
    correlation_id: str
    timestamp: datetime
    level: str
    step: str
    message: str
    metadata: dict | None = Field(default=None, validation_alias="metadata_json")

    model_config = {"from_attributes": True, "populate_by_name": True}


class TimelineStepResponse(BaseModel):
    event_id: UUID
    step: str
    level: str
    message: str
    timestamp: datetime
    duration_ms: int | None = None
    metadata: dict | None = None


class DeploymentTimelineResponse(BaseModel):
    deployment_id: UUID
    correlation_id: str | None
    status: str | None
    provision_state: str | None = None
    retry_count: int = 0
    total_duration_ms: int | None
    step_count: int
    steps: list[TimelineStepResponse]
