"""
Feature Model
------------
Database model for student response tracking (feedback loop).
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.database.connection import Base


class StudentResponse(Base):
    """
    Tracks student responses to interventions for feedback loop analysis.
    Enables measurement of intervention effectiveness and model improvement.
    """
    __tablename__ = "student_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    intervention_id = Column(Integer, ForeignKey("interventions.id"))
    
    # ========== Response Tracking ==========
    responded = Column(Boolean)  # Did the student respond to the intervention?
    response_time_hours = Column(Float)  # How long until response?
    behavioral_change_detected = Column(Boolean)  # Was there observable behavior change?
    
    # ========== Outcome Tracking (7-day window) ==========
    engagement_change_7days = Column(Float)  # % change in engagement after intervention
    attendance_change_7days = Column(Float)  # Change in attendance
    grade_change_next_assignment = Column(Float)  # Impact on next assignment grade
    
    # ========== Final Outcome ==========
    retained = Column(Boolean, nullable=True)  # NULL if outcome not yet determined
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("Student", backref="responses")
    intervention = relationship("Intervention", backref="responses")
