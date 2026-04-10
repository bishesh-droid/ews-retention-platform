"""
Prediction Schemas
-----------------
Pydantic schemas for risk prediction data.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.schemas.common import ATTENDANCE_FIELD


class PredictionBase(BaseModel):
    """Base prediction schema with strict field validation."""
    risk_score: float = Field(ge=0.0, le=100.0, description="Risk score (0-100)")
    engagement_score: float = Field(ge=0.0, le=100.0, description="Engagement score (0-100)")
    retention_likelihood: str
    attendance: Optional[float] = ATTENDANCE_FIELD
    assignments: float = Field(ge=0.0, le=100.0, description="Assignment completion (0-100)")
    grades: float = Field(ge=0.0, le=100.0, description="Grade percentage (0-100)")

    # Signal breakdown scores (all bounded 0-100)
    academic_signal_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    engagement_signal_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    consistency_signal_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    intent_signal_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    responsiveness_signal_score: Optional[float] = Field(None, ge=0.0, le=100.0)

    # Model metadata
    model_version: Optional[str] = None
    model_type: Optional[str] = "rule_based"
    model_description: Optional[str] = "Weighted engagement formula — not a trained ML model"
    score_basis: Optional[str] = "rule_based_formula"
    top_risk_factors: Optional[List[Dict[str, Any]]] = None


class PredictionCreate(PredictionBase):
    """Schema for creating a prediction."""


class Prediction(PredictionBase):
    """Full prediction schema with ID and timestamp."""
    id: int
    student_id: str
    prediction_timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
