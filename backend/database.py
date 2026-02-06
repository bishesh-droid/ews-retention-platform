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
    id = Column(String, primary_key=True, index=True)
    absrate1 = Column(Float)
    absrate2 = Column(Float)
    absrate3 = Column(Float)
    absrate4 = Column(Float)
    absrate5 = Column(Float)
    absrate6 = Column(Float)
    absrate7 = Column(Float)
    nsusp1 = Column(Float)
    nsusp2 = Column(Float)
    nsusp3 = Column(Float)
    nsusp4 = Column(Float)
    nsusp5 = Column(Float)
    nsusp6 = Column(Float)
    nsusp7 = Column(Float)
    mobility1 = Column(Float)
    mobility2 = Column(Float)
    mobility3 = Column(Float)
    mobility4 = Column(Float)
    mobility5 = Column(Float)
    mobility6 = Column(Float)
    mobility7 = Column(Float)
    q1mpa1 = Column(Float)
    q2mpa1 = Column(Float)
    q3mpa1 = Column(Float)
    q4mpa1 = Column(Float)
    q1mpa2 = Column(Float)
    q2mpa2 = Column(Float)
    q3mpa2 = Column(Float)
    q4mpa2 = Column(Float)
    q1mpa3 = Column(Float)
    q2mpa3 = Column(Float)
    q3mpa3 = Column(Float)
    q4mpa3 = Column(Float)
    q1mpa4 = Column(Float)
    q2mpa4 = Column(Float)
    q3mpa4 = Column(Float)
    q4mpa4 = Column(Float)
    q1mpa5 = Column(Float)
    q2mpa5 = Column(Float)
    q3mpa5 = Column(Float)
    q4mpa5 = Column(Float)
    q1mpa6 = Column(Float)
    q2mpa6 = Column(Float)
    q3mpa6 = Column(Float)
    q4mpa6 = Column(Float)
    q1mpa7 = Column(Float)
    q2mpa7 = Column(Float)
    q3mpa7 = Column(Float)
    q4mpa7 = Column(Float)
    nograd = Column(Integer)

    predictions = relationship("Prediction", back_populates="student")
    interventions = relationship("Intervention", back_populates="student")
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
    
    # Signal breakdown scores (0-1 scale)
    academic_signal_score = Column(Float)
    engagement_signal_score = Column(Float)
    consistency_signal_score = Column(Float)
    intent_signal_score = Column(Float)
    responsiveness_signal_score = Column(Float)
    
    # Model metadata
    model_version = Column(String)
    prediction_timestamp = Column(DateTime, default=datetime.utcnow)
    top_risk_factors = Column(String)  # JSON string of top risk factors
    
    student = relationship("Student", back_populates="predictions")

class Intervention(Base):
    __tablename__ = "interventions"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"))
    date = Column(Date)
    user = Column(String)
    action = Column(String)
    ai_suggested = Column(Integer, default=0)  # Boolean as int (0 or 1)
    ai_reasoning = Column(String)
    effectiveness_score = Column(Float)
    
    # Risk threshold information
    risk_score_at_trigger = Column(Float)
    threshold_category = Column(String)  # 'gentle_reminder', 'mentor_outreach', 'urgent_intervention'
    channels = Column(String)  # JSON string: ["email", "whatsapp", "mentor_call"]
    assigned_team = Column(String)  # 'automated', 'faculty', 'sales'
    
    student = relationship("Student", back_populates="interventions")

class LLMQuery(Base):
    """Tracks all LLM interactions for audit and improvement."""
    __tablename__ = "llm_queries"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    user_role = Column(String)  # 'student', 'faculty', 'admin', 'sales'
    query_type = Column(String)  # 'explain_risk', 'advice', 'cohort_analysis', etc.
    input_data = Column(String)  # JSON string
    response = Column(String)
    confidence = Column(String)  # 'high', 'medium', 'low'
    sources = Column(String)  # JSON array of sources
    timestamp = Column(Date)

