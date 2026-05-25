"""billing snapshots table

Revision ID: 005
Revises: 004
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("month_to_date_usd", sa.Numeric(12, 2), nullable=False),
        sa.Column("deployment_sum_usd", sa.Numeric(12, 2), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_billing_snapshots_provider", "billing_snapshots", ["provider"])
    op.create_index("ix_billing_snapshots_captured_at", "billing_snapshots", ["captured_at"])


def downgrade() -> None:
    op.drop_index("ix_billing_snapshots_captured_at", table_name="billing_snapshots")
    op.drop_index("ix_billing_snapshots_provider", table_name="billing_snapshots")
    op.drop_table("billing_snapshots")
