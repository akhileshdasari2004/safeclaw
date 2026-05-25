"""Persistent deployment events

Revision ID: 003
Revises: 002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deployments",
        sa.Column("correlation_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_deployments_correlation_id", "deployments", ["correlation_id"])

    op.create_table(
        "deployment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deployment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deployments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("step", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_deployment_events_deployment_id", "deployment_events", ["deployment_id"])
    op.create_index("ix_deployment_events_timestamp", "deployment_events", ["timestamp"])
    op.create_index("ix_deployment_events_correlation_id", "deployment_events", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_deployment_events_correlation_id", "deployment_events")
    op.drop_index("ix_deployment_events_timestamp", "deployment_events")
    op.drop_index("ix_deployment_events_deployment_id", "deployment_events")
    op.drop_table("deployment_events")
    op.drop_index("ix_deployments_correlation_id", "deployments")
    op.drop_column("deployments", "correlation_id")
