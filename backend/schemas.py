from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import date, datetime

# ========== Raw Event Schemas ==========
class RawEventBase(BaseModel):
    student_id: str
    event_source: str  # 'lms', 'zoom', 'website', 'communication', 'marketing'
    event_type: str
    event_data: Dict[str, Any]  # Flexible JSON data

class RawEventCreate(RawEventBase):
    pass

class RawEvent(RawEventBase):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Engineered Features Schemas ==========
class EngineeredFeaturesBase(BaseModel):
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
    pass

class EngineeredFeatures(EngineeredFeaturesBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ========== Student Response Schemas ==========
class StudentResponseBase(BaseModel):
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
    pass

class StudentResponse(StudentResponseBase):
    id: int
    recorded_at: datetime
    model_config = ConfigDict(from_attributes=True)

# ========== Prediction Schemas (Updated) ==========
class PredictionBase(BaseModel):
    risk_score: float
    engagement_score: float
    retention_likelihood: str
    attendance: float
    assignments: float
    grades: float
    # Signal breakdown scores
    academic_signal_score: Optional[float] = None
    engagement_signal_score: Optional[float] = None
    consistency_signal_score: Optional[float] = None
    intent_signal_score: Optional[float] = None
    responsiveness_signal_score: Optional[float] = None
    # Model metadata
    model_version: Optional[str] = None
    top_risk_factors: Optional[List[Dict[str, Any]]] = None

class PredictionCreate(PredictionBase):
    pass

class Prediction(PredictionBase):
    id: int
    student_id: str
    prediction_timestamp: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

# ========== Intervention Schemas (Updated) ==========
class InterventionBase(BaseModel):
    date: date
    user: str
    action: str
    risk_score_at_trigger: Optional[float] = None
    threshold_category: Optional[str] = None
    channels: Optional[List[str]] = None
    assigned_team: Optional[str] = None

class InterventionCreate(BaseModel):
    user: str
    action: str
    risk_score_at_trigger: Optional[float] = None
    threshold_category: Optional[str] = None
    channels: Optional[List[str]] = None
    assigned_team: Optional[str] = None

class Intervention(InterventionBase):
    id: int
    student_id: str
    ai_suggested: Optional[int] = 0
    ai_reasoning: Optional[str] = None
    effectiveness_score: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)

class RecommendationBase(BaseModel):
    recommendation: str

class RecommendationCreate(RecommendationBase):
    pass

class Recommendation(RecommendationBase):
    id: int
    student_id: str
    model_config = ConfigDict(from_attributes=True)

class PredictionResult(BaseModel):
    risk_score: float
    retention_prediction: str
    engagement_score: float
    signal_breakdown: Optional[Dict[str, float]] = None
    top_risk_factors: Optional[List[Dict[str, Any]]] = None
    
class StudentBase(BaseModel):
    id: str
    absrate1: Optional[float] = None
    absrate2: Optional[float] = None
    absrate3: Optional[float] = None
    absrate4: Optional[float] = None
    absrate5: Optional[float] = None
    absrate6: Optional[float] = None
    absrate7: Optional[float] = None
    nsusp1: Optional[float] = None
    nsusp2: Optional[float] = None
    nsusp3: Optional[float] = None
    nsusp4: Optional[float] = None
    nsusp5: Optional[float] = None
    nsusp6: Optional[float] = None
    nsusp7: Optional[float] = None
    mobility1: Optional[float] = None
    mobility2: Optional[float] = None
    mobility3: Optional[float] = None
    mobility4: Optional[float] = None
    mobility5: Optional[float] = None
    mobility6: Optional[float] = None
    mobility7: Optional[float] = None
    q1mpa1: Optional[float] = None
    q2mpa1: Optional[float] = None
    q3mpa1: Optional[float] = None
    q4mpa1: Optional[float] = None
    q1mpa2: Optional[float] = None
    q2mpa2: Optional[float] = None
    q3mpa2: Optional[float] = None
    q4mpa2: Optional[float] = None
    q1mpa3: Optional[float] = None
    q2mpa3: Optional[float] = None
    q3mpa3: Optional[float] = None
    q4mpa3: Optional[float] = None
    q1mpa4: Optional[float] = None
    q2mpa4: Optional[float] = None
    q3mpa4: Optional[float] = None
    q4mpa4: Optional[float] = None
    q1mpa5: Optional[float] = None
    q2mpa5: Optional[float] = None
    q3mpa5: Optional[float] = None
    q4mpa5: Optional[float] = None
    q1mpa6: Optional[float] = None
    q2mpa6: Optional[float] = None
    q3mpa6: Optional[float] = None
    q4mpa6: Optional[float] = None
    q1mpa7: Optional[float] = None
    q2mpa7: Optional[float] = None
    q3mpa7: Optional[float] = None
    q4mpa7: Optional[float] = None
    nograd: Optional[int] = None

class StudentCreate(StudentBase):
    pass

class Student(StudentBase):
    predictions: List[Prediction] = []
    interventions: List[Intervention] = [] # Add interventions
    model_config = ConfigDict(from_attributes=True)

class PatternDiscoveryBase(BaseModel):
    pattern_type: str
    title: str
    description: str
    severity: str
    affected_cohort: str
    root_cause: Optional[str] = None
    suggested_action: Optional[str] = None
    supporting_data: Optional[str] = None
    confidence: str

class PatternDiscoveryCreate(PatternDiscoveryBase):
    pass

class PatternDiscovery(PatternDiscoveryBase):
    id: int
    discovered_at: date
    acknowledged: int
    acted_upon: int
    model_config = ConfigDict(from_attributes=True)

