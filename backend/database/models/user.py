from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from ..connection import Base

class User(Base):
    """System users with RBAC roles"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # Student, Faculty, Admin, Retention Team
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSON, default=dict)  # UI and notification preferences per user

    # Relationships
    audit_trail = relationship("AuditLog", back_populates="user")
