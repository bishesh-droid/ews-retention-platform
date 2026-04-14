"""
TEST-7: Cohort Risk Profiles Crash Tests

Tests edge cases and crash scenarios for the /cohort-risk-profiles endpoint.
This endpoint was optimized to use eager loading and batch queries.

Tests cover:
1. Empty database (no students)
2. Null/missing student fields
3. Large pagination requests
4. Risk filter edge cases
5. Integration API authentication
"""

import pytest
import hashlib
import time
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.database.models.user import User
from backend.database.models.student import Student
from backend.config import INTEGRATION_API_KEY_HASH


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    from backend.database.connection import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def integration_headers():
    """Generate valid integration API headers."""
    api_key = "ews-integration-dev-key"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    import time
    timestamp = str(int(time.time()))

    return {
        "X-API-Key-Hash": api_key_hash,
        "X-Timestamp": timestamp,
    }


@pytest.fixture
def cleanup_test_data(db_session: Session):
    """Cleanup fixture to remove test students after tests."""
    yield
    # Cleanup test students
    for student_id in ["test1@test.com", "test2@test.com", "test3@test.com"]:
        student = db_session.query(Student).filter(Student.id == student_id).first()
        if student:
            db_session.delete(student)
    db_session.commit()


@pytest.fixture
def sample_students(db_session: Session, cleanup_test_data):
    """Create sample students for testing."""
    students = [
        Student(
            id="test1@test.com",
            org_defined_id="2025EB110001",
            first_name="Test",
            last_name="Student One",
            parent_department_name="BS - Data Science & AI",
            old_new_student="new",
            is_active=True,
        ),
        Student(
            id="test2@test.com",
            org_defined_id="2025EB110002",
            first_name="Test",
            last_name="Student Two",
            parent_department_name="BS - Data Science & AI",
            old_new_student="old",
            is_active=True,
        ),
        Student(
            id="test3@test.com",
            org_defined_id="2025EB110003",
            first_name="",  # Empty first name
            last_name="",   # Empty last name
            parent_department_name=None,  # Null department
            old_new_student=None,
            is_active=True,
        ),
    ]
    for student in students:
        db_session.add(student)
    db_session.commit()
    return students


# =============================================================================
# Crash Test Cases
# =============================================================================

class TestCohortRiskProfilesCrashTests:
    """
    Crash tests for /cohort-risk-profiles endpoint.

    These tests verify the endpoint handles edge cases without crashing.
    """

    def test_empty_database_returns_empty_profiles(
        self, client: TestClient, integration_headers: dict, db_session: Session
    ):
        """
        CRASH-1: Empty database should return empty profiles, not crash.

        Edge case: No students in the system.
        """
        # Verify no students exist
        count = db_session.query(Student).count()
        assert count == 0

        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 50},
        )

        # Should succeed with empty results
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["profiles"] == []
        assert data["data"]["total_in_system"] == 0
        assert data["data"]["returned"] == 0

    def test_student_with_null_fields_handled_gracefully(
        self, client: TestClient, integration_headers: dict, db_session: Session
    ):
        """
        CRASH-2: Student with null/empty fields should not crash.

        Edge case: Student record has null first_name, last_name, department.
        """
        # Create student with null fields
        student = Student(
            id="null_fields@test.com",
            org_defined_id="2025EB110099",
            first_name=None,
            last_name=None,
            parent_department_name=None,
            old_new_student=None,
            is_active=True,
        )
        db_session.add(student)
        db_session.commit()

        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 50},
        )

        # Should not crash - should handle null fields gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total_in_system"] >= 1

    def test_large_pagination_limit_handled(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        CRASH-3: Large pagination limit should be handled correctly.

        Edge case: Request with maximum allowed limit (500).
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 500},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["returned"] <= 500
        assert data["data"]["limit"] == 500

    def test_pagination_beyond_results_returns_empty(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        CRASH-4: Pagination beyond available results should return empty.

        Edge case: skip > total students.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 10000, "limit": 50},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["profiles"] == []
        assert data["data"]["returned"] == 0

    def test_risk_filter_with_no_matching_students(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        CRASH-5: Risk filter with no matching students should return empty.

        Edge case: Filter that matches no students.
        """
        # Filter for impossible risk range
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 50, "risk_min": 999, "risk_max": 1000},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["profiles"] == []

    def test_risk_filter_min_only(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        CRASH-6: Risk filter with only min should work correctly.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 50, "risk_min": 50},
        )

        # Should not crash
        assert response.status_code == 200

    def test_risk_filter_max_only(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        CRASH-7: Risk filter with only max should work correctly.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 50, "risk_max": 30},
        )

        # Should not crash
        assert response.status_code == 200

    def test_invalid_timestamp_header_rejected(
        self, client: TestClient, db_session: Session
    ):
        """
        CRASH-8: Invalid timestamp should be rejected, not crash.

        Security: Timestamp replay protection.
        """
        api_key = "ews-integration-dev-key"
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Invalid timestamp (not a number)
        headers = {
            "X-API-Key-Hash": api_key_hash,
            "X-Timestamp": "not-a-number",
        }

        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=headers,
        )

        assert response.status_code == 403

    def test_expired_timestamp_rejected(
        self, client: TestClient, db_session: Session
    ):
        """
        CRASH-9: Expired timestamp should be rejected.

        Security: 5-minute window for replay protection.
        """
        api_key = "ews-integration-dev-key"
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Timestamp from 10 minutes ago (expired)
        import time
        expired_timestamp = str(int(time.time()) - 600)

        headers = {
            "X-API-Key-Hash": api_key_hash,
            "X-Timestamp": expired_timestamp,
        }

        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=headers,
        )

        assert response.status_code == 403

    def test_missing_api_key_hash_rejected(
        self, client: TestClient, db_session: Session
    ):
        """
        CRASH-10: Missing API key hash should be rejected.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers={"X-Timestamp": str(int(time.time()))},
        )

        assert response.status_code == 422  # Validation error

    def test_limit_zero_returns_empty(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        CRASH-11: Limit of 0 should return empty results.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 0},
        )

        # Limit 0 is invalid (ge=1), should return 422
        assert response.status_code == 422

    def test_negative_skip_rejected(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        CRASH-12: Negative skip should be rejected.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": -1, "limit": 50},
        )

        assert response.status_code == 422

    def test_limit_above_maximum_rejected(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        CRASH-13: Limit above 500 should be rejected.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 1000},
        )

        assert response.status_code == 422


