"""
TEST-8: PostgreSQL Foreign Key Constraint Tests

Validates proper FK constraint enforcement using PostgreSQL.
SQLite's FK support is optional and often disabled, so these tests
ensure production-level data integrity with PostgreSQL.

These tests verify:
- Foreign key violations are properly rejected
- ON DELETE CASCADE behaviors
- ON UPDATE CASCADE behaviors
- Referential integrity in production-like environment

Run with: TEST_MODE=postgres pytest -xvs backend/tests/test_fk_constraints.py
"""

import pytest
import os
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

# Skip all tests in this file if not running in PostgreSQL mode
pytestmark = pytest.mark.skipif(
    os.getenv("TEST_MODE") != "postgres",
    reason="PostgreSQL FK constraint tests require TEST_MODE=postgres environment variable",
)

# Import fixtures from conftest_postgres
pytest_plugins = ["backend.tests.conftest_postgres"]


class TestForeignKeyConstraints:
    """
    FK-1: Foreign Key Constraint Validation Tests

    Tests proper enforcement of referential integrity constraints.
    """

    def test_enrollment_student_fk_constraint(self, postgres_session):
        """
        FK-1.1: Enrollment.student_id FK must reference valid Student.

        Attempting to insert enrollment with non-existent student_id
        should raise IntegrityError.
        """
        from backend.database.models.enrollment import Enrollment
        from backend.database.models.course import Course

        # Create a course first (need valid course_id too)
        course = Course(
            id="CS101",
            name="Computer Science 101",
            code="CS101",
            credits=4,
            is_active=True,
        )
        postgres_session.add(course)
        postgres_session.commit()

        # Attempt to create enrollment with non-existent student
        invalid_enrollment = Enrollment(
            student_id="nonexistent_student@test.com",  # Invalid student
            course_id=course.id,
            content_completed=10,
            content_required=20,
        )

        postgres_session.add(invalid_enrollment)

        # Should raise IntegrityError due to FK violation
        with pytest.raises(IntegrityError) as exc_info:
            postgres_session.commit()

        assert (
            "foreign key" in str(exc_info.value).lower()
            or "violation" in str(exc_info.value).lower()
        )

        # Rollback to clean state
        postgres_session.rollback()

    def test_enrollment_course_fk_constraint(self, postgres_session):
        """
        FK-1.2: Enrollment.course_id FK must reference valid Course.

        Attempting to insert enrollment with non-existent course_id
        should raise IntegrityError.
        """
        from backend.database.models.enrollment import Enrollment
        from backend.database.models.student import Student

        # Create a student
        student = Student(
            id="test_student_001",
            org_defined_id="2025EB110001",
            first_name="Test",
            last_name="Student",
            parent_department_name="Computer Science",
            old_new_student="new",
            is_active=True,
        )
        postgres_session.add(student)
        postgres_session.commit()

        # Attempt to create enrollment with non-existent course
        invalid_enrollment = Enrollment(
            student_id=student.id,
            course_id="NONEXISTENT_COURSE",  # Invalid course
            content_completed=10,
            content_required=20,
        )

        postgres_session.add(invalid_enrollment)

        # Should raise IntegrityError due to FK violation
        with pytest.raises(IntegrityError) as exc_info:
            postgres_session.commit()

        assert (
            "foreign key" in str(exc_info.value).lower()
            or "violation" in str(exc_info.value).lower()
        )

        postgres_session.rollback()

    def test_valid_enrollment_with_existing_student_and_course(self, postgres_session):
        """
        FK-1.3: Valid enrollment should succeed when both FKs exist.

        This is the happy path - valid student_id and course_id.
        """
        from backend.database.models.enrollment import Enrollment
        from backend.database.models.student import Student
        from backend.database.models.course import Course

        # Create student and course
        student = Student(
            id="valid_student_001",
            org_defined_id="2025EB110002",
            first_name="Valid",
            last_name="Student",
            parent_department_name="Data Science",
            old_new_student="new",
            is_active=True,
        )
        course = Course(
            id="DS101",
            name="Data Science 101",
            code="DS101",
            credits=4,
            is_active=True,
        )

        postgres_session.add_all([student, course])
        postgres_session.commit()

        # Create valid enrollment
        enrollment = Enrollment(
            student_id=student.id,
            course_id=course.id,
            content_completed=15,
            content_required=20,
        )

        postgres_session.add(enrollment)
        postgres_session.commit()

        # Verify enrollment was created
        result = (
            postgres_session.query(Enrollment)
            .filter(Enrollment.student_id == student.id)
            .first()
        )

        assert result is not None
        assert result.course_id == course.id

    def test_prediction_student_fk_constraint(self, postgres_session):
        """
        FK-1.4: Prediction.student_id FK must reference valid Student.

        Predictions are linked to students via FK constraint.
        """
        from backend.database.models.prediction import Prediction

        # Attempt to create prediction with non-existent student
        invalid_prediction = Prediction(
            student_id="nonexistent@example.com",
            risk_score=50.0,
            risk_level="medium",
            features_version="v1.0",
        )

        postgres_session.add(invalid_prediction)

        # Should raise IntegrityError
        with pytest.raises(IntegrityError):
            postgres_session.commit()

        postgres_session.rollback()

    def test_graded_component_student_fk_constraint(self, postgres_session):
        """
        FK-1.5: GradedComponent.student_id FK must reference valid Student.

        Graded components are linked to students via FK constraint.
        """
        from backend.database.models.academic import GradedComponent

        # Attempt to create graded component with non-existent student
        invalid_component = GradedComponent(
            student_id="nonexistent@example.com",
            course_id="CS101",
            component_type="quiz",
            score=85.0,
            max_score=100.0,
        )

        postgres_session.add(invalid_component)

        # Should raise IntegrityError
        with pytest.raises(IntegrityError):
            postgres_session.commit()

        postgres_session.rollback()

    def test_exam_record_student_fk_constraint(self, postgres_session):
        """
        FK-1.6: ExamRecord.student_id FK must reference valid Student.

        Exam records are linked to students via FK constraint.
        """
        from backend.database.models.academic import ExamRecord

        # Attempt to create exam record with non-existent student
        invalid_record = ExamRecord(
            student_id="nonexistent@example.com",
            course_code="CS101",
            present=True,
            marks_obtained=85.0,
            marks_total=100.0,
        )

        postgres_session.add(invalid_record)

        # Should raise IntegrityError
        with pytest.raises(IntegrityError):
            postgres_session.commit()

        postgres_session.rollback()


