"""
Enrollment Model
----------------
Database model for student-course enrollment with engagement metrics.
Each row represents one student enrolled in one course.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    ForeignKey,
    DateTime,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class Enrollment(Base):
    """
    Enrollment model from 'Learner Usage main dump' sheet.
    Contains all per-student-per-course engagement data.
    """

    __tablename__ = "enrollments"

    __table_args__ = (
        Index("ix_enrollment_last_login", "last_system_login"),
        Index("ix_enrollment_last_visited", "last_visited_date"),
        Index("ix_enrollment_student_id", "student_id"),
        Index("ix_enrollment_course_code", "course_id"),
        UniqueConstraint(
            "student_id", "course_id", name="uq_enrollment_student_course"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(
        String,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id = Column(
        String, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True
    )

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

    # Course type flag
    is_optional = Column(Boolean, default=False, nullable=False)

    # Final outcome (for retrospective evaluation of risk scores)
    # Values: "active" | "completed" | "dropped" | "deferred" | "unknown"
    final_outcome = Column(String(32), nullable=True, default=None)
    outcome_source = Column(
        String(64), nullable=True
    )  # "exam_data" | "admin_manual" | "inferred_from_activity"
    outcome_updated_at = Column(DateTime, nullable=True)

    # Relationships
    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
