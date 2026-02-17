"""
Database Queries
---------------
Common database query helpers and utilities.
"""

from sqlalchemy.orm import Session
from typing import Optional


def get_student_by_id(db: Session, student_id: str):
    """
    Retrieve a student by ID.
    
    Args:
        db: Database session
        student_id: Student identifier
        
    Returns:
        Student model instance or None if not found
    """
    from backend.database.models.student import Student
    return db.query(Student).filter(Student.id == student_id).first()


def get_students_by_ids(db: Session, student_ids: list[str]):
    """
    Retrieve multiple students by IDs.
    
    Args:
        db: Database session
        student_ids: List of student identifiers
        
    Returns:
        List of Student model instances
    """
    from backend.database.models.student import Student
    return db.query(Student).filter(Student.id.in_(student_ids)).all()


def get_all_students(db: Session, skip: int = 0, limit: int = 100):
    """
    Get all students with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Max number of records to return
        
    Returns:
        List of Student model instances
    """
    from backend.database.models.student import Student
    return db.query(Student).offset(skip).limit(limit).all()


def get_student_count(db: Session) -> int:
    """
    Get total count of students.

    Args:
        db: Database session

    Returns:
        Total number of students
    """
    from backend.database.models.student import Student
    return db.query(Student).count()


def get_prediction_by_student_id(db: Session, student_id: str):
    """
    Retrieve a prediction by student ID.

    Args:
        db: Database session
        student_id: Student identifier (string)

    Returns:
        Prediction model instance or None if not found
    """
    from backend.database.models.prediction import Prediction
    return db.query(Prediction).filter(Prediction.student_id == student_id).first()


def get_all_predictions(db: Session, skip: int = 0, limit: int = 5000):
    """
    Get all predictions with pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Max number of records to return

    Returns:
        List of Prediction model instances
    """
    from backend.database.models.prediction import Prediction
    return db.query(Prediction).offset(skip).limit(limit).all()


def get_interventions_by_student_id(db: Session, student_id: str, limit: int = 10):
    """
    Retrieve interventions for a student.

    Args:
        db: Database session
        student_id: Student identifier (string)
        limit: Max number of interventions to return

    Returns:
        List of Intervention model instances
    """
    from backend.database.models.intervention import Intervention
    return db.query(Intervention).filter(
        Intervention.student_id == student_id
    ).order_by(Intervention.date.desc()).limit(limit).all()
