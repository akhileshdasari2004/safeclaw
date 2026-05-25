"""Persisted billing snapshots for spend validation and alerting."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BillingSnapshot(Base):
    __tablename__ = "billing_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    month_to_date_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deployment_sum_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
