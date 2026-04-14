"""
Canonical Star Schema Models
----------------------------
Time-indexed fact and dimension tables for the EWS data pipeline.
These represent the canonical data model used by the ingestion pipeline.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey
from datetime import datetime, timezone
from backend.database.connection import Base


class DimStudent(Base):
    """Canonical student dimension with unified identifiers"""
    __tablename__ = "dim_students"

    student_id = Column(String(255), primary_key=True)  # Canonical email
    org_defined_id = Column(String(50), index=True)
    student_bits_id = Column(String(50))
    student_name = Column(String(255))
    program = Column(String(10), index=True)  # BS or MSc
    cohort = Column(String(20), index=True)
    trimester = Column(Integer)
    enrollment_status = Column(String(20), index=True)
    is_new_student = Column(Boolean)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class DimCourse(Base):
    """Course dimension"""
    __tablename__ = "dim_courses"

    course_id = Column(String(50), primary_key=True)
    course_code = Column(String(20))
    course_name = Column(String(255))
    department = Column(String(100))
    trimester = Column(String(20))
    program = Column(String(10))
    faculty_name = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FactAcademicPerformance(Base):
    """Time-indexed academic performance facts"""
    __tablename__ = "fact_academic_performance"

    performance_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(255), ForeignKey("dim_students.student_id"), nullable=False, index=True)
    course_id = Column(String(50), ForeignKey("dim_courses.course_id"))
    trimester = Column(String(20))
    assessment_type = Column(String(50), index=True)  # Quiz, Assignment, Exam
    assessment_name = Column(String(100))
    assessment_date = Column(Date)
    max_score = Column(Float)
    scored = Column(Float)
    percentage = Column(Float)
    submitted = Column(Boolean)
    submission_timestamp = Column(DateTime)
    late_submission = Column(Boolean)
    data_snapshot_date = Column(Date, index=True)  # Temporal versioning
    source_file = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FactEngagement(Base):
    """Time-indexed engagement facts"""
    __tablename__ = "fact_engagement"

    engagement_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(255), ForeignKey("dim_students.student_id"), nullable=False, index=True)
    course_id = Column(String(50), ForeignKey("dim_courses.course_id"), index=True)
    metric_date = Column(Date, index=True)
    metric_week = Column(Integer, index=True)

    # Attendance
    live_sessions_scheduled = Column(Integer)
    live_sessions_attended = Column(Integer)
    attendance_percentage = Column(Float)

    # Platform usage
    total_time_minutes = Column(Integer)
    content_access_time_minutes = Column(Integer)
    login_count = Column(Integer)
    days_active = Column(Integer)

    # Content interaction
    content_items_viewed = Column(Integer)
    discussion_posts = Column(Integer)
    discussion_reads = Column(Integer)

    data_snapshot_date = Column(Date, index=True)
    source_file = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FactConsistency(Base):
    """Consistency tracking over time windows"""
    __tablename__ = "fact_consistency"

    consistency_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(255), ForeignKey("dim_students.student_id"), nullable=False, index=True)
    course_id = Column(String(50), ForeignKey("dim_courses.course_id"))
    analysis_period_start = Column(Date)
    analysis_period_end = Column(Date)

    # Attendance consistency
    weeks_with_attendance = Column(Integer)
    total_weeks = Column(Integer)
    attendance_streak_current = Column(Integer)
    attendance_streak_max = Column(Integer)
    attendance_variance = Column(Float)

    # Platform consistency
    weeks_with_login = Column(Integer)
    avg_logins_per_week = Column(Float)
    login_variance = Column(Float)

    # Trend
    engagement_trend = Column(String(20))  # Increasing, Stable, Declining
    week_over_week_change = Column(Float)

    data_snapshot_date = Column(Date, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class FactIntentResponsiveness(Base):
    """Intent and responsiveness signals"""
    __tablename__ = "fact_intent_responsiveness"

    intent_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(255), ForeignKey("dim_students.student_id"), nullable=False, index=True)
    course_id = Column(String(50), ForeignKey("dim_courses.course_id"))

    # Quiz responsiveness
    quiz_name = Column(String(100))
    quiz_deadline = Column(DateTime)
    first_attempt_timestamp = Column(DateTime)
    final_submission_timestamp = Column(DateTime)
    hours_before_deadline = Column(Float)
    attempt_count = Column(Integer)

    # Communication responsiveness
    welcome_email_opened = Column(Boolean)
    support_emails_read = Column(Integer)
    response_time_hours = Column(Float)

    # Advanced communication tracking
    message_sent_date = Column(DateTime)
    response_received_date = Column(DateTime)
    response_received = Column(Boolean)
    message_priority = Column(String(50))  # normal, escalated, urgent
    message_type = Column(String(50))      # email, sms, whatsapp

    # Early warning
    no_login_days = Column(Integer)
    zero_participation_weeks = Column(Integer)

    data_snapshot_date = Column(Date)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DataLineage(Base):
    """Audit trail for the ETL pipeline"""
    __tablename__ = "data_lineage"

    lineage_id = Column(Integer, primary_key=True, autoincrement=True)
    source_file = Column(String(255))
    sheet_name = Column(String(255))
    target_table = Column(String(100))
    records_processed = Column(Integer)
    records_inserted = Column(Integer)
    records_updated = Column(Integer)
    records_skipped = Column(Integer)
    error_count = Column(Integer)
    processing_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processing_duration_seconds = Column(Integer)
