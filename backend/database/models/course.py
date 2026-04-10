"""
Course Model
------------
Database model for course offerings from Engagement_Analysis.xlsx.
"""

from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class Course(Base):
    """
    Course model derived from the 'Courses' sheet and 'Learner Usage main dump'.
    """
    __tablename__ = "courses"

    id = Column(String, primary_key=True, index=True)  # Course Offering Code
    name = Column(String, index=True)  # Course Offering Name
    semester_code = Column(String)
    semester_name = Column(String)  # 'Trimester 1' or 'Trimester 2'
    content_required_w1w2 = Column(Integer)  # Required content items for weeks 1 & 2
    content_required_total = Column(Integer)  # Total content items required
    week1_content = Column(Integer)
    week2_content = Column(Integer)
    lab_content = Column(Integer)

    # Relationships
    enrollments = relationship("Enrollment", back_populates="course")
