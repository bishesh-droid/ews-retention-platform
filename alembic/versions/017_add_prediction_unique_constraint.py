"""
017_add_prediction_unique_constraint.py
---------------------------------------
Add unique constraint and prediction_date column for Prediction model

Revision ID: 017
Revises: 016
Create Date: 2026-04-16

This migration adds:
1. prediction_date column to predictions table
2. UniqueConstraint on predictions (student_id, prediction_date)

These constraints prevent duplicate predictions per student per day
and enable proper upsert behavior in the scheduler.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade():
    # Add prediction_date column
    op.add_column(
        'predictions',
        sa.Column('prediction_date', sa.DateTime(), nullable=True)
    )
    
    # Add unique constraint on predictions
    op.create_unique_constraint(
        'uq_prediction_student_date',
        'predictions',
        ['student_id', 'prediction_date']
    )


def downgrade():
    # Remove unique constraint
    op.drop_constraint('uq_prediction_student_date', 'predictions', type_='unique')
    
    # Remove prediction_date column
    op.drop_column('predictions', 'prediction_date')
