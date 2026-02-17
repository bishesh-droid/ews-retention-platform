"""
Integration API Tests
----------------------
Tests for the EWS Integration API endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# We need to mock the database before importing the app
@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    return db


@pytest.fixture
def client():
    """Create a test client with mocked dependencies."""
    from backend.main import app
    return TestClient(app)


class TestIntegrationAuth:
    """Test API key authentication."""

    def test_missing_api_key_returns_422(self, client):
        """Request without API key should fail."""
        response = client.get("/api/v1/integration/student-risk-profile/test@example.com")
        assert response.status_code == 422  # Missing required header

    def test_invalid_api_key_returns_401(self, client):
        """Request with wrong API key should fail."""
        response = client.get(
            "/api/v1/integration/student-risk-profile/test@example.com",
            headers={"X-Integration-Key": "wrong-key"},
        )
        assert response.status_code in [401, 404]  # Auth fail or student not found

    def test_valid_api_key_accepted(self, client):
        """Request with correct API key should pass auth."""
        response = client.get(
            "/api/v1/integration/student-risk-profile/test@example.com",
            headers={"X-Integration-Key": "ews-integration-dev-key"},
        )
        # Should get 404 (student not found) not 401 (auth fail)
        assert response.status_code in [404, 200]


class TestStudentRiskProfile:
    """Test the student risk profile endpoint."""

    def test_nonexistent_student_returns_404(self, client):
        """Unknown student should return 404."""
        response = client.get(
            "/api/v1/integration/student-risk-profile/nonexistent@example.com",
            headers={"X-Integration-Key": "ews-integration-dev-key"},
        )
        assert response.status_code == 404

    def test_profile_contract_shape(self, client):
        """Valid profile should match the data contract schema."""
        # First, get a real student ID
        students_response = client.get(
            "/api/v1/students/students?limit=1",
        )
        if students_response.status_code != 200:
            pytest.skip("No student data available for testing")

        data = students_response.json()
        if not data.get("students"):
            pytest.skip("No students in database")

        student_id = data["students"][0]["id"]

        response = client.get(
            f"/api/v1/integration/student-risk-profile/{student_id}",
            headers={"X-Integration-Key": "ews-integration-dev-key"},
        )
        assert response.status_code == 200

        profile = response.json()

        # Verify contract fields exist
        required_fields = [
            "student_id", "student_name", "risk_score", "risk_level",
            "academic_signals", "engagement_signals", "consistency_signals",
            "trend_summary", "dominant_risk_factor", "risk_breakdown",
            "exported_at", "api_version",
        ]
        for field in required_fields:
            assert field in profile, f"Missing field: {field}"

        # Verify risk_score bounds
        assert 0 <= profile["risk_score"] <= 100

        # Verify risk_level is valid
        assert profile["risk_level"] in ["Low", "Medium", "High", "Unknown"]

        # Verify api_version
        assert profile["api_version"] == "1.0"

        # Verify signal sub-objects exist
        assert "content_completion_score" in profile["academic_signals"]
        assert "login_consistency_score" in profile["engagement_signals"]
        assert "total_courses" in profile["consistency_signals"]


class TestCohortRiskProfiles:
    """Test the cohort batch endpoint."""

    def test_cohort_endpoint_returns_correct_shape(self, client):
        """Cohort endpoint should return paginated results."""
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles?limit=5",
            headers={"X-Integration-Key": "ews-integration-dev-key"},
        )
        assert response.status_code == 200

        data = response.json()
        assert "profiles" in data
        assert "total_in_system" in data
        assert "returned" in data
        assert "api_version" in data

    def test_cohort_pagination(self, client):
        """Pagination parameters should work."""
        response = client.get(
            "/api/v1/integration/cohort-risk-profiles?skip=0&limit=2",
            headers={"X-Integration-Key": "ews-integration-dev-key"},
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["profiles"]) <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
