from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IncidentResponse(BaseModel):
    id: UUID
    deployment_id: UUID | None
    severity: str
    status: str
    title: str
    description: str | None
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}
