"""
Revoked Token Model
-------------------
Stores revoked JWT tokens for token blocklist functionality.
When a user logs out, their token's JTI is added to this table
and the token becomes invalid even before its natural expiration.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from backend.database.connection import Base


class RevokedToken(Base):
    """
    Revoked JWT token blocklist entry.

    Columns:
        id: Primary key (autoincrement)
        jti: JWT Token ID (unique, indexed) - the unique identifier of the revoked token
        user_id: Foreign key to users.id (Integer) - references User.id
        revoked_at: Timestamp when the token was revoked (server default)
        expires_at: Token's original expiration timestamp (for cleanup)
    """

    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jti = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    revoked_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    # Additional index for efficient cleanup queries
    __table_args__ = (
        Index("ix_revoked_tokens_expires_at", "expires_at"),
        Index("ix_revoked_tokens_user_id", "user_id"),
    )
