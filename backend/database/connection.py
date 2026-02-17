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
    """
    # Import all models to ensure they're registered with Base
    from backend.database.models import student, prediction, intervention, llm, event, feature
    
    Base.metadata.create_all(bind=engine)
