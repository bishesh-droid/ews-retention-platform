"""
Student Model
------------
Database model for student entity from Engagement_Analysis.xlsx.

STUDENT IDENTIFIER NAMING CONVENTION
=====================================
student.id              = email address (primary key in students table)
student.org_defined_id  = BITS ID e.g. "2025EB1100001" — use in ALL FK references
                          across InterventionLog, RiskSnapshot, GradedComponent, etc.

NEVER use:
  - "student_id" as an FK to students.id — use "student_org_id" pointing to org_defined_id
  - "org_id" as a variable name — always use "org_defined_id" for the BITS ID
  - "bits_id" — rename to "org_defined_id" at the call site

If a new model needs to reference a student, the FK column MUST be named
"student_org_id" and point to students.org_defined_id.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Index
from sqlalchemy.orm import relationship, foreign
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
        # D5-3: Composite index for faculty-scoped active student queries
        Index('ix_student_dept_active', 'parent_department_name', 'is_active'),
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
    intervention_logs = relationship(
        "InterventionLog",
        cascade="all, delete-orphan",
        foreign_keys="[InterventionLog.student_org_id]",
        primaryjoin="Student.org_defined_id == foreign(InterventionLog.student_org_id)",
        overlaps="student"
    )
