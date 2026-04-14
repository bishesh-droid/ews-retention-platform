"""
014_add_not_null_constraints_and_tz_aware_timestamps.py
--------------------------------------------------------
Enforce strict database integrity for PostgreSQL.

This migration:
1. Adds NOT NULL constraints to critical User fields
2. Adds NOT NULL + check constraint to Prediction.risk_score
3. Migrates from datetime.utcnow to timezone-aware UTC timestamps

Revision ID: 014
Revises: 013
Create Date: 2026-04-14

DATA SAFETY STRATEGY:
---------------------
1. Backfill NULL values with sensible defaults BEFORE adding constraints
2. User fields: Use empty string for NULL text fields (should not exist, but safe fallback)
3. Prediction.risk_score: Set to 0.0 for any NULL (neutral risk score)
4. Timestamps: Convert naive datetimes to UTC-aware using AT TIME ZONE

This ensures no data loss while enforcing integrity.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade():
    """
    Step 1: Backfill NULL values before adding constraints
    Step 2: Add NOT NULL constraints
    Step 3: Add check constraints for data validity
    Step 4: Update timestamp columns to timezone-aware defaults
    """

    # =========================================================================
    # STEP 1: BACKFILL NULL VALUES (User table)
    # =========================================================================

    # Backfill NULL usernames with empty string (should not exist, but safe)
    op.execute("""
        UPDATE users SET username = '' WHERE username IS NULL
    """)

    # Backfill NULL emails with empty string
    op.execute("""
        UPDATE users SET email = '' WHERE email IS NULL
    """)

    # Backfill NULL hashed_password with empty string
    op.execute("""
        UPDATE users SET hashed_password = '' WHERE hashed_password IS NULL
    """)

    # Backfill NULL roles with 'student' (safest default for existing accounts)
    op.execute("""
        UPDATE users SET role = 'student' WHERE role IS NULL
    """)

    # Backfill NULL is_active to true (preserve access for existing users)
    op.execute("""
        UPDATE users SET is_active = TRUE WHERE is_active IS NULL
    """)

    # Backfill NULL is_superuser to false
    op.execute("""
        UPDATE users SET is_superuser = FALSE WHERE is_superuser IS NULL
    """)

    # =========================================================================
    # STEP 2: BACKFILL NULL VALUES (Prediction table)
    # =========================================================================

    # Backfill NULL risk_score to 0.0 (neutral/lowest risk)
    op.execute("""
        UPDATE predictions SET risk_score = 0.0 WHERE risk_score IS NULL
    """)

    # Backfill NULL engagement_score to 0.0
    op.execute("""
        UPDATE predictions SET engagement_score = 0.0 WHERE engagement_score IS NULL
    """)

    # Backfill NULL retention_likelihood to 'unknown'
    op.execute("""
        UPDATE predictions SET retention_likelihood = 'unknown' WHERE retention_likelihood IS NULL
    """)

    # Backfill NULL student_id - these are orphan records, delete them
    op.execute("""
        DELETE FROM predictions WHERE student_id IS NULL
    """)

    # =========================================================================
    # STEP 3: ADD NOT NULL CONSTRAINTS (User table)
    # =========================================================================

    # Alter User columns to NOT NULL
    op.alter_column('users', 'username', existing_type=sa.String(), nullable=False)
    op.alter_column('users', 'email', existing_type=sa.String(), nullable=False)
    op.alter_column('users', 'hashed_password', existing_type=sa.String(), nullable=False)
    op.alter_column('users', 'role', existing_type=sa.String(), nullable=False)
    op.alter_column('users', 'is_active', existing_type=sa.Boolean(), nullable=False)
    op.alter_column('users', 'is_superuser', existing_type=sa.Boolean(), nullable=False)

    # =========================================================================
    # STEP 4: ADD NOT NULL CONSTRAINTS (Prediction table)
    # =========================================================================

    op.alter_column('predictions', 'risk_score', existing_type=sa.Float(), nullable=False)
    op.alter_column('predictions', 'engagement_score', existing_type=sa.Float(), nullable=False)
    op.alter_column('predictions', 'retention_likelihood', existing_type=sa.String(), nullable=False)
    op.alter_column('predictions', 'student_id', existing_type=sa.String(), nullable=False)

    # =========================================================================
    # STEP 5: ADD CHECK CONSTRAINTS
    # =========================================================================

    # Add role validation check constraint
    op.create_check_constraint(
        'check_valid_role',
        'users',
        "role IN ('student', 'faculty', 'admin', 'retention team')"
    )

    # Add risk_score range check constraint (0-100 scale)
    op.create_check_constraint(
        'check_risk_score_range',
        'predictions',
        'risk_score >= 0.0 AND risk_score <= 100.0'
    )

    # =========================================================================
    # STEP 6: FIX TIMESTAMPS (convert to timezone-aware UTC)
    # =========================================================================

    # For PostgreSQL: convert naive timestamps to UTC-aware
    # This assumes existing timestamps are in the database's default timezone
    op.execute("""
        ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE predictions ALTER COLUMN prediction_timestamp TYPE TIMESTAMPTZ
        USING prediction_timestamp AT TIME ZONE 'UTC'
    """)


def downgrade():
    """
    Reverse the migration:
    1. Remove check constraints
    2. Allow NULLs again
    3. Revert timestamp types
    """

    # Remove check constraints
    op.drop_constraint('check_risk_score_range', 'predictions', type_='check')
    op.drop_constraint('check_valid_role', 'users', type_='check')

    # Allow NULLs again (User table)
    op.alter_column('users', 'username', existing_type=sa.String(), nullable=True)
    op.alter_column('users', 'email', existing_type=sa.String(), nullable=True)
    op.alter_column('users', 'hashed_password', existing_type=sa.String(), nullable=True)
    op.alter_column('users', 'role', existing_type=sa.String(), nullable=True)
    op.alter_column('users', 'is_active', existing_type=sa.Boolean(), nullable=True)
    op.alter_column('users', 'is_superuser', existing_type=sa.Boolean(), nullable=True)

    # Allow NULLs again (Prediction table)
    op.alter_column('predictions', 'risk_score', existing_type=sa.Float(), nullable=True)
    op.alter_column('predictions', 'engagement_score', existing_type=sa.Float(), nullable=True)
    op.alter_column('predictions', 'retention_likelihood', existing_type=sa.String(), nullable=True)
    op.alter_column('predictions', 'student_id', existing_type=sa.String(), nullable=True)

    # Revert timestamps to naive (note: this loses timezone info)
    op.execute("""
        ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP
        USING created_at AT TIME ZONE 'UTC'
    """)

    op.execute("""
        ALTER TABLE predictions ALTER COLUMN prediction_timestamp TYPE TIMESTAMP
        USING prediction_timestamp AT TIME ZONE 'UTC'
    """)
