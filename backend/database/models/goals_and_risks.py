from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from ..connection import Base  # Corrected import for Base


class RiskSnapshot(Base):
    """Historical risk snapshots for trend & velocity analysis"""

    # Requires DB migration: alembic revision 004_add_week_number_to_risk_snapshots
    __tablename__ = "risk_snapshots"

    __table_args__ = (
        UniqueConstraint(
            'student_id', 'week_number', 'semester_name',
            name='uq_risk_snapshot_student_week'
        ),
        Index('ix_risk_snapshot_student', 'student_id'),
        Index('ix_risk_snapshot_timestamp', 'timestamp'),
        Index('ix_risk_snapshot_week', 'week_number'),
    )

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    risk_score = Column(Float)
    velocity = Column(Float)      # Weekly change
    acceleration = Column(Float)  # Rate of change of velocity
    engagement_score = Column(Float)
    week_number = Column(Integer, nullable=True)  # trimester week (see config.TRIMESTER_START_DATE)
    semester_name = Column(String(64), nullable=True)  # e.g. "Trimester 2"
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
