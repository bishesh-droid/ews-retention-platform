"""
Intervention Schemas
-------------------
Pydantic schemas for intervention data.
"""

from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date


class InterventionBase(BaseModel):
    """Base intervention schema."""
    date: date
    user: str
    action: str
    status: Optional[str] = "Pending"
    assigned_faculty: Optional[str] = None
    risk_score_at_trigger: Optional[float] = None
    threshold_category: Optional[str] = None
    channels: Optional[List[str]] = None
    assigned_team: Optional[str] = None


class InterventionCreate(BaseModel):
    """Schema for creating an intervention."""
    student_id: Optional[str] = None
    student_ids: Optional[List[str]] = None
    date: Optional[date] = None
    user: str
    action: str
    status: Optional[str] = "Pending"
    assigned_faculty: Optional[str] = None
    risk_score_at_trigger: Optional[float] = None
    threshold_category: Optional[str] = None
    channels: Optional[List[str]] = None
    assigned_team: Optional[str] = None


class Intervention(InterventionBase):
    """Full intervention schema with metadata."""
    id: int
    student_id: str
    ai_suggested: Optional[int] = 0
    ai_reasoning: Optional[str] = None
    effectiveness_score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class RecommendationBase(BaseModel):
    """Base recommendation schema."""
    recommendation: str


class RecommendationCreate(RecommendationBase):
    """Schema for creating a recommendation."""
    pass


class Recommendation(RecommendationBase):
    """Full recommendation schema."""
    id: int
    student_id: str
    
    model_config = ConfigDict(from_attributes=True)
