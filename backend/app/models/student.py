"""
Student Model
------------
Database model for student entity from Engagement_Analysis.xlsx.
"""

from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship
from backend.app.database.connection import Base


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
