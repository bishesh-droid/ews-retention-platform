"""
010_add_model_version_index_and_prediction_log.py
-----------------------------------------------
ML-2: Add index on predictions.model_version for queryability.
ML-4: Create prediction_logs table for audit trail of every inference call.

Revision ID: 010
Revises: 009
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = '010'
down_revision = '009'


def upgrade():
    """Add model_version index and prediction_logs table."""
    
    # ML-2: Add index on predictions.model_version if not exists
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check existing indexes on predictions table
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('predictions')]
    
    if 'ix_predictions_model_version' not in existing_indexes:
        op.create_index(
            'ix_predictions_model_version',
            'predictions',
            ['model_version']
        )
    
    # ML-4: Create prediction_logs table
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if prediction_logs table already exists (e.g., created by SQLAlchemy model)
    existing_tables = inspector.get_table_names()
    
    if 'prediction_logs' not in existing_tables:
        op.create_table(
            'prediction_logs',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('student_id', sa.String(), sa.ForeignKey('students.id'), nullable=False, index=True),
            sa.Column('model_version', sa.String(), nullable=False, index=True),
            sa.Column('input_features', sa.JSON(), nullable=True),
            sa.Column('output_score', sa.Float(), nullable=False),
            sa.Column('output_category', sa.String(20), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, index=True),
            sa.Column('source', sa.String(50), nullable=True),
        )
    
    # Add composite index for common queries (check if exists first)
    existing_prediction_indexes = [idx['name'] for idx in inspector.get_indexes('prediction_logs')]
    
    if 'ix_prediction_logs_student_created' not in existing_prediction_indexes:
        op.create_index(
            'ix_prediction_logs_student_created',
            'prediction_logs',
            ['student_id', 'created_at']
        )
    if 'ix_prediction_logs_model_version' not in existing_prediction_indexes:
        op.create_index(
            'ix_prediction_logs_model_version',
            'prediction_logs',
            ['model_version']
        )


def downgrade():
    """Remove model_version index and prediction_logs table."""
    
    # Drop prediction_logs table and its indexes
    op.drop_index('ix_prediction_logs_model_version', 'prediction_logs')
    op.drop_index('ix_prediction_logs_student_created', 'prediction_logs')
    op.drop_table('prediction_logs')
    
    # Drop model_version index from predictions
    op.drop_index('ix_predictions_model_version', 'predictions')
