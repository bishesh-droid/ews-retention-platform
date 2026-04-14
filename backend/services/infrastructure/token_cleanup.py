"""
Token Cleanup Service
-----------------------
Utility for cleaning up expired revoked tokens from the database.

This module provides a function to purge revoked tokens that have
passed their expiration date, preventing the revoked_tokens table
from growing indefinitely.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from backend.database.models.revoked_token import RevokedToken


def purge_expired_revoked_tokens(db: Session) -> int:
    """
    Delete all revoked tokens where expires_at < current UTC time.

    Args:
        db: SQLAlchemy database session

    Returns:
        Number of rows deleted

    Example:
        from backend.database.connection import SessionLocal
        db = SessionLocal()
        try:
            deleted_count = purge_expired_revoked_tokens(db)
            print(f"Purged {deleted_count} expired tokens")
        finally:
            db.close()
    """
    now = datetime.utcnow()

    # Query for expired tokens
    expired_tokens = db.query(RevokedToken).filter(
        RevokedToken.expires_at < now
    )

    # Count before deletion
    count = expired_tokens.count()

    # Delete expired tokens
    if count > 0:
        expired_tokens.delete(synchronize_session=False)
        db.commit()

    return count
