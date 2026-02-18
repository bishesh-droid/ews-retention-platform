"""
Database Connection
------------------
Database engine and declarative base configuration.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker # Add sessionmaker
from backend.config import DATABASE_URL

# Create database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create declarative base for models
Base = declarative_base()

# Configure SessionLocal
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database by creating all tables.
    Should be called on application startup.
    """
    # Import all models to ensure they're registered with Base
    from backend.database.models import (
        Student, Course, Enrollment, Prediction, Intervention, LLMQuery,
        LLMInsight, AIExplanation, PatternDiscovery, RawEvent,
        EngineeredFeatures, StudentResponse, User, GradedComponent, ExamRecord
    )
    
    Base.metadata.create_all(bind=engine)
