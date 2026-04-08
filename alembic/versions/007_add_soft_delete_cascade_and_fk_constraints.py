"""
Add soft delete to Student, cascade rules, and non-nullable FKs

Revision ID: 007
Revises: 006_add_performance_indexes
Create Date: 2026-04-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006_add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # FIX 1: Add soft delete columns to students (CROSS-1)
    # =========================================================================
    
    # Ensure is_active exists with proper default (should already exist, but ensure nullable=False)
    op.alter_column('students', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=False,
                    server_default=sa.true())
    
    # Add deactivated_at timestamp
    op.add_column('students',
                  sa.Column('deactivated_at', sa.DateTime(), nullable=True))
    
    # Add deactivation_reason (values: "not_in_latest_export" | "manual" | "withdrawn")
    op.add_column('students',
                  sa.Column('deactivation_reason', sa.String(128), nullable=True))
    
    # Create index on is_active for efficient filtering
    op.create_index('ix_students_is_active', 'students', ['is_active'])
    
    # =========================================================================
    # FIX 3: Make student_id non-nullable with CASCADE (DB-4)
    # =========================================================================
    
    # First, clean up any existing NULLs (assign to a placeholder or delete)
    # In practice, you might want to handle these manually; this is a safety cleanup
    op.execute("DELETE FROM enrollments WHERE student_id IS NULL")
    
    # Alter student_id to be non-nullable with CASCADE
    op.alter_column('enrollments', 'student_id',
                    existing_type=sa.String(),
                    nullable=False)
    
    # Update the foreign key constraint to add ON DELETE CASCADE
    # (SQLite may not support this well; for SQLite we just document it)
    # For PostgreSQL/MySQL:
    try:
        op.drop_constraint('enrollments_student_id_fkey', 'enrollments', type_='foreignkey')
    except:
        pass  # Constraint may not exist with that name
    
    op.create_foreign_key(
        'fk_enrollments_student_id',
        'enrollments', 'students',
        ['student_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Update course_id FK to have ON DELETE SET NULL
    try:
        op.drop_constraint('enrollments_course_id_fkey', 'enrollments', type_='foreignkey')
    except:
        pass
    
    op.create_foreign_key(
        'fk_enrollments_course_id',
        'enrollments', 'courses',
        ['course_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # =========================================================================
    # Downgrade: Reverse the changes
    # =========================================================================
    
    # Drop soft delete columns
    op.drop_column('students', 'deactivated_at')
    op.drop_column('students', 'deactivation_reason')
    
    # Make is_active nullable again
    op.alter_column('students', 'is_active',
                    existing_type=sa.Boolean(),
                    nullable=True)
    
    # Drop index
    op.drop_index('ix_students_is_active', 'students')
    
    # Revert FK changes (make nullable again, remove CASCADE)
    try:
        op.drop_constraint('fk_enrollments_student_id', 'enrollments', type_='foreignkey')
    except:
        pass
    try:
        op.drop_constraint('fk_enrollments_course_id', 'enrollments', type_='foreignkey')
    except:
        pass
    
    # Make student_id nullable again
    op.alter_column('enrollments', 'student_id',
                    existing_type=sa.String(),
                    nullable=True)
    
    # Recreate original FKs without CASCADE (simple references)
    op.create_foreign_key(
        'enrollments_student_id_fkey',
        'enrollments', 'students',
        ['student_id'], ['id']
    )
    op.create_foreign_key(
        'enrollments_course_id_fkey',
        'enrollments', 'courses',
        ['course_id'], ['id']
    )
