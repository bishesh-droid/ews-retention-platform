"""
Student Model
------------
Database model for student entity from Engagement_Analysis.xlsx.
"""

from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class Student(Base):
    """
    Student model derived from the 'Learner Usage main dump' sheet.
    One row per unique student (username).
    """
    __tablename__ = "students"

    id = Column(String, primary_key=True, index=True)  # Username (email)
    org_defined_id = Column(String, index=True)
    first_name = Column(String)
    last_name = Column(String)
    old_new_student = Column(String)  # 'old' or 'new'
    is_active = Column(Boolean, default=True)
    parent_department_name = Column(String)  # 'BS - Data Science & AI' or MS variant
    parent_department_code = Column(String)

    # Relationships
    enrollments = relationship("Enrollment", back_populates="student")
    predictions = relationship("Prediction", back_populates="student")
    interventions = relationship("Intervention", back_populates="student")
    exam_records = relationship("ExamRecord", back_populates="student")
    raw_events = relationship("RawEvent", back_populates="student")
    engineered_features = relationship("EngineeredFeatures", back_populates="student")
    responses = relationship("StudentResponse", back_populates="student")
    risk_history = relationship("RiskSnapshot", back_populates="student")
    goals = relationship("Goal", back_populates="student")
    graded_components = relationship("GradedComponent", back_populates="student")
