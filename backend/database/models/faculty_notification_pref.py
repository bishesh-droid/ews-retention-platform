"""Faculty Notification Preferences Model

E-1 Enhancement: Webhook/email notification system for faculty risk threshold alerts.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from ..connection import Base


class FacultyNotificationPref(Base):
    """Faculty notification preferences for risk threshold alerts.

    Stores per-faculty configuration for receiving alerts when students cross
    HIGH (70) or CRITICAL (85) risk thresholds.

    Database Integrity:
    - user_id references users.id with unique constraint (one prefs record per user)
    - notification_channel must be 'email' or 'webhook'
    - cooldown_hours prevents alert spam (default 24 hours)
    """

    __tablename__ = "faculty_notification_prefs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    notify_on_high_risk = Column(Boolean, default=True, nullable=False)
    notify_on_critical_risk = Column(Boolean, default=True, nullable=False)
    notification_channel = Column(
        String(20), default="email", nullable=False
    )  # email | webhook
    webhook_url = Column(String(500), nullable=True)
    email_override = Column(String(200), nullable=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    cooldown_hours = Column(Integer, default=24, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="notification_pref")

    __table_args__ = (Index("ix_faculty_notification_prefs_user_id", "user_id"),)
