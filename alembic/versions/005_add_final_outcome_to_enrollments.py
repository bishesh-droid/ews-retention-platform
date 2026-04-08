"""Add final_outcome to enrollments

Revision ID: 005_add_final_outcome_to_enrollments
Revises: 004_add_week_number_to_risk_snapshots
Create Date: 2026-04-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_add_final_outcome_to_enrollments"
down_revision: Union[str, None] = "004_add_week_number_to_risk_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "enrollments",
        sa.Column("final_outcome", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "enrollments",
        sa.Column("outcome_source", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "enrollments",
        sa.Column("outcome_updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("enrollments", "outcome_updated_at")
    op.drop_column("enrollments", "outcome_source")
    op.drop_column("enrollments", "final_outcome")
