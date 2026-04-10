"""
Add composite index for faculty-scoped student queries

Revision ID: 006
Revises: 005_add_unique_constraints
Create Date: 2026-04-10

This migration adds:
- Composite index on students (parent_department_name, is_active)

This index covers: WHERE parent_department_name = ? AND is_active = true
Used by every faculty-scoped student list query.
"""

from alembic import op

# revision identifiers
revision = '006'
down_revision = '005_add_unique_constraints'
branch_labels = None
depends_on = None


def upgrade():
    # Add composite index for faculty queries
    op.create_index(
        'ix_student_dept_active',
        'students',
        ['parent_department_name', 'is_active']
    )


def downgrade():
    # Remove composite index
    op.drop_index('ix_student_dept_active', 'students')
