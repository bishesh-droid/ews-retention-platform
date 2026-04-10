"""
Event Schemas
------------
Pydantic schemas for events and engineered features.
"""

from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
from datetime import date, datetime


class RawEventBase(BaseModel):
    """Base raw event schema."""
    student_id: str
    event_source: str  # 'lms', 'zoom', 'website', 'communication', 'marketing'
    event_type: str
    event_data: Dict[str, Any]  # Flexible JSON data


class RawEventCreate(RawEventBase):
    """Schema for creating a raw event."""


class RawEvent(RawEventBase):
    """Full raw event schema."""
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class EngineeredFeaturesBase(BaseModel):
    """Base engineered features schema."""
    student_id: str
    computation_date: date

    # Academic Performance Signals
    assignment_completion_rate: Optional[float] = None
    average_grade: Optional[float] = None
    deadline_adherence_score: Optional[float] = None
    grade_trend: Optional[float] = None

    # Engagement Signals
    login_frequency: Optional[float] = None
    avg_session_duration: Optional[float] = None
    video_completion_rate: Optional[float] = None
    platform_interaction_score: Optional[float] = None

    # Consistency Signals
    attendance_rate: Optional[float] = None
    activity_regularity_score: Optional[float] = None
    missed_classes_count: Optional[int] = None
    attendance_trend: Optional[float] = None

    # Intent Signals
    engagement_trend: Optional[float] = None
    days_inactive: Optional[int] = None
    declining_performance_flag: Optional[bool] = None

    # Responsiveness Signals
    email_open_rate: Optional[float] = None
    message_reply_rate: Optional[float] = None
    avg_response_time_hours: Optional[float] = None


class EngineeredFeaturesCreate(EngineeredFeaturesBase):
    """Schema for creating engineered features."""


class EngineeredFeatures(EngineeredFeaturesBase):
    """Full engineered features schema."""
    id: int

    model_config = ConfigDict(from_attributes=True)


class StudentResponseBase(BaseModel):
    """Base student response schema for intervention feedback."""
    student_id: str
    intervention_id: int
    responded: bool
    response_time_hours: Optional[float] = None
    behavioral_change_detected: bool
    engagement_change_7days: Optional[float] = None
    attendance_change_7days: Optional[float] = None
    grade_change_next_assignment: Optional[float] = None
    retained: Optional[bool] = None


class StudentResponseCreate(StudentResponseBase):
    """Schema for creating a student response."""


class StudentResponse(StudentResponseBase):
    """Full student response schema."""
    id: int
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)
