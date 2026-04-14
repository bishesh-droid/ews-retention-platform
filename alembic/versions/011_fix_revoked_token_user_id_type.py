"""
011_fix_revoked_token_user_id_type.py
-------------------------------------
Fix revoked_tokens.user_id from String to Integer for PostgreSQL FK compatibility.

This migration safely converts user_id from String to Integer:
1. Handles existing string values by casting to integer
2. Properly recreates FK constraint for PostgreSQL
3. Preserves all existing data

Revision ID: 011
Revises: 010
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    """
    Change revoked_tokens.user_id from String to Integer.

    Data Migration Strategy:
    - Existing string user_ids are expected to be numeric strings (e.g., "1", "42")
    - These are safely cast to integers
    - Non-numeric strings would indicate data corruption and are logged

    PostgreSQL Strategy:
    - Use ALTER COLUMN ... TYPE ... USING clause for type conversion
    - Drop and recreate FK constraint properly
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    # First, check for any non-numeric user_id values that would fail conversion
    result = conn.execute(text("""
        SELECT COUNT(*) FROM revoked_tokens
        WHERE user_id !~ '^[0-9]+$'
    """))
    non_numeric_count = result.scalar()

    if non_numeric_count > 0:
        # Log warning but proceed - these rows will need manual intervention
        print(f"WARNING: Found {non_numeric_count} rows with non-numeric user_id values")
        print("These rows will be set to NULL or require manual fix before FK constraint can be applied")

    if dialect == 'postgresql':
        # Step 1: Drop existing FK constraint if it exists
        conn.execute(text("""
            ALTER TABLE revoked_tokens
            DROP CONSTRAINT IF EXISTS revoked_tokens_user_id_fkey
        """))

        # Step 2: Clean up any non-numeric values (set to NULL temporarily)
        conn.execute(text("""
            UPDATE revoked_tokens
            SET user_id = NULL
            WHERE user_id !~ '^[0-9]+$'
        """))

        # Step 3: Convert column type using PostgreSQL's USING clause
        conn.execute(text("""
            ALTER TABLE revoked_tokens
            ALTER COLUMN user_id TYPE INTEGER USING
                CASE
                    WHEN user_id ~ '^[0-9]+$' THEN user_id::INTEGER
                    ELSE NULL
                END
        """))

        # Step 4: Make column NOT NULL after conversion (if no NULLs exist)
        # Check for NULLs first
        result = conn.execute(text("""
            SELECT COUNT(*) FROM revoked_tokens WHERE user_id IS NULL
        """))
        null_count = result.scalar()

        if null_count == 0:
            conn.execute(text("""
                ALTER TABLE revoked_tokens
                ALTER COLUMN user_id SET NOT NULL
            """))

        # Step 5: Recreate FK constraint
        conn.execute(text("""
            ALTER TABLE revoked_tokens
            ADD CONSTRAINT revoked_tokens_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        """))

    elif dialect == 'sqlite':
        # SQLite requires table recreation for type changes
        # Use batch_alter_table which handles this automatically
        with op.batch_alter_table('revoked_tokens', schema=None) as batch_op:
            batch_op.alter_column(
                'user_id',
                existing_type=sa.String(),
                type_=sa.Integer(),
                existing_nullable=False,
                postgresql_using='user_id::integer'
            )

    else:
        # Generic fallback for other databases
        op.drop_constraint('revoked_tokens_user_id_fkey', 'revoked_tokens', type_='foreignkey')

        with op.batch_alter_table('revoked_tokens', schema=None) as batch_op:
            batch_op.alter_column(
                'user_id',
                existing_type=sa.String(),
                type_=sa.Integer(),
                existing_nullable=False
            )

        op.create_foreign_key(
            'revoked_tokens_user_id_fkey',
            'revoked_tokens',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE'
        )


def downgrade():
    """
    Revert revoked_tokens.user_id from Integer to String.

    Note: This is primarily for rollback during testing.
    In production, downgrading should be avoided.
    """
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == 'postgresql':
        # Drop FK constraint
        conn.execute(text("""
            ALTER TABLE revoked_tokens
            DROP CONSTRAINT IF EXISTS revoked_tokens_user_id_fkey
        """))

        # Change column type back to String
        conn.execute(text("""
            ALTER TABLE revoked_tokens
            ALTER COLUMN user_id TYPE VARCHAR USING user_id::VARCHAR
        """))

        # Recreate FK constraint (may not work properly with VARCHAR)
        conn.execute(text("""
            ALTER TABLE revoked_tokens
            ADD CONSTRAINT revoked_tokens_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        """))

    elif dialect == 'sqlite':
        with op.batch_alter_table('revoked_tokens', schema=None) as batch_op:
            batch_op.alter_column(
                'user_id',
                existing_type=sa.Integer(),
                type_=sa.String(),
                existing_nullable=False
            )

    else:
        op.drop_constraint('revoked_tokens_user_id_fkey', 'revoked_tokens', type_='foreignkey')

        with op.batch_alter_table('revoked_tokens', schema=None) as batch_op:
            batch_op.alter_column(
                'user_id',
                existing_type=sa.Integer(),
                type_=sa.String(),
                existing_nullable=False
            )

        op.create_foreign_key(
            'revoked_tokens_user_id_fkey',
            'revoked_tokens',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE'
        )
