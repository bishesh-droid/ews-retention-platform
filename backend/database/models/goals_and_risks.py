from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..connection import Base # Corrected import for Base

class RiskSnapshot(Base):
    """Historical risk snapshots for trend & velocity analysis"""
    __tablename__ = "risk_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    risk_score = Column(Float)
    velocity = Column(Float)      # Weekly change
    acceleration = Column(Float)  # Rate of change of velocity
    engagement_score = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    student = relationship("Student", back_populates="risk_history")

class Goal(Base):
    """Student progress goals"""
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    type = Column(String)  # "login", "study_hours", "assignment", "attendance"
    title = Column(String)
    target_value = Column(Float)
    current_value = Column(Float, default=0.0)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    status = Column(String, default="active")  # active, completed, failed
    
    student = relationship("Student", back_populates="goals")
