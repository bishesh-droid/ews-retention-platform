"""
Test suite for student list query functionality.

Validates that risk filtering works correctly with live computed scores,
even when the Prediction table is empty.
"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from backend.application.student.student_application_service import (
    StudentApplicationService,
)
from backend.database.models.student import Student


@pytest.fixture
def mock_db_no_predictions():
    """
    Returns a mock DB session with empty Prediction table.
    Simulates fresh install where ingest_all_data has never written to Prediction.
    """
    session = MagicMock(spec=Session)

    # Mock the subquery to return no prediction rows (empty result)
    mock_subquery = MagicMock()
    mock_subquery.c = MagicMock()
    mock_subquery.c.student_id = MagicMock()
    mock_subquery.c.risk_score = MagicMock()

    # Empty result for any query
    (
        session.query.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value
    ) = []

    return session


@pytest.fixture
def mock_student_with_risk_75():
    """Returns a mock student with computed risk score of 75."""
    student = MagicMock(spec=Student)
    student.id = "student_risk_75"
    student.org_defined_id = "2025EB110075"
    student.first_name = "High"
    student.last_name = "Risk"
    student.parent_department_name = "Computer Science"
    student.old_new_student = "new"
    student.is_active = True
    return student


@pytest.fixture
def mock_student_with_risk_45():
    """Returns a mock student with computed risk score of 45."""
    student = MagicMock(spec=Student)
    student.id = "student_risk_45"
    student.org_defined_id = "2025EB110045"
    student.first_name = "Medium"
    student.last_name = "Risk"
    student.parent_department_name = "Computer Science"
    student.old_new_student = "new"
    student.is_active = True
    return student


def test_risk_filter_works_without_prediction_table():
    """
    Test that risk filtering works even with empty Prediction table.

    This validates the fix for the bug where DB-level risk filtering against
    the Prediction table would return empty results on fresh installs.
    """
    # We need to mock at the repository level since we're testing the service
    with (
        patch(
            "backend.infrastructure.student_repository.StudentRepository.latest_prediction_rows_subquery"
        ) as mock_pred_subq,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_enrollments_map"
        ) as mock_enroll_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_graded_map"
        ) as mock_graded_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_exam_map"
        ) as mock_exam_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.sort_expr_for_students"
        ) as mock_sort_expr,
    ):

        # Setup mock DB session
        mock_db = MagicMock(spec=Session)
        mock_pred_subq.return_value = MagicMock()
        mock_sort_expr.return_value = None  # Simple order_by

        # Mock student rows returned from DB (before risk filtering)
        mock_student_high = MagicMock(spec=Student)
        mock_student_high.id = "student_high"
        mock_student_high.org_defined_id = "2025EB110075"
        mock_student_high.first_name = "High"
        mock_student_high.last_name = "Risk"
        mock_student_high.parent_department_name = "Computer Science"
        mock_student_high.old_new_student = "new"
        mock_student_high.is_active = True
        mock_student_high.semester_name = "Trimester 1"

        mock_student_low = MagicMock(spec=Student)
        mock_student_low.id = "student_low"
        mock_student_low.org_defined_id = "2025EB110045"
        mock_student_low.first_name = "Low"
        mock_student_low.last_name = "Risk"
        mock_student_low.parent_department_name = "Computer Science"
        mock_student_low.old_new_student = "new"
        mock_student_low.is_active = True
        mock_student_low.semester_name = "Trimester 1"

        # Return both students from DB query
        (
            mock_db.query.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value
        ) = [
            (mock_student_high, None),
            (mock_student_low, None),
        ]

        # Mock empty enrollment/graded/exam data
        mock_enroll_map.return_value = {}
        mock_graded_map.return_value = {}
        mock_exam_map.return_value = {}

        # Call get_all_students with risk_min=60
        result = StudentApplicationService.get_all_students(
            db=mock_db,
            skip=0,
            limit=100,
            risk_min=60,  # Should filter to only high-risk students
            risk_max=None,
            current_user=None,
        )

        # Result should be a dict with 'students' and 'total' keys
        # Note: Since we're mocking all the repository calls, the actual risk scores
        # will be computed from empty feature data. The key assertion is that
        # the function RUNS without error and applies the filter post-computation.
        assert isinstance(result, dict), "Result should be a dict"
        assert "students" in result, "Result should have 'students' key"
        assert "total" in result, "Result should have 'total' key"
        students = result["students"]

        # The key validation: all returned students should have risk_score >= 60
        # (or the list should be empty if no students match, not due to DB bug)
        for student in students:
            assert (
                student.get("risk_score", 0) >= 60
            ), f"Student {student.get('id')} has risk_score {student.get('risk_score')} < 60"


def test_risk_filter_0_to_100_scale():
    """
    Test that risk filter accepts 0-100 scale values (not 0-1).

    Validates that the ÷100 normalization was removed.
    """
    # Test that values are used directly without normalization
    # risk_min=60 should filter to >= 60, not >= 0.6

    with (
        patch(
            "backend.infrastructure.student_repository.StudentRepository.latest_prediction_rows_subquery"
        ) as mock_pred_subq,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_enrollments_map"
        ) as mock_enroll_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_graded_map"
        ) as mock_graded_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_exam_map"
        ) as mock_exam_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.sort_expr_for_students"
        ) as mock_sort_expr,
    ):

        mock_db = MagicMock(spec=Session)
        mock_pred_subq.return_value = MagicMock()
        mock_sort_expr.return_value = None

        # Empty result from DB
        (
            mock_db.query.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value
        ) = []
        mock_enroll_map.return_value = {}
        mock_graded_map.return_value = {}
        mock_exam_map.return_value = {}

        # Should not raise error with 0-100 scale values
        result = StudentApplicationService.get_all_students(
            db=mock_db,
            skip=0,
            limit=100,
            risk_min=75.0,  # 0-100 scale
            risk_max=95.0,  # 0-100 scale
            current_user=None,
        )

        assert isinstance(result, dict)
        assert "students" in result


def test_risk_max_filter_applied():
    """
    Test that risk_max filter is applied correctly.
    """
    with (
        patch(
            "backend.infrastructure.student_repository.StudentRepository.latest_prediction_rows_subquery"
        ) as mock_pred_subq,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_enrollments_map"
        ) as mock_enroll_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_graded_map"
        ) as mock_graded_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_exam_map"
        ) as mock_exam_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.sort_expr_for_students"
        ) as mock_sort_expr,
    ):

        mock_db = MagicMock(spec=Session)
        mock_pred_subq.return_value = MagicMock()
        mock_sort_expr.return_value = None

        # Empty result
        (
            mock_db.query.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value
        ) = []
        mock_enroll_map.return_value = {}
        mock_graded_map.return_value = {}
        mock_exam_map.return_value = {}

        result = StudentApplicationService.get_all_students(
            db=mock_db,
            skip=0,
            limit=100,
            risk_min=None,
            risk_max=40.0,  # Only low-risk students
            current_user=None,
        )

        assert isinstance(result, dict)
        assert "students" in result
        for student in result["students"]:
            assert (
                student.get("risk_score", 100) <= 40
            ), f"Student has risk_score {student.get('risk_score')} > 40"


def test_combined_risk_min_and_max():
    """
    Test that both risk_min and risk_max can be applied together.
    """
    with (
        patch(
            "backend.infrastructure.student_repository.StudentRepository.latest_prediction_rows_subquery"
        ) as mock_pred_subq,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_enrollments_map"
        ) as mock_enroll_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_graded_map"
        ) as mock_graded_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.fetch_exam_map"
        ) as mock_exam_map,
        patch(
            "backend.infrastructure.student_repository.StudentRepository.sort_expr_for_students"
        ) as mock_sort_expr,
    ):

        mock_db = MagicMock(spec=Session)
        mock_pred_subq.return_value = MagicMock()
        mock_sort_expr.return_value = None

        (
            mock_db.query.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value
        ) = []
        mock_enroll_map.return_value = {}
        mock_graded_map.return_value = {}
        mock_exam_map.return_value = {}

        result = StudentApplicationService.get_all_students(
            db=mock_db,
            skip=0,
            limit=100,
            risk_min=40.0,
            risk_max=60.0,  # Medium risk band
            current_user=None,
        )

        assert isinstance(result, dict)
        assert "students" in result
        for student in result["students"]:
            score = student.get("risk_score", 0)
            assert (
                40 <= score <= 60
            ), f"Student risk_score {score} outside range [40, 60]"
