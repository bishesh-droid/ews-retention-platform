"""
TEST-6: IDOR Tests for Recommendations Endpoint

Tests for Insecure Direct Object Reference (IDOR) vulnerabilities
in the recommendations API endpoint.

Security Requirements:
- Students can ONLY access their own recommendations
- Faculty/Admin/Retention team can access ANY student's recommendations
- All access attempts must be logged for FERPA compliance
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from backend.database.models.user import User
from backend.database.models.student import Student
from backend.core.auth import get_password_hash, create_access_token


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
def cleanup_test_users(db_session: Session):
    """Cleanup fixture to remove test users and students after tests."""
    from backend.database.models.student import Student
    from backend.database.models.enrollment import Enrollment
    from backend.database.models.academic import GradedComponent
    from backend.database.models.academic import ExamRecord

    yield
    # Cleanup related student data first
    student_ids = ["student1@test.com", "student2@test.com"]
    for student_id in student_ids:
        db_session.query(Enrollment).filter(
            Enrollment.student_id == student_id
        ).delete()
        db_session.query(GradedComponent).filter(
            GradedComponent.student_id == student_id
        ).delete()
        db_session.query(ExamRecord).filter(
            ExamRecord.student_id == student_id
        ).delete()
        student = db_session.query(Student).filter(Student.id == student_id).first()
        if student:
            db_session.delete(student)
    db_session.commit()

    # Cleanup test users
    for username in [
        "student1@test.com",
        "student2@test.com",
        "faculty@test.com",
        "admin@test.com",
    ]:
        user = db_session.query(User).filter(User.username == username).first()
        if user:
            db_session.delete(user)
    db_session.commit()


@pytest.fixture
def student1_user(db_session: Session, cleanup_test_users):
    """Create first student user."""
    user = User(
        username="student1@test.com",
        email="student1@test.com",
        hashed_password=get_password_hash("password123"),
        role="student",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student2_user(db_session: Session, cleanup_test_users):
    """Create second student user (for IDOR testing)."""
    user = User(
        username="student2@test.com",
        email="student2@test.com",
        hashed_password=get_password_hash("password123"),
        role="student",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def faculty_user(db_session: Session, cleanup_test_users):
    """Create faculty user."""
    user = User(
        username="faculty@test.com",
        email="faculty@test.com",
        hashed_password=get_password_hash("password123"),
        role="faculty",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session, cleanup_test_users):
    """Create admin user."""
    user = User(
        username="admin@test.com",
        email="admin@test.com",
        hashed_password=get_password_hash("password123"),
        role="admin",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student1_student_record(db_session: Session):
    """Create student record for student1."""
    student = Student(
        id="student1@test.com",
        org_defined_id="2025EB110001",
        first_name="Student",
        last_name="One",
        parent_department_name="BS - Data Science & AI",
        old_new_student="new",
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    return student


@pytest.fixture
def student2_student_record(db_session: Session):
    """Create student record for student2."""
    student = Student(
        id="student2@test.com",
        org_defined_id="2025EB110002",
        first_name="Student",
        last_name="Two",
        parent_department_name="BS - Data Science & AI",
        old_new_student="new",
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    return student


def get_auth_token(user: User) -> str:
    """Helper to create a valid access token for a user."""
    return create_access_token(
        subject=user.username,
        role=user.role,
    )


# =============================================================================
# IDOR Test Cases
# =============================================================================


class TestRecommendationsIDOR:
    """
    IDOR tests for recommendations endpoint.

    These tests verify that the ResourceOwnershipChecker properly
    prevents students from accessing other students' data.
    """

    def test_student_accessing_own_recommendations_succeeds(
        self,
        client: TestClient,
        student1_user: User,
        student1_student_record,
        db_session: Session,
    ):
        """
        IDOR-1: Student accessing their own recommendations should succeed (200).

        This is the legitimate use case - students viewing their own data.
        """
        token = get_auth_token(student1_user)

        # Mock the StudentService to return test data
        with patch(
            "backend.routes.recommendations.StudentService.get_student_by_id"
        ) as mock_get:
            mock_get.return_value = {
                "id": "student1@test.com",
                "risk_score": 45.0,
                "content_completion_score": 60.0,
                "graded_quiz_score": 55.0,
                "login_consistency_score": 70.0,
                "discussion_engagement_score": 40.0,
                "exam_attendance_rate": 90.0,
            }

            response = client.get(
                "/api/v1/recommendations/student1@test.com",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert "data" in response.json()
        assert isinstance(response.json()["data"], list)

    def test_student_accessing_other_student_recommendations_fails_403(
        self,
        client: TestClient,
        student1_user: User,
        student2_student_record,
        db_session: Session,
    ):
        """
        IDOR-2: Student accessing another student's recommendations should fail (403).

        This is the critical IDOR vulnerability - students must NOT be able
        to snoop on other students' recommendations.
        """
        token = get_auth_token(student1_user)

        # Attempt to access student2's recommendations
        response = client.get(
            "/api/v1/recommendations/student2@test.com",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should be forbidden
        assert response.status_code == 403
        body = response.json()
        detail = body.get("detail") or body.get("error", {}).get("message", "")
        assert "Access denied" in detail

    def test_student_accessing_random_student_recommendations_fails_403(
        self, client: TestClient, student1_user: User, db_session: Session
    ):
        """
        IDOR-3: Student accessing random student ID should fail (403).

        Test with a completely different student ID.
        """
        token = get_auth_token(student1_user)

        response = client.get(
            "/api/v1/recommendations/random_student@test.com",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Should be forbidden (access check happens before not-found check)
        assert response.status_code == 403

    def test_faculty_accessing_any_student_recommendations_succeeds(
        self,
        client: TestClient,
        faculty_user: User,
        student2_student_record,
        db_session: Session,
    ):
        """
        IDOR-4: Faculty accessing any student's recommendations should succeed (200).

        Faculty have legitimate educational interest in all student data.
        """
        token = get_auth_token(faculty_user)

        with patch(
            "backend.routes.recommendations.StudentService.get_student_by_id"
        ) as mock_get:
            mock_get.return_value = {
                "id": "student2@test.com",
                "risk_score": 45.0,
                "content_completion_score": 60.0,
                "graded_quiz_score": 55.0,
                "login_consistency_score": 70.0,
                "discussion_engagement_score": 40.0,
                "exam_attendance_rate": 90.0,
            }

            response = client.get(
                "/api/v1/recommendations/student2@test.com",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert "data" in response.json()

    def test_admin_accessing_any_student_recommendations_succeeds(
        self,
        client: TestClient,
        admin_user: User,
        student1_student_record,
        db_session: Session,
    ):
        """
        IDOR-5: Admin accessing any student's recommendations should succeed (200).

        Admins have full system access.
        """
        token = get_auth_token(admin_user)

        with patch(
            "backend.routes.recommendations.StudentService.get_student_by_id"
        ) as mock_get:
            mock_get.return_value = {
                "id": "student1@test.com",
                "risk_score": 45.0,
                "content_completion_score": 60.0,
            }

            response = client.get(
                "/api/v1/recommendations/student1@test.com",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200

    def test_unauthenticated_access_fails_401(
        self, client: TestClient, db_session: Session
    ):
        """
        IDOR-6: Unauthenticated access should fail (401).

        No anonymous access to recommendations.
        """
        response = client.get(
            "/api/v1/recommendations/student1@test.com",
        )

        assert response.status_code == 401

    def test_invalid_token_fails_401(self, client: TestClient, db_session: Session):
        """
        IDOR-7: Invalid token should fail (401).

        Forged or expired tokens should be rejected.
        """
        response = client.get(
            "/api/v1/recommendations/student1@test.com",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )

        assert response.status_code == 401


class TestRecommendationsLogging:
    """
    FERPA compliance logging tests.

    All access attempts to recommendations must be logged.
    """

    def test_access_attempt_is_logged(
        self,
        client: TestClient,
        student1_user: User,
        student1_student_record,
        db_session: Session,
        caplog,
    ):
        """
        LOG-1: Access attempts should be logged for audit trail.

        FERPA requires audit trail of who accessed what student data.
        """
        import logging

        logging.getLogger("backend.routes.recommendations").setLevel(logging.INFO)

        token = get_auth_token(student1_user)

        with patch(
            "backend.routes.recommendations.StudentService.get_student_by_id"
        ) as mock_get:
            mock_get.return_value = {
                "id": "student1@test.com",
                "risk_score": 45.0,
                "content_completion_score": 60.0,
            }

            with caplog.at_level(logging.INFO):
                response = client.get(
                    "/api/v1/recommendations/student1@test.com",
                    headers={"Authorization": f"Bearer {token}"},
                )

        # Verify logging occurred
        assert response.status_code == 200
        assert any(
            "Recommendations access" in record.message for record in caplog.records
        )


class TestRecommendationsEdgeCases:
    """
    Edge case tests for recommendations endpoint.
    """

    def test_nonexistent_student_with_faculty_token_succeeds(
        self, client: TestClient, faculty_user: User, db_session: Session
    ):
        """
        EDGE-1: Faculty accessing nonexistent student should handle gracefully.

        Faculty can access any student ID - if student doesn't exist,
        should return 404, not 403.
        """
        token = get_auth_token(faculty_user)

        response = client.get(
            "/api/v1/recommendations/nonexistent@test.com",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Faculty bypasses ownership check, so gets 404 for nonexistent student
        assert response.status_code == 404

    def test_student_with_null_email_fails_gracefully(
        self, client: TestClient, db_session: Session
    ):
        """
        EDGE-2: Malformed tokens should be handled gracefully.
        """
        # Token with malformed payload
        response = client.get(
            "/api/v1/recommendations/student1@test.com",
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIifQ.invalid"
            },
        )

        # Should fail with 401 (invalid token)
        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
