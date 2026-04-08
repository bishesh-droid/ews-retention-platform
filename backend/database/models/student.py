"""
Student Model
------------
Database model for student entity from Engagement_Analysis.xlsx.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class Student(Base):
    """
    Student model derived from the 'Learner Usage main dump' sheet.
    One row per unique student (username).
    """
    __tablename__ = "students"

    __table_args__ = (
        Index('ix_student_department', 'parent_department_name'),
        Index('ix_student_org_id', 'org_defined_id'),
        Index('ix_student_is_active', 'is_active'),
    )

    id = Column(String, primary_key=True, index=True)  # Username (email)
    org_defined_id = Column(String, index=True)
    first_name = Column(String)
    last_name = Column(String)
    old_new_student = Column(String)  # 'old' or 'new'
    is_active = Column(Boolean, default=True, nullable=False)
    parent_department_name = Column(String)  # 'BS - Data Science & AI' or MS variant
    parent_department_code = Column(String)

    # Soft delete fields (CROSS-1)
    deactivated_at = Column(DateTime, nullable=True)
    deactivation_reason = Column(String(128), nullable=True)
    # Values: "not_in_latest_export" | "manual" | "withdrawn"

    # Relationships with cascade rules (DB-3)
    enrollments = relationship(
        "Enrollment", back_populates="student",
        cascade="all, delete-orphan",
        lazy="select"
    )
    predictions = relationship(
        "Prediction", back_populates="student",
        cascade="all, delete-orphan"
    )
    interventions = relationship(
        "Intervention", back_populates="student",
        cascade="all, delete-orphan"
    )
    exam_records = relationship(
        "ExamRecord", back_populates="student",
        cascade="all, delete-orphan"
    )
    raw_events = relationship(
        "RawEvent", back_populates="student",
        cascade="all, delete-orphan"
    )
    engineered_features = relationship(
        "EngineeredFeatures", back_populates="student",
        cascade="all, delete-orphan"
    )
    responses = relationship(
        "StudentResponse", back_populates="student",
        cascade="all, delete-orphan"
    )
    risk_history = relationship(
        "RiskSnapshot", back_populates="student",
        cascade="all, delete-orphan"
    )
    goals = relationship(
        "Goal", back_populates="student",
        cascade="all, delete-orphan"
    )
    graded_components = relationship(
        "GradedComponent", back_populates="student",
        cascade="all, delete-orphan"
    )
