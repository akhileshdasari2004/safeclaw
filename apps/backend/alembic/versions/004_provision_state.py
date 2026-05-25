"""Provision state machine columns

Revision ID: 004
Revises: 003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deployments",
        sa.Column("provision_state", sa.String(32), nullable=False, server_default="QUEUED"),
    )
    op.add_column(
        "deployments",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("deployments", "retry_count")
    op.drop_column("deployments", "provision_state")