class LLMInsight(Base):
    """Stores institutional insights discovered by LLM."""
    __tablename__ = "llm_insights"
    id = Column(Integer, primary_key=True, index=True)
    insight_type = Column(String)  # 'systemic_issue', 'pattern', 'blind_spot'
    title = Column(String)
    content = Column(String)
    source_data = Column(String)  # JSON
    confidence = Column(String)
    visibility = Column(String)  # 'public', 'admin_only'
    created_at = Column(Date)
    dismissed = Column(Integer, default=0)  # Boolean as int

class AIExplanation(Base):
    """Stores generated explanations for students."""
    __tablename__ = "ai_explanations"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String)
    explanation_type = Column(String)  # 'risk_change', 'advice', 'what_if'
    content = Column(String)
    confidence = Column(String)
    created_at = Column(Date)
    viewed = Column(Integer, default=0)  # Boolean as int

class PatternDiscovery(Base):
    """Stores discovered institutional patterns and blind spots identified by LLM."""
    __tablename__ = "pattern_discoveries"
    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(String)  # 'systemic_issue', 'cross_semester', 'demographic_disparity', 'blind_spot'
    title = Column(String)
    description = Column(String)
    severity = Column(String)  # 'low', 'medium', 'high', 'critical'
    affected_cohort = Column(String)  # JSON array of cohort identifiers
    root_cause = Column(String)  # LLM-suggested root cause
    suggested_action = Column(String)  # Recommended intervention at institutional level
    supporting_data = Column(String)  # JSON of statistical evidence
    confidence = Column(String)  # 'high', 'medium', 'low'
    discovered_at = Column(Date)
    acknowledged = Column(Integer, default=0)  # Whether admin has reviewed
    acted_upon = Column(Integer, default=0)  # Whether action was taken

class RawEvent(Base):
    """Stores all incoming student activity events from various sources."""
    __tablename__ = "raw_events"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    event_source = Column(String, index=True)  # 'lms', 'zoom', 'website', 'communication', 'marketing'
    event_type = Column(String)  # 'login', 'assignment_submit', 'class_attend', 'email_open', etc.
    event_data = Column(String)  # JSON string for flexible event-specific data
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    student = relationship("Student", backref="raw_events")

class EngineeredFeatures(Base):
    """Stores computed features organized by 5 signal categories."""
    __tablename__ = "engineered_features"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    computation_date = Column(Date, index=True)
    
    # Academic Performance Signals
    assignment_completion_rate = Column(Float)
    average_grade = Column(Float)
    deadline_adherence_score = Column(Float)
    grade_trend = Column(Float)
    
    # Engagement Signals
    login_frequency = Column(Float)
    avg_session_duration = Column(Float)
    video_completion_rate = Column(Float)
    platform_interaction_score = Column(Float)
    
    # Consistency Signals
    attendance_rate = Column(Float)
    activity_regularity_score = Column(Float)
    missed_classes_count = Column(Integer)
    attendance_trend = Column(Float)
    
    # Intent Signals
    engagement_trend = Column(Float)
    days_inactive = Column(Integer)
    declining_performance_flag = Column(Boolean)
    
    # Responsiveness Signals
    email_open_rate = Column(Float)
    message_reply_rate = Column(Float)
    avg_response_time_hours = Column(Float)
    
    student = relationship("Student", backref="engineered_features")

class StudentResponse(Base):
    """Tracks student responses to interventions for feedback loop."""
    __tablename__ = "student_responses"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    intervention_id = Column(Integer, ForeignKey("interventions.id"))
    
    # Response tracking
    responded = Column(Boolean)
    response_time_hours = Column(Float)
    behavioral_change_detected = Column(Boolean)
    
    # Outcome tracking (7-day window)
    engagement_change_7days = Column(Float)  # % change in engagement
    attendance_change_7days = Column(Float)
    grade_change_next_assignment = Column(Float)
    
    # Final outcome
    retained = Column(Boolean, nullable=True)  # NULL if not yet determined
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("Student", backref="responses")
    intervention = relationship("Intervention", backref="responses")

def init_db():
    Base.metadata.create_all(bind=engine)