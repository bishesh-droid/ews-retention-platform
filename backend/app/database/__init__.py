"""
Database Package
---------------
Database connection, session management, and query utilities.
"""

from backend.app.database.connection import engine, Base, init_db
from backend.app.database.session import SessionLocal, get_db
from backend.app.database.queries import (
    get_student_by_id,
    get_students_by_ids,
    get_all_students,
    get_student_count,
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
]
