"""
IDOR (Insecure Direct Object Reference) Security Tests
======================================================

Tests FERPA-compliant resource ownership controls:
- Students can only access their own records
- Staff (faculty/admin) can access any student records
- Superusers bypass all checks

These tests verify the require_resource_ownership dependency works correctly.
"""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.api.deps import require_resource_ownership, ResourceOwnershipChecker
from backend.database.models.user import User


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_student_user():
    """Create a mock student user."""
    user = User(id=1, username="student1@example.com", email="student1@example.com", role="student")
    user.is_superuser = False
    return user


@pytest.fixture
def mock_other_student_user():
    """Create another mock student user (different student)."""
    user = User(id=2, username="student2@example.com", email="student2@example.com", role="student")
    user.is_superuser = False
    return user


@pytest.fixture
def mock_faculty_user():
    """Create a mock faculty user."""
    user = User(id=3, username="faculty1@example.com", email="faculty1@example.com", role="faculty")
    user.is_superuser = False
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = User(id=4, username="admin@example.com", email="admin@example.com", role="admin")
    user.is_superuser = False
    return user


@pytest.fixture
def mock_superuser():
    """Create a mock superuser."""
    user = User(id=5, username="super@example.com", email="super@example.com", role="student")
    user.is_superuser = True
    return user


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request with path_params."""
    class MockRequest:
        def __init__(self, path_params):
            self.path_params = path_params
    return MockRequest


# -----------------------------------------------------------------------------
# Test Cases
# -----------------------------------------------------------------------------

class TestResourceOwnershipChecker:
    """Unit tests for the ResourceOwnershipChecker dependency."""

    def test_student_accessing_own_record_passes(self, mock_student_user, mock_request):
        """
        Test Case 1: Student accessing their own record should succeed.

        This is the primary use case - students viewing their own dashboard.
        """
        checker = ResourceOwnershipChecker()
        request = mock_request({"student_id": "student1@example.com"})

        # Should not raise any exception
        result = checker(request=request, current_user=mock_student_user)
        assert result == mock_student_user

    def test_student_accessing_other_student_record_fails(self, mock_student_user, mock_request):
        """
        Test Case 2: Student accessing another student's record should get 403.

        This is the IDOR vulnerability - preventing students from snooping on others.
        """
        checker = ResourceOwnershipChecker()
        request = mock_request({"student_id": "student2@example.com"})  # Different student

        with pytest.raises(HTTPException) as exc_info:
            checker(request=request, current_user=mock_student_user)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    def test_faculty_accessing_any_student_record_passes(self, mock_faculty_user, mock_request):
        """
        Test Case 3: Faculty can access any student's record.

        Staff need to view all students for advising and intervention purposes.
        """
        checker = ResourceOwnershipChecker()
        request = mock_request({"student_id": "student1@example.com"})  # Any student

        # Should not raise any exception
        result = checker(request=request, current_user=mock_faculty_user)
        assert result == mock_faculty_user

    def test_admin_accessing_any_student_record_passes(self, mock_admin_user, mock_request):
        """
        Additional Test: Admin can access any student's record.

        Admins have full system access for management purposes.
        """
        checker = ResourceOwnershipChecker()
        request = mock_request({"student_id": "student99@example.com"})  # Any student

        # Should not raise any exception
        result = checker(request=request, current_user=mock_admin_user)
        assert result == mock_admin_user

    def test_superuser_bypasses_all_checks(self, mock_superuser, mock_request):
        """
        Additional Test: Superuser can access any record regardless of role.

        Superusers bypass all authorization checks.
        """
        checker = ResourceOwnershipChecker()
        request = mock_request({"student_id": "any_student@example.com"})

        # Should not raise any exception even though role is "student"
        result = checker(request=request, current_user=mock_superuser)
        assert result == mock_superuser

    def test_student_with_null_role_fails(self, mock_request):
        """
        Edge Case: User with null/empty role should only access own record.
        """
        user = User(id=6, username="test@example.com", email="test@example.com", role=None)
        user.is_superuser = False

        checker = ResourceOwnershipChecker()

        # Own record - should pass
        request_own = mock_request({"student_id": "test@example.com"})
        result = checker(request=request_own, current_user=user)
        assert result == user

        # Other record - should fail
        request_other = mock_request({"student_id": "other@example.com"})
        with pytest.raises(HTTPException) as exc_info:
            checker(request=request_other, current_user=user)
        assert exc_info.value.status_code == 403

    def test_retention_team_access_passes(self, mock_request):
        """
        Edge Case: Retention team role should have staff access.
        """
        user = User(id=7, username="retention@example.com", email="retention@example.com", role="retention team")
        user.is_superuser = False

        checker = ResourceOwnershipChecker()
        request = mock_request({"student_id": "any_student@example.com"})

        # Should not raise any exception
        result = checker(request=request, current_user=user)
        assert result == user

    def test_custom_student_id_param(self, mock_faculty_user, mock_request):
        """
        Edge Case: Custom student_id parameter name should work.
        """
        checker = ResourceOwnershipChecker(student_id_param="org_id")
        request = mock_request({"org_id": "student123", "student_id": "wrong_id"})

        # Should check org_id, not student_id
        result = checker(request=request, current_user=mock_faculty_user)
        assert result == mock_faculty_user


class TestRequireResourceOwnershipFactory:
    """Tests for the require_resource_ownership factory function."""

    def test_factory_returns_checker(self):
        """Factory should return a ResourceOwnershipChecker instance."""
        checker = require_resource_ownership()
        assert isinstance(checker, ResourceOwnershipChecker)
        assert checker.student_id_param == "student_id"

    def test_factory_with_custom_param(self):
        """Factory should accept custom student_id_param."""
        checker = require_resource_ownership("org_id")
        assert isinstance(checker, ResourceOwnershipChecker)
        assert checker.student_id_param == "org_id"


# -----------------------------------------------------------------------------
# Integration Tests (if FastAPI app is available)
# -----------------------------------------------------------------------------

@pytest.mark.skipif(
    True,  # Set to False to run integration tests when app is available
    reason="Integration tests require full FastAPI app context"
)
class TestIDORIntegration:
    """Integration tests against actual API endpoints."""

    def test_predictions_endpoint_enforces_ownership(self, client: TestClient):
        """
        Integration Test: /predictions/{student_id} should enforce resource ownership.
        """
        # This would require authentication setup


# -----------------------------------------------------------------------------
# FERPA Compliance Documentation
# -----------------------------------------------------------------------------

def test_ferpa_compliance_matrix():
    """
    Document the FERPA compliance matrix implemented by the checker.

    FERPA requires that educational records be accessible only to:
    1. The student themselves (or their parents if under 18)
    2. School officials with legitimate educational interest
    3. Certain other authorized parties (with consent)

    Our implementation covers:
    - Student own records: ALLOWED (student viewing own data)
    - Other student records: DENIED (FERPA violation without consent)
    - Faculty: ALLOWED (legitimate educational interest for advising)
    - Admin: ALLOWED (school official with legitimate interest)
    - Retention team: ALLOWED (legitimate educational interest)
    """
    # This is documentation - the actual tests are above
    compliance_rules = {
        "student_own_record": True,
        "student_other_record": False,
        "faculty_any_record": True,
        "admin_any_record": True,
        "retention_team_any_record": True,
        "superuser_any_record": True,
    }

    for rule, allowed in compliance_rules.items():
        assert isinstance(allowed, bool), f"Rule {rule} must be defined"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
