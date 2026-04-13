"""
009_add_revoked_tokens_table.py
---------------------------------
Add revoked_tokens table for JWT token blocklist functionality.

This migration creates the revoked_tokens table to store JWT tokens
that have been explicitly revoked (e.g., on logout) before their
natural expiration. This enables proper token invalidation.

Revision ID: 009
Revises: 008
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '009'
down_revision = '008'


def upgrade():
    """Create revoked_tokens table with indexes."""
    op.create_table(
        'revoked_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jti', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('jti')
    )
    
    # Create indexes for efficient queries
    op.create_index('ix_revoked_tokens_jti', 'revoked_tokens', ['jti'])
    op.create_index('ix_revoked_tokens_expires_at', 'revoked_tokens', ['expires_at'])
    op.create_index('ix_revoked_tokens_user_id', 'revoked_tokens', ['user_id'])


def downgrade():
    """Drop revoked_tokens table and indexes."""
    op.drop_index('ix_revoked_tokens_user_id', 'revoked_tokens')
    op.drop_index('ix_revoked_tokens_expires_at', 'revoked_tokens')
    op.drop_index('ix_revoked_tokens_jti', 'revoked_tokens')
    op.drop_table('revoked_tokens')
