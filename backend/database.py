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

def init_db():
    Base.metadata.create_all(bind=engine)
