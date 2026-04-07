"""Add unique constraint and index to enrollments table

Revision ID: 001
Revises:
Create Date: 2026-04-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create composite index for faster joins
    op.create_index(
        'ix_enrollments_student_course',
        'enrollments',
        ['student_id', 'course_id'],
        unique=False
    )

    # Add unique constraint to prevent duplicate enrollments
    # SQLite requires recreating the table for constraints
    # This approach works for both SQLite and PostgreSQL/MySQL
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_enrollment_student_course',
            ['student_id', 'course_id']
        )


def downgrade() -> None:
    # Remove unique constraint
    with op.batch_alter_table('enrollments', schema=None) as batch_op:
        batch_op.drop_constraint('uq_enrollment_student_course', type_='unique')

    # Drop index
    op.drop_index('ix_enrollments_student_course', table_name='enrollments')
