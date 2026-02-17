"""
Database Session Management
---------------------------
Session factory and dependency injection for FastAPI.
"""

from sqlalchemy.orm import sessionmaker, Session
from backend.database.connection import engine

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
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
    finally:
        db.close()
