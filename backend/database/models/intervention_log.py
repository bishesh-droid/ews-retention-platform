"""
Intervention Log Model
----------------------
Tracks intervention recommendations, advisor actions, and outcome measurements.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime, UniqueConstraint
from backend.database.connection import Base


class InterventionLog(Base):
    """
    Logs intervention recommendations and tracks advisor actions & outcomes.
    """
    __tablename__ = "intervention_logs"

    __table_args__ = (
        UniqueConstraint(
            'student_org_id', 'week_number', 'semester_name', 'intervention_type',
            name='uq_intervention_log_weekly'
        ),
    )

    id = Column(Integer, primary_key=True)
    student_org_id = Column(String(64), ForeignKey("students.org_defined_id"), nullable=False, index=True)
    recommended_at = Column(DateTime, default=datetime.utcnow, index=True)
    intervention_type = Column(String(64))  # "gentle_reminder"|"mentor_outreach"|"urgent"|etc.
    engagement_pattern = Column(String(32), nullable=True)
    risk_score_at_recommendation = Column(Float)
    week_number = Column(Integer, nullable=True)
    semester_name = Column(String(64), nullable=True)

    # Advisor action fields
    reviewed = Column(Boolean, default=False)
    acted_on = Column(Boolean, nullable=True)  # null = not yet reviewed
    acted_on_at = Column(DateTime, nullable=True)
    acted_on_by = Column(String(128), nullable=True)
    dismissed_reason = Column(String(256), nullable=True)
    notes = Column(Text, nullable=True)

    # Outcome tracking (populated by next ingestion run, >= 7 days after recommendation)
    follow_up_risk_score = Column(Float, nullable=True)
    follow_up_at = Column(DateTime, nullable=True)
    outcome = Column(String(32), nullable=True)  # "improved"|"unchanged"|"worsened"|"pending"
    outcome_delta = Column(Float, nullable=True)  # current_score - recommendation_score
