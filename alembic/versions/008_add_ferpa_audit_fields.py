"""
008_add_ferpa_audit_fields.py
------------------------------
Add FERPA-compliant data access audit fields to the audit_logs table.

This migration adds columns required for FERPA compliance:
- action: READ/WRITE/DELETE
- resource_type: type of resource accessed
- resource_id: unique identifier of resource
- ip_address: source IP for access tracking
- request_id: for tracing across log systems

Revision ID: 008
Revises: 007
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers
revision = '008'
down_revision = '007'


def upgrade():
    """Add FERPA audit fields to audit_logs table."""
    # Check if columns already exist (in case of partial migration)
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('audit_logs')]

    # Add action column if not exists
    if 'action' not in columns:
        op.add_column(
            'audit_logs',
            sa.Column('action', sa.String(20), nullable=True, index=True)
        )
        # Populate with default value for existing records
        op.execute("UPDATE audit_logs SET action = 'WRITE' WHERE action IS NULL")

    # Add resource_type column if not exists
    if 'resource_type' not in columns:
        op.add_column(
            'audit_logs',
            sa.Column('resource_type', sa.String(50), nullable=True, index=True)
        )

    # Add resource_id column if not exists
    if 'resource_id' not in columns:
        op.add_column(
            'audit_logs',
            sa.Column('resource_id', sa.String(50), nullable=True, index=True)
        )
        # Populate from affected_student_id if available
        op.execute("""
            UPDATE audit_logs 
            SET resource_id = affected_student_id 
            WHERE resource_id IS NULL AND affected_student_id IS NOT NULL
        """)

    # Add ip_address column if not exists
    if 'ip_address' not in columns:
        op.add_column(
            'audit_logs',
            sa.Column('ip_address', sa.String(45), nullable=True)
        )

    # Add request_id column if not exists
    if 'request_id' not in columns:
        op.add_column(
            'audit_logs',
            sa.Column('request_id', sa.String(100), nullable=True, index=True)
        )

    # Add indexes for efficient querying
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_resource_id', 'audit_logs', ['resource_id'])
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'])
    op.create_index('ix_audit_logs_timestamp_action', 'audit_logs', ['timestamp', 'action'])


def downgrade():
    """Remove FERPA audit fields from audit_logs table."""
    # Drop indexes
    op.drop_index('ix_audit_logs_timestamp_action', 'audit_logs')
    op.drop_index('ix_audit_logs_request_id', 'audit_logs')
    op.drop_index('ix_audit_logs_resource_id', 'audit_logs')
    op.drop_index('ix_audit_logs_resource_type', 'audit_logs')
    op.drop_index('ix_audit_logs_action', 'audit_logs')

    # Drop columns
    op.drop_column('audit_logs', 'request_id')
    op.drop_column('audit_logs', 'ip_address')
    op.drop_column('audit_logs', 'resource_id')
    op.drop_column('audit_logs', 'resource_type')
    op.drop_column('audit_logs', 'action')
