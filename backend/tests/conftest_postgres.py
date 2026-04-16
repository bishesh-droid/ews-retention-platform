"""
PostgreSQL Test Configuration
-----------------------------
Provides PostgreSQL-based test configuration for proper FK constraint validation.

Usage:
    TEST_MODE=postgres pytest -xvs backend/tests/test_fk_constraints.py

This module provides:
- PostgreSQL engine/session fixtures
- FK constraint validation tests
- Integration with existing test fixtures

PostgreSQL is preferred over SQLite for tests that validate:
- Foreign key constraint enforcement
- CASCADE behaviors
- Transaction isolation
- Database-specific SQL behaviors
"""

import os
import pytest
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy_utils import database_exists, create_database

# PostgreSQL connection string - uses environment or defaults to local test db
POSTGRES_TEST_URL = os.getenv(
    "POSTGRES_TEST_URL",
    "postgresql://postgres:postgres@localhost:5432/ews_test_db"
)

# Create PostgreSQL engine with proper settings for tests


def get_postgres_engine():
    """Create a PostgreSQL engine with proper test settings."""
    return create_engine(
        POSTGRES_TEST_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        echo=False,
    )


@pytest.fixture(scope="session")
def postgres_engine():
    """
    PostgreSQL engine fixture - session scoped.
    Creates test database if it doesn't exist.
    """
    engine = get_postgres_engine()
    
    # Create database if it doesn't exist
    if not database_exists(engine.url):
        create_database(engine.url)
    
    yield engine
    
    # Cleanup after all tests
    engine.dispose()


@pytest.fixture(scope="function")
def postgres_db(postgres_engine):
    """
    PostgreSQL database fixture - function scoped.
    Creates all tables before each test, drops after.
    """
    from backend.database.models import Base
    
    # Create all tables
    Base.metadata.create_all(bind=postgres_engine)
    
    yield postgres_engine
    
    # Drop all tables to ensure clean state
    Base.metadata.drop_all(bind=postgres_engine)


@pytest.fixture
def postgres_session(postgres_db) -> Generator[Session, None, None]:
    """
    PostgreSQL session fixture.
    Provides a transactional session that rolls back after test.
    """
    connection = postgres_db.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def postgres_client(postgres_db):
    """
    FastAPI TestClient with PostgreSQL database.
    """
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.database.connection import get_db
    
    # Create a session bound to the test transaction
    connection = postgres_db.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Initialize app state
    from backend.core.rate_limiting import limiter
    app.state.limiter = limiter
    
    with TestClient(app) as client:
        yield client
    
    # Cleanup
    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@contextmanager
def postgres_transaction_session(postgres_engine):
    """
    Context manager for PostgreSQL transactional sessions.
    Useful for integration tests that need manual transaction control.
    
    Usage:
        with postgres_transaction_session(engine) as session:
            # Do database operations
            session.commit()
    """
    connection = postgres_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    try:
        yield session
    except Exception:
        transaction.rollback()
        raise
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def pytest_addoption(parser):
    """Add custom pytest option for test mode."""
    parser.addoption(
        "--test-mode",
        action="store",
        default="sqlite",
        help="Test mode: 'sqlite' (default) or 'postgres'",
    )


def pytest_configure(config):
    """Configure pytest based on test mode."""
    test_mode = config.getoption("--test-mode")
    os.environ["TEST_MODE"] = test_mode
    
    if test_mode == "postgres":
        # Set TESTING=false temporarily so DATABASE_URL from environment is used
        os.environ["TESTING"] = "false"
        os.environ["DATABASE_URL"] = POSTGRES_TEST_URL
    else:
        os.environ["TESTING"] = "true"
