"""
Schemas Package
--------------
Pydantic schemas for request/response validation.
"""

from backend.schemas.common import PredictionResult, MessageResponse, ErrorResponse
from backend.schemas.student import Student, StudentCreate, StudentBase
from backend.schemas.prediction import Prediction, PredictionCreate, PredictionBase
from backend.schemas.intervention import (
    Intervention, InterventionCreate, InterventionBase,
    Recommendation, RecommendationCreate, RecommendationBase
)
from backend.schemas.llm import (
    PatternDiscovery, PatternDiscoveryCreate, PatternDiscoveryBase,
    LLMQueryBase, LLMInsightBase
)
from backend.schemas.event import (
    RawEvent, RawEventCreate, RawEventBase,
    EngineeredFeatures, EngineeredFeaturesCreate, EngineeredFeaturesBase,
    StudentResponse, StudentResponseCreate, StudentResponseBase
)

__all__ = [
    # Common
    "PredictionResult",
    "MessageResponse",
    "ErrorResponse",
    # Student
    "Student",
    "StudentCreate",
    "StudentBase",
    # Prediction
    "Prediction",
    "PredictionCreate",
    "PredictionBase",
    # Intervention
    "Intervention",
    "InterventionCreate",
    "InterventionBase",
    "Recommendation",
    "RecommendationCreate",
    "RecommendationBase",
    # LLM
    "PatternDiscovery",
    "PatternDiscoveryCreate",
    "PatternDiscoveryBase",
    "LLMQueryBase",
    "LLMInsightBase",
    # Events
    "RawEvent",
    "RawEventCreate",
    "RawEventBase",
    "EngineeredFeatures",
    "EngineeredFeaturesCreate",
    "EngineeredFeaturesBase",
    "StudentResponse",
    "StudentResponseCreate",
    "StudentResponseBase",
]
