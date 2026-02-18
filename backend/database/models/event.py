"""
Event Models
-----------
Database models for raw events and engineered features.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.connection import Base


class RawEvent(Base):
    """
    Stores all incoming student activity events from various sources.
    This is the raw event stream before feature engineering.
    """
    __tablename__ = "raw_events"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    
    # Event classification
    event_source = Column(String, index=True)  # 'lms', 'zoom', 'website', 'communication', 'marketing'
    event_type = Column(String)  # 'login', 'assignment_submit', 'class_attend', 'email_open', etc.
    
    # Event payload
    event_data = Column(String)  # JSON string for flexible event-specific data
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    student = relationship("Student", back_populates="raw_events")


class EngineeredFeatures(Base):
    """
    Stores computed features organized by the 5 signal categories:
    - Academic Performance
    - Engagement
    - Consistency
    - Intent
    - Responsiveness
    """
    __tablename__ = "engineered_features"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    computation_date = Column(Date, index=True)
    
    # ========== Academic Performance Signals ==========
    assignment_completion_rate = Column(Float)
    average_grade = Column(Float)
    deadline_adherence_score = Column(Float)
    grade_trend = Column(Float)  # Positive = improving, Negative = declining
    
    # ========== Engagement Signals ==========
    login_frequency = Column(Float)  # Logins per week
    avg_session_duration = Column(Float)  # Average minutes per session
    video_completion_rate = Column(Float)  # % of videos watched to completion
    platform_interaction_score = Column(Float)  # Composite engagement metric
    
    # ========== Consistency Signals ==========
    attendance_rate = Column(Float)  # % of classes attended
    activity_regularity_score = Column(Float)  # How regular is their activity pattern
    missed_classes_count = Column(Integer)
    attendance_trend = Column(Float)  # Trend over time
    
    # ========== Intent Signals ==========
    engagement_trend = Column(Float)  # Increasing or decreasing engagement
    days_inactive = Column(Integer)  # Days since last activity
    declining_performance_flag = Column(Boolean)  # True if performance is declining
    
    # ========== Responsiveness Signals ==========
    email_open_rate = Column(Float)  # % of emails opened
    message_reply_rate = Column(Float)  # % of messages replied to
    avg_response_time_hours = Column(Float)  # Average time to respond
    
    # Relationship
    student = relationship("Student", back_populates="engineered_features")