class TestCascadeBehaviors:
    """
    FK-2: ON DELETE/UPDATE CASCADE Behavior Tests

    Tests that configured cascade behaviors work correctly.
    """

    def test_prediction_cascade_delete_on_student_delete(self, postgres_session):
        """
        FK-2.1: Deleting student should cascade delete related predictions.

        Predictions have ON DELETE CASCADE on student_id.
        """
        from backend.database.models.prediction import Prediction
        from backend.database.models.student import Student

        # Create student with prediction
        student = Student(
            id="cascade_test_student",
            org_defined_id="2025EB110003",
            first_name="Cascade",
            last_name="Test",
            parent_department_name="Computer Science",
            old_new_student="new",
            is_active=True,
        )
        prediction = Prediction(
            student_id=student.id,
            risk_score=45.0,
            risk_level="medium",
            features_version="v1.0",
        )

        postgres_session.add_all([student, prediction])
        postgres_session.commit()

        # Verify prediction exists
        pred_count_before = (
            postgres_session.query(Prediction)
            .filter(Prediction.student_id == student.id)
            .count()
        )
        assert pred_count_before == 1

        # Delete student - should cascade delete prediction
        postgres_session.delete(student)
        postgres_session.commit()

        # Verify prediction was cascade deleted
        pred_count_after = (
            postgres_session.query(Prediction)
            .filter(Prediction.student_id == student.id)
            .count()
        )
        assert pred_count_after == 0


class TestReferentialIntegrity:
    """
    FK-3: Referential Integrity Constraint Tests

    Tests that ensure data integrity in the database.
    """

    def test_cannot_delete_referenced_course_with_enrollments(self, postgres_session):
        """
        FK-3.1: Cannot delete course that has enrollments.

        Without ON DELETE CASCADE, deletion should fail if FK references exist.
        """
        from backend.database.models.enrollment import Enrollment
        from backend.database.models.student import Student
        from backend.database.models.course import Course

        # Create student, course, and enrollment
        student = Student(
            id="integrity_test_student",
            org_defined_id="2025EB110004",
            first_name="Integrity",
            last_name="Test",
            parent_department_name="Computer Science",
            old_new_student="new",
            is_active=True,
        )
        course = Course(
            id="INTEGRITY101",
            name="Integrity Test Course",
            code="INT101",
            credits=4,
            is_active=True,
        )
        enrollment = Enrollment(
            student_id=student.id,
            course_id=course.id,
            content_completed=10,
            content_required=20,
        )

        postgres_session.add_all([student, course, enrollment])
        postgres_session.commit()

        # Attempt to delete course with existing enrollment
        postgres_session.delete(course)

        # Should raise IntegrityError due to FK reference
        with pytest.raises(IntegrityError):
            postgres_session.commit()

        postgres_session.rollback()

    def test_database_tables_have_expected_fk_constraints(self, postgres_engine):
        """
        FK-3.2: Verify expected tables have FK constraints defined.

        Uses SQLAlchemy inspector to verify schema.
        """
        inspector = inspect(postgres_engine)

        # Tables that should have FK constraints
        expected_fk_tables = [
            "enrollments",
            "predictions",
            "graded_components",
            "exam_records",
            "interventions",
            "goals",
        ]

        for table_name in expected_fk_tables:
            fks = inspector.get_foreign_keys(table_name)
            assert len(fks) > 0, f"Table {table_name} should have FK constraints"


class TestTransactionIsolation:
    """
    FK-4: Transaction Isolation Tests

    Tests proper transaction behavior with FK constraints.
    """

    def test_fk_violation_allows_rollback(self, postgres_session):
        """
        FK-4.1: FK violation should allow transaction rollback.

        After rollback, database should be in consistent state.
        """
        from backend.database.models.enrollment import Enrollment
        from backend.database.models.student import Student

        # Create a valid student
        student = Student(
            id="rollback_test_student",
            org_defined_id="2025EB110005",
            first_name="Rollback",
            last_name="Test",
            parent_department_name="Computer Science",
            old_new_student="new",
            is_active=True,
        )
        postgres_session.add(student)
        postgres_session.commit()

        # Attempt invalid operation
        invalid_enrollment = Enrollment(
            student_id="nonexistent@test.com",
            course_id="CS101",
            content_completed=10,
            content_required=20,
        )
        postgres_session.add(invalid_enrollment)

        try:
            postgres_session.commit()
        except IntegrityError:
            postgres_session.rollback()

        # Verify valid student still exists after rollback
        result = (
            postgres_session.query(Student).filter(Student.id == student.id).first()
        )

        assert result is not None
        assert result.first_name == "Rollback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