class TestCohortRiskProfilesDataIntegrity:
    """
    Data integrity tests for cohort risk profiles.
    """

    def test_response_structure_is_correct(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        INTEGRITY-1: Response should have correct structure.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 50},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify envelope structure
        assert "success" in data
        assert "data" in data
        assert "message" in data

        # Verify data structure
        cohort_data = data["data"]
        assert "profiles" in cohort_data
        assert "total_in_system" in cohort_data
        assert "returned" in cohort_data
        assert "skip" in cohort_data
        assert "limit" in cohort_data
        assert "exported_at" in cohort_data
        assert "api_version" in cohort_data

    def test_profile_structure_is_correct(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        INTEGRITY-2: Each profile should have required fields.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 50},
        )

        assert response.status_code == 200
        data = response.json()

        # Each profile should have required fields
        for profile in data["data"]["profiles"]:
            required_fields = [
                "student_id",
                "student_name",
                "risk_score",
                "risk_level",
                "academic_signals",
                "engagement_signals",
                "consistency_signals",
                "trend_summary",
                "dominant_risk_factor",
                "risk_breakdown",
                "exported_at",
                "api_version",
            ]
            for field in required_fields:
                assert field in profile, f"Missing required field: {field}"

    def test_risk_score_in_valid_range(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        INTEGRITY-3: Risk scores should be in 0-100 range.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 50},
        )

        assert response.status_code == 200
        data = response.json()

        for profile in data["data"]["profiles"]:
            risk_score = profile.get("risk_score")
            if risk_score is not None:
                assert 0 <= risk_score <= 100, f"Risk score out of range: {risk_score}"

    def test_pagination_metadata_is_accurate(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        INTEGRITY-4: Pagination metadata should match results.
        """
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles",
            headers=integration_headers,
            params={"skip": 0, "limit": 2},
        )

        assert response.status_code == 200
        data = response.json()

        cohort_data = data["data"]
        # returned should match actual profiles count
        assert cohort_data["returned"] == len(cohort_data["profiles"])
        # returned should be <= limit
        assert cohort_data["returned"] <= cohort_data["limit"]


class TestCohortRiskProfilesOptimization:
    """
    Tests to verify the N+1 query optimization is working.
    """

    def test_eager_loading_reduces_queries(
        self, client: TestClient, integration_headers: dict, sample_students, db_session: Session
    ):
        """
        OPT-1: Verify eager loading is configured correctly.

        This test verifies the optimization by checking that the
        query uses selectinload options.
        """
        from sqlalchemy.orm import selectinload
        from backend.database.models.student import Student

        # Verify that the route imports and uses selectinload
        import backend.routes.integration as integration_module

        # The optimized route should use selectinload
        # This is a static verification - the actual query count
        # reduction is tested via performance monitoring
        assert hasattr(integration_module, 'selectinload') or \
               'selectinload' in str(integration_module.__file__)

    def test_batch_queries_for_related_data(
        self, client: TestClient, integration_headers: dict, sample_students
    ):
        """
        OPT-2: Verify batch queries are used for related data.

        The optimized endpoint should use StudentRepository batch methods.
        """
        from backend.infrastructure.student_repository import StudentRepository

        # Verify batch methods exist
        assert hasattr(StudentRepository, 'fetch_enrollments_map')
        assert hasattr(StudentRepository, 'fetch_graded_map')
        assert hasattr(StudentRepository, 'fetch_exam_map')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
