from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AlertCreateRequest(BaseModel):
    threshold: Decimal = Field(gt=0)
    enabled: bool = True


class AlertUpdateRequest(BaseModel):
    threshold: Decimal | None = Field(default=None, gt=0)
    enabled: bool | None = None


class AlertResponse(BaseModel):
    id: UUID
    threshold: Decimal
    enabled: bool
    last_triggered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
