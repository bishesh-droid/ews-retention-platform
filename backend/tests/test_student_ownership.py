"""
Test student ownership verification (SEC-7 fix).

Tests that ownership is determined by email match, not username.
This ensures students can access their own data even if their
username differs from their institutional email.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock

from backend.api.deps import ResourceOwnershipChecker
from backend.core.constants import Role
from backend.database.models.user import User
from backend.database.models.student import Student


class TestStudentOwnershipEmailMismatch:
    """
    Test that student ownership is verified by email match, not username.

    SEC-7: Fixed ownership check to use email comparison instead of
    username comparison, allowing students with nicknames as usernames
    to access their own data.
    """

    def test_ownership_check_passes_when_email_matches(self):
        """
        Test that ownership check PASSES when student email matches user email,
        even if username is different.

        Scenario: User registered with nickname as username but institutional
        email as email address.
        """
        # Create a user with username != email (nickname scenario)
        user = MagicMock(spec=User)
        user.id = 1
        user.username = "nickname"  # Different from email
        user.email = "student@bits.edu"
        user.role = Role.STUDENT
        user.is_superuser = False

        # Create a student with id matching the email
        student = MagicMock(spec=Student)
        student.id = "student@bits.edu"
        student.email = "student@bits.edu"

        # Mock the database query to return the student
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = student

        checker = ResourceOwnershipChecker()

        # Create mock request with student_id in path params
        mock_request = MagicMock()
        mock_request.path_params = {"student_id": "student@bits.edu"}

        # Should NOT raise an exception - ownership is verified by email match
        result = checker(mock_request, user, mock_db)
        assert result == user

    def test_ownership_check_fails_when_email_mismatch(self):
        """
        Test that ownership check FAILS when student email does not match
        user email and user is not staff.

        Scenario: Different user tries to access another student's data.
        """
        # Create a user trying to access another student's data
        user = MagicMock(spec=User)
        user.id = 2
        user.username = "other_user"
        user.email = "other@bits.edu"  # Different from student email
        user.role = Role.STUDENT
        user.is_superuser = False

        # Create a student with different email
        student = MagicMock(spec=Student)
        student.id = "student@bits.edu"
        student.email = "student@bits.edu"  # Different from user email

        # Mock the database query to return the student
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = student

        checker = ResourceOwnershipChecker()

        # Create mock request with student_id in path params
        mock_request = MagicMock()
        mock_request.path_params = {"student_id": "student@bits.edu"}

        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            checker(mock_request, user, mock_db)

        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    def test_ownership_check_fails_when_student_not_found(self):
        """
        Test that ownership check returns 404 when the student owns the ID
        (email matches) but the record does not exist in the database.
        Authorization precedes existence: a mismatched email yields 403, so
        we must match email == student_id to reach the 404 branch.
        """
        student_id = "nonexistent@bits.edu"
        user = MagicMock(spec=User)
        user.id = 1
        user.username = "nickname"
        user.email = student_id  # ownership passes; record still missing
        user.role = Role.STUDENT
        user.is_superuser = False

        # Mock the database query to return None (student not found)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        checker = ResourceOwnershipChecker()

        mock_request = MagicMock()
        mock_request.path_params = {"student_id": student_id}

        # Should raise 404 Not Found
        with pytest.raises(HTTPException) as exc_info:
            checker(mock_request, user, mock_db)

        assert exc_info.value.status_code == 404
        assert "Student not found" in exc_info.value.detail

    def test_staff_can_access_any_student(self):
        """
        Test that staff roles (admin, faculty, retention team) can access
        any student record regardless of email match.
        """
        for role in [Role.ADMIN, Role.FACULTY, Role.RETENTION_TEAM]:
            user = MagicMock(spec=User)
            user.id = 1
            user.username = "staff_user"
            user.email = "staff@bits.edu"
            user.role = role
            user.is_superuser = False

            checker = ResourceOwnershipChecker()

            mock_request = MagicMock()
            mock_request.path_params = {"student_id": "any_student@bits.edu"}

            # Staff should bypass ownership check entirely
            result = checker(mock_request, user)
            assert result == user, f"Staff role {role} should bypass ownership check"

    def test_superuser_can_access_any_student(self):
        """
        Test that superusers can access any student record regardless of email.
        """
        user = MagicMock(spec=User)
        user.id = 1
        user.username = "superuser"
        user.email = "super@bits.edu"
        user.role = Role.STUDENT  # Even with student role
        user.is_superuser = True

        checker = ResourceOwnershipChecker()

        mock_request = MagicMock()
        mock_request.path_params = {"student_id": "any_student@bits.edu"}

        # Superuser should bypass ownership check
        result = checker(mock_request, user)
        assert result == user
