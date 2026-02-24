"""
Database Package
---------------
Database connection, session management, and query utilities.
"""

from backend.database.connection import engine, Base, init_db
from backend.database.session import SessionLocal, get_db
from backend.database.queries import (
    get_student_by_id,
    get_students_by_ids,
    get_all_students,
    get_student_count,
)
from backend.database.models import (
    User,
    Student,
    Course,
    Enrollment,
    Prediction,
    Intervention,
    LLMQuery,
    LLMInsight,
    AIExplanation,
    PatternDiscovery,
    RawEvent,
    EngineeredFeatures,
    StudentResponse,
    GradedComponent,
    ExamRecord,
    Goal,
    RiskSnapshot,
    AuditLog,
    DimStudent,
    DimCourse,
    FactAcademicPerformance,
    FactEngagement,
    FactConsistency,
    FactIntentResponsiveness,
    DataLineage,
)

__all__ = [
    "engine",
    "Base",
    "init_db",
    "SessionLocal",
    "get_db",
    "get_student_by_id",
    "get_students_by_ids",
    "get_all_students",
    "get_student_count",
    "User",
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
