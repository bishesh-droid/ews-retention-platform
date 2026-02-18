from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..connection import Base # Corrected import for Base

class AuditLog(Base):
    """Structured audit trail for system actions"""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user_role = Column(String)
    action_type = Column(String)  # risk_change, signal_update, login, export, ai_generation
    affected_student_id = Column(String, index=True)
    details = Column(JSON)  # Store specific action data

    user = relationship("User", back_populates="audit_trail")
