"""
Database Connection
------------------
Database engine and declarative base configuration.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base
from backend.config import DATABASE_URL


def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Configure SQLite connection settings for each new connection."""
    cursor = dbapi_connection.cursor()
    # Enable foreign key enforcement (disabled by default in SQLite)
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


# Create database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Attach pragma configuration to every new connection
event.listen(engine, "connect", _set_sqlite_pragmas)

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
