"""
Database Session Management
---------------------------
Session factory and dependency injection for FastAPI.
"""

from typing import AsyncGenerator, Generator

from sqlalchemy.orm import Session, sessionmaker
from backend.database.connection import engine

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI dependency injection.
    
    Yields:
        Session: SQLAlchemy database session
        
    Example:
        @app.get("/students")
        def get_students(db: Session = Depends(get_db)):
            return db.query(Student).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        # Ensure we don't keep a failed transaction open.
        db.rollback()
        raise
    finally:
        db.close()


async def get_db_async() -> AsyncGenerator[Session, None]:
    """
    Async dependency variant for FastAPI async endpoints.

    FastAPI may execute sync dependencies for async endpoints in a worker thread.
    This async generator keeps session creation in the event-loop thread.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
