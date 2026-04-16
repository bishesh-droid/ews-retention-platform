from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, event
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..connection import Base  # Corrected import for Base


# FERPA: AuditLog append-only enforcement
# For SQLite: Application-level guard using SQLAlchemy events
# For PostgreSQL production: Use DDL trigger or RLS policy instead of application guard
# Example PostgreSQL trigger:
#   CREATE OR REPLACE FUNCTION prevent_audit_update_delete()
#   RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION 'AuditLog is append-only'; END; $$ LANGUAGE plpgsql;
#   CREATE TRIGGER audit_log_append_only BEFORE UPDATE OR DELETE ON audit_logs
#   FOR EACH ROW EXECUTE FUNCTION prevent_audit_update_delete();


class AuditLog(Base):
    """
    FERPA-compliant audit trail for data access.

    Tracks who accessed what student data and when, for compliance
    with FERPA requirements for educational records access logging.

    IMPORTANT: This table is append-only. Records cannot be updated or deleted
    to maintain a complete audit trail. Application-level enforcement is used
    for SQLite; PostgreSQL production should use DDL triggers or RLS policies.
    """

    __tablename__ = "audit_logs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # User information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_role = Column(String(50), index=True)  # faculty, admin, retention team, etc.

    # Action details (READ/WRITE/DELETE for data access auditing)
    action = Column(String(20), nullable=False, index=True)  # READ, WRITE, DELETE
    resource_type = Column(
        String(50), nullable=False, index=True
    )  # student, enrollment, grade, etc.
    resource_id = Column(
        String(50), nullable=False, index=True
    )  # student_id, enrollment_id, etc.

    # Network/request context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    request_id = Column(
        String(100), nullable=True, index=True
    )  # For tracing across logs

    # Timestamp
    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    # Legacy fields (maintained for backward compatibility)
    action_type = Column(
        String(50)
    )  # risk_change, signal_update, login, export, ai_generation
    affected_student_id = Column(String(50), index=True)
    details = Column(JSON)  # Store specific action data

    # Relationships
    user = relationship("User", back_populates="audit_trail")

    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, user_id={self.user_id}, action={self.action}, "
            f"resource_type={self.resource_type}, resource_id={self.resource_id}, "
            f"timestamp={self.timestamp})>"
        )


# SQLite application-level guard: prevent UPDATE and DELETE on audit_logs
@event.listens_for(AuditLog, "before_update")
def prevent_audit_update(mapper, connection, target):
    """Raise RuntimeError if attempting to update an AuditLog record."""
    raise RuntimeError("AuditLog is append-only: UPDATE operations are prohibited")


@event.listens_for(AuditLog, "before_delete")
def prevent_audit_delete(mapper, connection, target):
    """Raise RuntimeError if attempting to delete an AuditLog record."""
    raise RuntimeError("AuditLog is append-only: DELETE operations are prohibited")
