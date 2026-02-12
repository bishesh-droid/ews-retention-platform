from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Date, DateTime, Boolean, JSON
from datetime import datetime

from sqlalchemy.orm import sessionmaker, relationship, Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_student_by_id(db: Session, student_id: str):
    return db.query(Student).filter(Student.id == student_id).first()

DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    id = Column(String, primary_key=True, index=True)  # Username (email)
    org_defined_id = Column(String, index=True)
    first_name = Column(String)
    last_name = Column(String)
    old_new_student = Column(String)
    is_active = Column(Boolean, default=True)
    parent_department_name = Column(String)
    parent_department_code = Column(String)

    enrollments = relationship("Enrollment", back_populates="student")
    predictions = relationship("Prediction", back_populates="student")
    interventions = relationship("Intervention", back_populates="student")

class Course(Base):
    __tablename__ = "courses"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    semester_code = Column(String)
    semester_name = Column(String)
    content_required_w1w2 = Column(Integer)
    content_required_total = Column(Integer)
    week1_content = Column(Integer)
    week2_content = Column(Integer)
    lab_content = Column(Integer)

    enrollments = relationship("Enrollment", back_populates="course")

class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    course_id = Column(String, ForeignKey("courses.id"), index=True)

    content_completed = Column(Integer, default=0)
    content_required = Column(Integer, default=0)
    content_required_w1w2 = Column(Integer, default=0)
    checklist_completed = Column(Integer, default=0)
    quiz_completed = Column(Integer, default=0)
    total_quiz_attempts = Column(Integer, default=0)
    last_quiz_attempt_date = Column(String)
    discussion_posts_created = Column(Integer, default=0)
    discussion_post_replies = Column(Integer, default=0)
    discussion_posts_read = Column(Integer, default=0)
    last_discussion_post_date = Column(String)
    num_assignment_submissions = Column(Integer, default=0)
    last_assignment_submission_date = Column(String)
    total_time_spent_seconds = Column(Integer, default=0)
    last_visited_date = Column(String)
    last_system_login = Column(String)
    num_logins = Column(Integer, default=0)
    last_scorm_completion_date = Column(String)
    last_scorm_visit_date = Column(String)

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"))
    risk_score = Column(Float)
    engagement_score = Column(Float)
    retention_likelihood = Column(String)
    attendance = Column(Float)
    assignments = Column(Float)
    grades = Column(Float)

    # Signal breakdown scores
    academic_signal_score = Column(Float)
    engagement_signal_score = Column(Float)
    consistency_signal_score = Column(Float)
    intent_signal_score = Column(Float)
    responsiveness_signal_score = Column(Float)

    model_version = Column(String)
    prediction_timestamp = Column(DateTime, default=datetime.utcnow)
    top_risk_factors = Column(String)

    student = relationship("Student", back_populates="predictions")

class Intervention(Base):
    __tablename__ = "interventions"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"))
    date = Column(Date)
    user = Column(String)
    action = Column(String)
    ai_suggested = Column(Integer, default=0)
    ai_reasoning = Column(String)
    effectiveness_score = Column(Float)

    risk_score_at_trigger = Column(Float)
    threshold_category = Column(String)
    channels = Column(String)
    assigned_team = Column(String)

    student = relationship("Student", back_populates="interventions")

class LLMQuery(Base):
    __tablename__ = "llm_queries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    user_role = Column(String)
    query_type = Column(String)
    input_data = Column(String)
    response = Column(String)
    confidence = Column(String)
    sources = Column(String)
    timestamp = Column(Date)

class LLMInsight(Base):
    __tablename__ = "llm_insights"
    id = Column(Integer, primary_key=True, index=True)
    insight_type = Column(String)
    title = Column(String)
    content = Column(String)
    source_data = Column(String)
    confidence = Column(String)
    visibility = Column(String)
    created_at = Column(Date)
    dismissed = Column(Integer, default=0)

class AIExplanation(Base):
    __tablename__ = "ai_explanations"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String)
    explanation_type = Column(String)
    content = Column(String)
    confidence = Column(String)
    created_at = Column(Date)
    viewed = Column(Integer, default=0)

class PatternDiscovery(Base):
    __tablename__ = "pattern_discoveries"
    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(String)
    title = Column(String)
    description = Column(String)
    severity = Column(String)
    affected_cohort = Column(String)
    root_cause = Column(String)
    suggested_action = Column(String)
    supporting_data = Column(String)
    confidence = Column(String)
    discovered_at = Column(Date)
    acknowledged = Column(Integer, default=0)
    acted_upon = Column(Integer, default=0)

class RawEvent(Base):
    __tablename__ = "raw_events"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    event_source = Column(String, index=True)
    event_type = Column(String)
    event_data = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    student = relationship("Student", backref="raw_events")

