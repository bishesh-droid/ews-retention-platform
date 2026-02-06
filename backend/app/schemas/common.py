"""
Common Schemas
-------------
Shared base models and common response schemas.
"""

from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, List, Optional


class PredictionResult(BaseModel):
    """Common prediction result schema used across the API."""
    risk_score: float
    retention_prediction: str
    engagement_score: float
    signal_breakdown: Optional[Dict[str, float]] = None
    top_risk_factors: Optional[List[Dict[str, Any]]] = None


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    

class ErrorResponse(BaseModel):
    """Generic error response."""
    error: str
    detail: Optional[str] = None
