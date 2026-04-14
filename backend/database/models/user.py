from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from ..connection import Base


class User(Base):
    """System users with RBAC roles

    Database Integrity:
    - username, email, hashed_password, role are NOT NULL (required fields)
    - created_at uses timezone-aware UTC datetime
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # student, faculty, admin, retention team
    department = Column(String, nullable=True)  # Department scope for faculty accounts
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    preferences = Column(JSON, default=dict)  # UI and notification preferences per user

    # Relationships
    audit_trail = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        # Ensure role is one of the allowed values
        CheckConstraint(
            "role IN ('student', 'faculty', 'admin', 'retention team')",
            name="check_valid_role"
        ),
    )
