"""
Pytest fixtures for backend tests.
"""

import hashlib
import os
import pytest
from unittest.mock import MagicMock, create_autospec
from sqlalchemy.orm import Session


# Ensure TESTING environment is set for all tests
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production-x7f9k2m"

# Configure greenlet for SQLAlchemy async/sync compatibility
os.environ["SQLALCHEMY_WARN_20"] = "0"

# Pre-configure integration API key hash so integration tests can authenticate
_INTEGRATION_DEV_KEY = "ews-integration-dev-key"
os.environ["INTEGRATION_API_KEY_HASH"] = hashlib.sha256(
    _INTEGRATION_DEV_KEY.encode()
).hexdigest()


@pytest.fixture(autouse=True, scope="session")
def initialize_test_db():
    """Create all DB tables once per test session before any test runs."""
    from backend.database.connection import init_db
    init_db()
    yield


@pytest.fixture(autouse=True, scope="function")
def cleanup_db_after_each_test():
    """
    Clean up database after each test function to ensure test isolation.
    This runs automatically for all tests.
    """
    yield
    from backend.database.connection import SessionLocal, Base

    db = SessionLocal()
    try:
        # Delete data in reverse dependency order to avoid FK violations
        for table in reversed(Base.metadata.sorted_tables):
            if table.name != 'sqlite_sequence':
                db.execute(table.delete())
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture
def client():
    """
    Returns a TestClient with proper app state initialization.
    This ensures rate limiter and other state is set for integration tests.
    Database cleanup is handled by the autouse cleanup_db_after_each_test fixture.
    """
    from backend.main import app
    from backend.core.rate_limiting import limiter
    from backend.database.connection import init_db
    from fastapi.testclient import TestClient

    # Initialize app state that would normally be set during lifespan startup
    app.state.limiter = limiter

    # Initialize database synchronously before tests
    init_db()

    # Use TestClient for app testing
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # Clean up dependency overrides after test
        app.dependency_overrides.clear()


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
