"""Add week_number to risk_snapshots

Revision ID: 004_add_week_number_to_risk_snapshots
Revises: 003_add_department_to_user
Create Date: 2026-04-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_add_week_number_to_risk_snapshots"
down_revision: Union[str, None] = "003_add_department_to_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "risk_snapshots",
        sa.Column("week_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "risk_snapshots",
        sa.Column("semester_name", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("risk_snapshots", "semester_name")
    op.drop_column("risk_snapshots", "week_number")
