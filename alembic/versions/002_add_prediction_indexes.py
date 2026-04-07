"""Add indexes to predictions.student_id and predictions.risk_score

Revision ID: 002
Revises: 001
Create Date: 2026-04-07

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create index on student_id for faster joins to students table
    op.create_index(
        'ix_predictions_student_id',
        'predictions',
        ['student_id'],
        unique=False
    )

    # Create index on risk_score for ORDER BY / filtering operations
    op.create_index(
        'ix_predictions_risk_score',
        'predictions',
        ['risk_score'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_predictions_risk_score', table_name='predictions')
    op.drop_index('ix_predictions_student_id', table_name='predictions')
