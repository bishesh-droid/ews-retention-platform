"""
Course Content Registry Model
-----------------------------
Stores the best-known content_required value per course per semester.
Acts as a fallback when ingestion produces null values.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from ..connection import Base


class CourseContentRegistry(Base):
    """Registry for course content requirements with versioning."""
    __tablename__ = "course_content_registry"

    id = Column(Integer, primary_key=True)
    course_offering_code = Column(String(64), nullable=False, index=True)
    course_name = Column(String(256), nullable=False)
    semester_name = Column(String(64), nullable=False)
    content_required = Column(Integer, nullable=False)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source_file = Column(String(256), nullable=True)

    __table_args__ = (
        UniqueConstraint("course_offering_code", "semester_name", name="uq_course_semester"),
    )
