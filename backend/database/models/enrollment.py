"""
Enrollment Model
----------------
Database model for student-course enrollment with engagement metrics.
Each row represents one student enrolled in one course.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class Enrollment(Base):
    """
    Enrollment model from 'Learner Usage main dump' sheet.
    Contains all per-student-per-course engagement data.
    """
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    course_id = Column(String, ForeignKey("courses.id"), index=True)

    # Content engagement
    content_completed = Column(Integer, default=0)
    content_required = Column(Integer, default=0)
    content_required_w1w2 = Column(Integer, default=0)

    # Checklist
    checklist_completed = Column(Integer, default=0)

    # Quiz engagement
    quiz_completed = Column(Integer, default=0)
    total_quiz_attempts = Column(Integer, default=0)
    last_quiz_attempt_date = Column(String)

    # Discussion engagement
    discussion_posts_created = Column(Integer, default=0)
    discussion_post_replies = Column(Integer, default=0)
    discussion_posts_read = Column(Integer, default=0)
    last_discussion_post_date = Column(String)

    # Assignment engagement
    num_assignment_submissions = Column(Integer, default=0)
    last_assignment_submission_date = Column(String)

    # Time and login
    total_time_spent_seconds = Column(Integer, default=0)
    last_visited_date = Column(String)
    last_system_login = Column(String)
    num_logins = Column(Integer, default=0)

    # SCORM
    last_scorm_completion_date = Column(String)
    last_scorm_visit_date = Column(String)

    # Relationships
    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
