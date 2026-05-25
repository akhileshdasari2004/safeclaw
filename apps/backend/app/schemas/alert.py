from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AlertCreateRequest(BaseModel):
    threshold: Decimal = Field(gt=0)
    enabled: bool = True
    cooldown_hours: int = Field(default=24, ge=1, le=168)


class AlertUpdateRequest(BaseModel):
    threshold: Decimal | None = Field(default=None, gt=0)
    enabled: bool | None = None
    cooldown_hours: int | None = Field(default=None, ge=1, le=168)


class AlertResponse(BaseModel):
    id: UUID
    threshold: Decimal
    enabled: bool
    cooldown_hours: int
    last_triggered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertHistoryResponse(BaseModel):
    id: UUID
    provider: str | None
    current_spend: Decimal
    threshold: Decimal
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
