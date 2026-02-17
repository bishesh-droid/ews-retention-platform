"""
LLM Schemas
----------
Pydantic schemas for LLM-related data (queries, insights, patterns).
"""

from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Optional


class PatternDiscoveryBase(BaseModel):
    """Base pattern discovery schema."""
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
    """Schema for creating a pattern discovery."""
    pass


class PatternDiscovery(PatternDiscoveryBase):
    """Full pattern discovery schema."""
    id: int
    discovered_at: date
    acknowledged: int
    acted_upon: int
    
    model_config = ConfigDict(from_attributes=True)


# Future LLM schemas can be added here
class LLMQueryBase(BaseModel):
    """Base LLM query schema."""
    user_id: str
    user_role: str
    query_type: str
    input_data: str
    response: str
    confidence: str
    sources: Optional[str] = None


class LLMInsightBase(BaseModel):
    """Base LLM insight schema."""
    insight_type: str
    title: str
    content: str
    source_data: Optional[str] = None
    confidence: str
    visibility: str
