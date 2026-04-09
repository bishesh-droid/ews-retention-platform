"""
Common Schemas
-------------
Shared base models and common response schemas.
"""

from pydantic import BaseModel, ConfigDict, Field
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


# ============================================================================
# Strict Field Validators for FERPA Compliance
# ============================================================================
# These fields enforce strict validation to prevent data corruption and
# injection attacks. Use these for student data input schemas.
# ============================================================================

# GPA field: strictly bounded between 0.0 and 4.0
GPA_FIELD = Field(
    None,
    ge=0.0,
    le=4.0,
    description="Grade Point Average (0.0 to 4.0 scale)"
)

# Attendance field: percentage strictly bounded between 0 and 100
ATTENDANCE_FIELD = Field(
    None,
    ge=0,
    le=100,
    description="Attendance percentage (0 to 100)"
)

# Student ID field: alphanumeric with underscores/hyphens, 4-20 chars
# Pattern prevents injection while allowing common ID formats
STUDENT_ID_FIELD = Field(
    ...,
    pattern=r'^[A-Za-z0-9_-]{4,20}$',
    min_length=4,
    max_length=20,
    description="Student identifier (4-20 alphanumeric characters, underscores, or hyphens)"
)
