"""
Database Connection
------------------
Database engine and declarative base configuration.

Supports both synchronous and asynchronous operations:
- sync engine: for background tasks, migrations, admin scripts
- async engine: for FastAPI async route handlers (recommended)
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator, Generator
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from backend.config import DATABASE_URL
import asyncio


def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Configure SQLite connection settings for each new connection (sync)."""
    cursor = dbapi_connection.cursor()
    # Enable foreign key enforcement (disabled by default in SQLite)
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


# ============================================================================
# SYNCHRONOUS DATABASE (for background tasks, migrations, admin scripts)
# ============================================================================

# Create sync engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Attach pragma configuration to every new connection
event.listen(engine, "connect", _set_sqlite_pragmas)

# Sync session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# ============================================================================
# ASYNCHRONOUS DATABASE (for FastAPI async route handlers)
# ============================================================================

# Convert SQLite URL to async version (aiosqlite)
# Handle both file-based and in-memory SQLite databases
if DATABASE_URL == "sqlite:///:memory:":
    ASYNC_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
elif DATABASE_URL.startswith("sqlite:///"):
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Create async engine
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    # Pool settings for async
    pool_pre_ping=True,
    echo=False,  # Set True for debugging SQL
)


async def _set_async_sqlite_pragmas(conn):
    """Configure SQLite connection settings for each new async connection."""
    # Enable foreign key enforcement
    await conn.execute(text("PRAGMA foreign_keys = ON"))


# Async session factory
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Create declarative base for models
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Canonical sync DB dependency for FastAPI sync endpoints."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def get_db_async() -> AsyncGenerator[AsyncSession, None]:
    """
    Canonical async DB dependency for FastAPI async endpoints.

    Usage:
        @router.get("/students")
        async def get_students(db: AsyncSession = Depends(get_db_async)):
            result = await db.execute(select(Student))
            students = result.scalars().all()
            return students
    """
    async with AsyncSessionLocal() as session:
        # Configure SQLite pragmas for this session
        await _set_async_sqlite_pragmas(session.bind)
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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
