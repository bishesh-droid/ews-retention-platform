"""
Models Package
-------------
Database models for the EWS Retention Platform.
"""

from backend.database.models.student import Student
from backend.database.models.course import Course
from backend.database.models.enrollment import Enrollment
from backend.database.models.prediction import Prediction
from backend.database.models.intervention import Intervention
from backend.database.models.llm import LLMQuery, LLMInsight, AIExplanation, PatternDiscovery
from backend.database.models.event import RawEvent, EngineeredFeatures
from backend.database.models.feature import StudentResponse
from .user import User
from .academic import GradedComponent, ExamRecord
from .goals_and_risks import Goal, RiskSnapshot
from .audit import AuditLog
from .canonical import (
    DimStudent,
    DimCourse,
    FactAcademicPerformance,
    FactEngagement,
    FactConsistency,
    FactIntentResponsiveness,
    DataLineage,
)

__all__ = [
    "Student",
    "Course",
    "Enrollment",
    "Prediction",
    "Intervention",
    "LLMQuery",
    "LLMInsight",
    "AIExplanation",
    "PatternDiscovery",
    "RawEvent",
    "EngineeredFeatures",
    "StudentResponse",
    "User",
    "GradedComponent",
    "ExamRecord",
    "Goal",
    "RiskSnapshot",
    "AuditLog",
    "DimStudent",
    "DimCourse",
    "FactAcademicPerformance",
    "FactEngagement",
    "FactConsistency",
    "FactIntentResponsiveness",
    "DataLineage",
]
