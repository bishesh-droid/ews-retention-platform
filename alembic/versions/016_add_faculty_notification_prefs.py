"""Add faculty_notification_prefs table

Revision ID: 016_add_faculty_notification_prefs
Revises: 015_fix_remaining_datetime_columns
Create Date: 2026-04-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "016_add_faculty_notification_prefs"
down_revision: Union[str, None] = "015_fix_remaining_datetime_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "faculty_notification_prefs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("notify_on_high_risk", sa.Boolean(), default=True, nullable=False),
        sa.Column("notify_on_critical_risk", sa.Boolean(), default=True, nullable=False),
        sa.Column("notification_channel", sa.String(20), default="email", nullable=False),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column("email_override", sa.String(200), nullable=True),
        sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cooldown_hours", sa.Integer(), default=24, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
    )
    op.create_index("ix_faculty_notification_prefs_user_id", "faculty_notification_prefs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_faculty_notification_prefs_user_id", table_name="faculty_notification_prefs")
    op.drop_table("faculty_notification_prefs")
