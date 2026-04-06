"""
Database Connection
------------------
Database engine and declarative base configuration.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from backend.config import DATABASE_URL

# Create database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create declarative base for models
Base = declarative_base()


def init_db():
    """
    Initialize database by creating all tables.
    Should be called on application startup.
    Imports every model so SQLAlchemy registers them with Base.metadata
    before create_all is called.
    """
    from backend.database.models import (  # noqa: F401
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
        User,
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

    Base.metadata.create_all(bind=engine)
