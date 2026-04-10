"""
Add unique constraints for InterventionLog and RiskSnapshot

Revision ID: 005
Revises: 004_add_week_number_to_risk_snapshots
Create Date: 2026-04-10

This migration adds:
1. UniqueConstraint on intervention_logs (student_org_id, week_number, semester_name, intervention_type)
2. UniqueConstraint on risk_snapshots (student_id, week_number, semester_name)

These constraints prevent duplicate entries and enable proper upsert behavior.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '005'
down_revision = '004_add_week_number_to_risk_snapshots'
branch_labels = None
depends_on = None


def upgrade():
    # Add unique constraint on intervention_logs
    op.create_unique_constraint(
        'uq_intervention_log_weekly',
        'intervention_logs',
        ['student_org_id', 'week_number', 'semester_name', 'intervention_type']
    )
    
    # Add unique constraint on risk_snapshots
    op.create_unique_constraint(
        'uq_risk_snapshot_student_week',
        'risk_snapshots',
        ['student_id', 'week_number', 'semester_name']
    )
    
    # NOTE: When migrating to PostgreSQL, verify that cascade behavior 
    # for InterventionLog deletion via Student cascade is properly configured.
    # The SQLite cascade may behave differently than PostgreSQL's.


def downgrade():
    # Remove unique constraints
    op.drop_constraint('uq_intervention_log_weekly', 'intervention_logs', type_='unique')
    op.drop_constraint('uq_risk_snapshot_student_week', 'risk_snapshots', type_='unique')
