from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DeployCreateRequest(BaseModel):
    provider: Literal["hetzner", "digitalocean"]
    region: str
    server_name: str = Field(min_length=3, max_length=64, pattern=r"^[a-z0-9-]+$")
    plan_id: str
    ssh_public_key: str = Field(min_length=50)
    ssh_private_key: str | None = Field(
        default=None,
        description="Optional PEM private key; encrypted at rest if provided",
    )
    idempotency_key: str | None = Field(default=None, max_length=64)


class DeployResponse(BaseModel):
    id: UUID
    provider: str
    region: str
    server_name: str
    ip_address: str | None
    status: str
    monthly_cost: Decimal | None
    logs: str | None
    error_message: str | None
    provision_state: str | None = None
    retry_count: int = 0
    correlation_id: str | None = None
    ssh_key_version: int = 1
    ssh_rotated_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RotateSshRequest(BaseModel):
    new_public_key: str = Field(min_length=50)
    new_private_key: str = Field(min_length=50, description="PEM private key matching new_public_key")


class RegionItem(BaseModel):
    id: str
    name: str
    country: str | None = None


class PlanItem(BaseModel):
    id: str
    name: str
    vcpus: int
    memory_gb: int
    disk_gb: int
    monthly_cost_usd: float


class ProviderRegionsResponse(BaseModel):
    provider: str
    regions: list[RegionItem]


class ProviderPlansResponse(BaseModel):
    provider: str
    plans: list[PlanItem]
