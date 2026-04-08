"""
Pytest fixtures for backend tests.
"""

import os
import pytest
from unittest.mock import MagicMock, create_autospec
from sqlalchemy.orm import Session


# Ensure TESTING environment is set for all tests
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production-x7f9k2m"

# All tests use the in-memory DB automatically


@pytest.fixture
def mock_db_session():
    """
    Returns a mocked SQLAlchemy Session for testing.
    
    Usage:
        def test_something(mock_db_session):
            # Configure mock as needed
            mock_db_session.query.return_value.filter.return_value.first.return_value = None
            # Call function under test
    """
    session = create_autospec(Session, instance=True)
    return session


@pytest.fixture
def mock_student():
    """
    Returns a mock Student object with common attributes.
    """
    from backend.database.models.student import Student
    
    student = MagicMock(spec=Student)
    student.id = "test_student_001"
    student.org_defined_id = "2025EB110001"
    student.first_name = "Test"
    student.last_name = "Student"
    student.parent_department_name = "Computer Science"
    student.old_new_student = "new"
    student.is_active = True
    return student
