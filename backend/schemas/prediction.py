"""
Prediction Schemas
-----------------
Pydantic schemas for risk prediction data.
"""

from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime


class PredictionBase(BaseModel):
    """Base prediction schema."""
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
    model_type: Optional[str] = "rule_based"
    model_description: Optional[str] = "Weighted engagement formula — not a trained ML model"
    score_basis: Optional[str] = "rule_based_formula"
    top_risk_factors: Optional[List[Dict[str, Any]]] = None


class PredictionCreate(PredictionBase):
    """Schema for creating a prediction."""
    pass


class Prediction(PredictionBase):
    """Full prediction schema with ID and timestamp."""
    id: int
    student_id: str
    prediction_timestamp: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
