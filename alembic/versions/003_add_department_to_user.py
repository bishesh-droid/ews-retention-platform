"""Add department column to users table

Revision ID: 003_add_department_to_user
Revises: 002_add_prediction_indexes
Create Date: 2026-04-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_add_department_to_user"
down_revision: Union[str, None] = "002_add_prediction_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("department", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "department")