class EngineeredFeatures(Base):
    __tablename__ = "engineered_features"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    computation_date = Column(Date, index=True)

    assignment_completion_rate = Column(Float)
    average_grade = Column(Float)
    deadline_adherence_score = Column(Float)
    grade_trend = Column(Float)
    login_frequency = Column(Float)
    avg_session_duration = Column(Float)
    video_completion_rate = Column(Float)
    platform_interaction_score = Column(Float)
    attendance_rate = Column(Float)
    activity_regularity_score = Column(Float)
    missed_classes_count = Column(Integer)
    attendance_trend = Column(Float)
    engagement_trend = Column(Float)
    days_inactive = Column(Integer)
    declining_performance_flag = Column(Boolean)
    email_open_rate = Column(Float)
    message_reply_rate = Column(Float)
    avg_response_time_hours = Column(Float)

    student = relationship("Student", backref="engineered_features")

class StudentResponse(Base):
    __tablename__ = "student_responses"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    intervention_id = Column(Integer, ForeignKey("interventions.id"))

    responded = Column(Boolean)
    response_time_hours = Column(Float)
    behavioral_change_detected = Column(Boolean)
    engagement_change_7days = Column(Float)
    attendance_change_7days = Column(Float)
    grade_change_next_assignment = Column(Float)
    retained = Column(Boolean, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", backref="responses")
    intervention = relationship("Intervention", backref="responses")

class LiveSessionAttendance(Base):
    __tablename__ = "live_session_attendance"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    semester_code = Column(String)
    week_number = Column(Integer)
    attended = Column(Boolean, default=False)
    student = relationship("Student", backref="live_attendance")

class GradedComponent(Base):
    __tablename__ = "graded_components"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    course_code = Column(String)
    course_name = Column(String)
    component_type = Column(String)  # "quiz" or "assignment"
    component_number = Column(Integer)
    score = Column(Float, nullable=True)  # null = missed/absent
    max_score = Column(Float)
    missed = Column(Boolean, default=False)
    student = relationship("Student", backref="graded_components")

class ExamRecord(Base):
    __tablename__ = "exam_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    course_code = Column(String)
    course_name = Column(String)
    slot = Column(String)  # "slot-1", "slot-2"
    marks_obtained = Column(Float, nullable=True)
    marks_total = Column(Float)
    present = Column(Boolean, default=True)
    mode = Column(String, nullable=True)  # "Online" or "Onsite"
    student = relationship("Student", backref="exam_records")

# ============================================================================
# CANONICAL DATA MODEL - TIME-INDEXED FACT & DIMENSION TABLES
# ============================================================================

class DimStudent(Base):
    """Canonical student dimension with unified identifiers"""
    __tablename__ = "dim_students"
    
    student_id = Column(String(255), primary_key=True)  # Canonical email
    org_defined_id = Column(String(50), index=True)
    student_bits_id = Column(String(50))
    student_name = Column(String(255))
    program = Column(String(10))  # BS or MSc
    cohort = Column(String(20))
    trimester = Column(Integer)
    enrollment_status = Column(String(20))
    is_new_student = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)

class FactAcademicPerformance(Base):
    """Time-indexed academic performance facts"""
    __tablename__ = "fact_academic_performance"
    
    performance_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(255), ForeignKey("dim_students.student_id"), nullable=False, index=True)
    course_id = Column(String(50), ForeignKey("dim_courses.course_id"))
    trimester = Column(String(20))
    assessment_type = Column(String(50))  # Quiz, Assignment, Exam
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
    created_at = Column(DateTime, default=datetime.utcnow)

class FactEngagement(Base):
    """Time-indexed engagement facts"""
    __tablename__ = "fact_engagement"
    
    engagement_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(255), ForeignKey("dim_students.student_id"), nullable=False, index=True)
    course_id = Column(String(50), ForeignKey("dim_courses.course_id"))
    metric_date = Column(Date, index=True)
    metric_week = Column(Integer)
    
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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    
    # Advanced Communication Tracking (New)
    message_sent_date = Column(DateTime)
    response_received_date = Column(DateTime)
    response_received = Column(Boolean)
    message_priority = Column(String(50))  # normal, escalated, urgent
    message_type = Column(String(50))      # email, sms, whatsapp
    
    # Early warning
    no_login_days = Column(Integer)
    zero_participation_weeks = Column(Integer)
    
    data_snapshot_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)

class DataLineage(Base):
    """Audit trail for ETL pipeline"""
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
    processing_timestamp = Column(DateTime, default=datetime.utcnow)
    processing_duration_seconds = Column(Integer)

def init_db():
    Base.metadata.create_all(bind=engine)
