import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.deployment_event import DeploymentEvent
    from app.models.incident_event import IncidentEvent
    from app.models.provision_job import ProvisionJob
    from app.models.scan import Scan
    from app.models.user import User


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    region: Mapped[str] = mapped_column(String(64), nullable=False)
    server_name: Mapped[str] = mapped_column(String(128), nullable=False)
    plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    monthly_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    provider_server_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    encrypted_ssh_private_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    provision_state: Mapped[str] = mapped_column(String(32), default="QUEUED", nullable=False)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    ssh_key_version: Mapped[int] = mapped_column(default=1, nullable=False)
    ssh_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="deployments")
    scans: Mapped[list["Scan"]] = relationship(back_populates="deployment")
    events: Mapped[list["DeploymentEvent"]] = relationship(
        back_populates="deployment",
        order_by="DeploymentEvent.timestamp",
    )
    provision_jobs: Mapped[list["ProvisionJob"]] = relationship(back_populates="deployment")
    incidents: Mapped[list["IncidentEvent"]] = relationship(back_populates="deployment")
