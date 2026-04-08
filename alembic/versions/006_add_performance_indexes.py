"""
Add performance indexes for frequently queried columns (DB-1)

Revision ID: 006
Revises: 005_add_final_outcome_to_enrollments
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005_add_final_outcome_to_enrollments'
branch_labels = None
depends_on = None


def upgrade():
    # Enrollment indexes
    op.create_index('ix_enrollment_last_login', 'enrollments', ['last_system_login'])
    op.create_index('ix_enrollment_last_visited', 'enrollments', ['last_visited_date'])
    op.create_index('ix_enrollment_student_id', 'enrollments', ['student_id'])
    op.create_index('ix_enrollment_course_code', 'enrollments', ['course_id'])
    
    # Add unique constraint on enrollment (student_id, course_id)
    op.create_unique_constraint(
        'uq_enrollment_student_course', 
        'enrollments', 
        ['student_id', 'course_id']
    )
    
    # Student indexes
    op.create_index('ix_student_department', 'students', ['parent_department_name'])
    op.create_index('ix_student_org_id', 'students', ['org_defined_id'])
    op.create_index('ix_student_is_active', 'students', ['is_active'])
    
    # RiskSnapshot indexes
    op.create_index('ix_risk_snapshot_student', 'risk_snapshots', ['student_id'])
    op.create_index('ix_risk_snapshot_timestamp', 'risk_snapshots', ['timestamp'])
    op.create_index('ix_risk_snapshot_week', 'risk_snapshots', ['week_number'])


def downgrade():
    # RiskSnapshot indexes
    op.drop_index('ix_risk_snapshot_week', 'risk_snapshots')
    op.drop_index('ix_risk_snapshot_timestamp', 'risk_snapshots')
    op.drop_index('ix_risk_snapshot_student', 'risk_snapshots')
    
    # Student indexes
    op.drop_index('ix_student_is_active', 'students')
    op.drop_index('ix_student_org_id', 'students')
    op.drop_index('ix_student_department', 'students')
    
    # Enrollment unique constraint
    op.drop_constraint('uq_enrollment_student_course', 'enrollments', type_='unique')
    
    # Enrollment indexes
    op.drop_index('ix_enrollment_course_code', 'enrollments')
    op.drop_index('ix_enrollment_student_id', 'enrollments')
    op.drop_index('ix_enrollment_last_visited', 'enrollments')
    op.drop_index('ix_enrollment_last_login', 'enrollments')
