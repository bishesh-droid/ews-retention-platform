"""
Database Connection
------------------
Database engine and declarative base configuration.
"""

from sqlalchemy import create_engine, event
from typing import AsyncGenerator, Generator
from sqlalchemy.orm import Session, declarative_base, sessionmaker
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

# Canonical session factory (single source of truth)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Canonical sync DB dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_db_async() -> AsyncGenerator[Session, None]:
    """Canonical async DB dependency for FastAPI async endpoints."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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
        IngestionRun,
        CourseContentRegistry,
        InterventionLog,
        DimStudent,
        DimCourse,
        FactAcademicPerformance,
        FactEngagement,
        FactConsistency,
        FactIntentResponsiveness,
        DataLineage,
    )

    Base.metadata.create_all(bind=engine)
