from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..connection import Base  # Corrected import for Base


class AuditLog(Base):
    """
    FERPA-compliant audit trail for data access.

    Tracks who accessed what student data and when, for compliance
    with FERPA requirements for educational records access logging.
    """
    __tablename__ = "audit_logs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # User information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_role = Column(String(50), index=True)  # faculty, admin, retention team, etc.

    # Action details (READ/WRITE/DELETE for data access auditing)
    action = Column(String(20), nullable=False, index=True)  # READ, WRITE, DELETE
    resource_type = Column(String(50), nullable=False, index=True)  # student, enrollment, grade, etc.
    resource_id = Column(String(50), nullable=False, index=True)  # student_id, enrollment_id, etc.

    # Network/request context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    request_id = Column(String(100), nullable=True, index=True)  # For tracing across logs

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Legacy fields (maintained for backward compatibility)
    action_type = Column(String(50))  # risk_change, signal_update, login, export, ai_generation
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
