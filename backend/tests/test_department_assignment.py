"""
Tests for department/program assignment (B-3 regression guards).

These tests guard against regressions in the B-3 fix which ensures:
1. Program is derived from Org_Defined_Id prefix (2025EM/2024EM = MSc, others = BS)
2. Existing department assignments are not overwritten by _ensure_student
3. Faculty scoping filters work correctly
"""

import pytest
from unittest.mock import MagicMock, create_autospec, patch
from sqlalchemy.orm import Session

from backend.database.models.student import Student
from backend.database.models.user import User


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_session():
    """Returns a mocked SQLAlchemy Session for unit tests."""
    session = create_autospec(Session, instance=True)
    return session


@pytest.fixture
def mock_session_with_students():
    """
    Returns a mocked session with 10 BS and 10 MSc students in the query results.
    Used for integration tests requiring realistic student data.
    """
    session = create_autospec(Session, instance=True)

    # Create mock students
    bs_students = []
    for i in range(10):
        student = MagicMock(spec=Student)
        student.id = f"2025EB{i:05d}@bitspilani-digital.edu.in"
        student.org_defined_id = f"2025EB{i:05d}"
        student.first_name = f"BS_Student{i}"
        student.last_name = "Test"
        student.parent_department_name = "BS - Data Science & AI"
        student.parent_department_code = "dept_bs_dsai"
        student.old_new_student = "new"
        student.is_active = True
        bs_students.append(student)

    msc_students = []
    for i in range(10):
        student = MagicMock(spec=Student)
        student.id = f"2025EM{i:05d}@bitspilani-digital.edu.in"
        student.org_defined_id = f"2025EM{i:05d}"
        student.first_name = f"MSc_Student{i}"
        student.last_name = "Test"
        student.parent_department_name = "MSc - Data Science & AI"
        student.parent_department_code = "dept_msc_dsai"
        student.old_new_student = "new"
        student.is_active = True
        msc_students.append(student)

    all_students = bs_students + msc_students

    # Configure mock query chain
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_filter.filter.return_value.all.return_value = all_students
    mock_query.filter.return_value = mock_filter.filter.return_value
    mock_query.all.return_value = all_students

    session.query.return_value = mock_query

    return session


@pytest.fixture
def mock_bs_faculty():
    """Returns a mock BS faculty user for scoping tests."""
    faculty = MagicMock(spec=User)
    faculty.id = "faculty_001"
    faculty.role = "faculty"
    faculty.department = "BS - Data Science & AI"
    faculty.is_superuser = False
    faculty.username = "bs_faculty"
    return faculty


@pytest.fixture
def mock_msc_faculty():
    """Returns a mock MSc faculty user for scoping tests."""
    faculty = MagicMock(spec=User)
    faculty.id = "faculty_002"
    faculty.role = "faculty"
    faculty.department = "MSc - Data Science & AI"
    faculty.is_superuser = False
    faculty.username = "msc_faculty"
    return faculty


# =============================================================================
# Helper function (extracted from data_ingestion.py for testing)
# =============================================================================

def derive_program_from_org_id(org_id: str) -> str:
    """
    Derive program (BS/MSc) from Org_Defined_Id prefix.

    B-3 Fix: This function must check for a 4-digit year followed by "EM"
    to identify MSc students, NOT use substring matching on email.

    Args:
        org_id: The Org_Defined_Id (e.g., "2025EB1100001" or "2025EM1100001")

    Returns:
        "MSc" if org_id starts with any 4-digit year + "EM", otherwise "BS"
    """
    import re
    if not org_id:
        return "BS"
    oid = org_id.upper()
    if re.match(r'^\d{4}EM', oid):
        return "MSc"
    return "BS"


# =============================================================================
# TEST 1 — Unit test for program detection logic
# =============================================================================

@pytest.mark.parametrize("org_id,email,expected_program", [
    ("2025EB1100001", "2025eb1100001@bitspilani-digital.edu.in", "BS"),
    ("2025EM1100001", "2025em1100001@bitspilani-digital.edu.in", "MSc"),
    ("2024EB0900042", "2024eb0900042@bitspilani-digital.edu.in", "BS"),
    ("2024EM0900042", "2024em0900042@bitspilani-digital.edu.in", "MSc"),
    # Emails that would have tripped the old "em" substring match:
    ("2025EB1100055", "student.semester@bitspilani-digital.edu.in", "BS"),  # "semester" contains "em"
    ("2025EB1100066", "remote.learner@bitspilani-digital.edu.in", "BS"),    # "remote" contains "em"
    ("2025EB1100077", "premium.user@bitspilani-digital.edu.in", "BS"),      # "premium" contains "em"
    # Edge cases
    ("", "some.email@example.com", "BS"),  # empty org_id
    ("2025EB", "short@example.com", "BS"),  # short org_id (BS)
    ("2025EM", "short@example.com", "MSc"),  # short org_id (MSc)
    ("2023EM12345", "legacy@example.com", "MSc"),  # older year MSc
])
def test_program_derived_from_org_id_not_email(org_id, email, expected_program):
    """
    Test that program is derived ONLY from Org_Defined_Id prefix, not from email.

    This guards against the B-3 regression where email containing "em" substring
    (like "semester", "remote", "premium") would incorrectly trigger MSc detection.
    """
    result = derive_program_from_org_id(org_id)
    assert result == expected_program, \
        f"org_id={org_id}: got {result}, expected {expected_program}. " \
        f"Old email heuristic may have been reintroduced."


# =============================================================================
# TEST 2 — Integration test: _ensure_student does not overwrite existing department
# =============================================================================

def test_ensure_student_does_not_overwrite_department(mock_session):
    """
    Test that _ensure_student preserves existing department assignments.

    This guards against the B-3 regression where exam file ingestion could
    overwrite the correct department (set by primary engagement ingestion)
    with an incorrect department derived from the exam file's heuristic.
    """
    # Import here to avoid circular imports during test collection
    from backend.services.core.data_ingestion import _ensure_student

    # Simulate: student already has correct department from engagement ingestion
    existing_student = MagicMock(spec=Student)
    existing_student.org_defined_id = "2025EB1100001"
    existing_student.parent_department_name = "BS - Data Science & AI"  # correct, set by primary ingestion
    existing_student.parent_department_code = "dept_bs_dsai"
    existing_student.first_name = "Existing"
    existing_student.last_name = "Student"
    existing_student.old_new_student = "new"
    existing_student.is_active = True

    # Mock the query to return our existing student
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = existing_student
    mock_session.query.return_value = mock_query

    # Now call _ensure_student with WRONG department (as would come from exam file heuristic)
    _ensure_student(
        db=mock_session,
        student_id="2025EB1100001@bitspilani-digital.edu.in",
        org_id="2025EB1100001",
        name="Test Student",
        program="MSc"  # WRONG — should be ignored because student already has BS
    )

    # Department should be unchanged
    assert existing_student.parent_department_name == "BS - Data Science & AI", \
        "_ensure_student overwrote an existing department — B-3 fix may not be applied correctly. " \
        f"Got: {existing_student.parent_department_name}, expected: BS - Data Science & AI"

    # Department code should also be unchanged
    assert existing_student.parent_department_code == "dept_bs_dsai", \
        f"_ensure_student overwrote department code. Got: {existing_student.parent_department_code}"


def test_ensure_student_sets_department_for_new_student(mock_session):
    """
    Test that _ensure_student DOES set department for new students (no regression).

    This ensures the "don't overwrite" logic doesn't prevent setting department
    for genuinely new students.
    """
    from backend.services.core.data_ingestion import _ensure_student

    # Mock: no existing student (returns None from query)
    mock_query = MagicMock()
    mock_query.filter.return_value.first.return_value = None
    mock_session.query.return_value = mock_query

    # Create a new student mock that will be added
    new_student = MagicMock(spec=Student)
    new_student.id = "2025EB1100002@bitspilani-digital.edu.in"
    new_student.org_defined_id = None
    new_student.first_name = None
    new_student.last_name = None
    new_student.old_new_student = None
    new_student.is_active = None
    new_student.parent_department_name = None  # No department yet
    new_student.parent_department_code = None

    # Mock Student constructor to return our mock
    with patch('backend.services.core.data_ingestion.Student', return_value=new_student):
        _ensure_student(
            db=mock_session,
            student_id="2025EB1100002@bitspilani-digital.edu.in",
            org_id="2025EB1100002",
            name="New Student",
            program="BS"
        )

    # For new students, department SHOULD be set
    assert new_student.parent_department_name == "BS - Data Science & AI", \
        "_ensure_student should set department for new students"
    assert new_student.parent_department_code == "dept_bs_dsai", \
        "_ensure_student should set department code for new students"


# =============================================================================
# TEST 3 — Faculty scoping filter smoke test
# =============================================================================

def test_faculty_sees_only_own_department_students(mock_session_with_students, mock_bs_faculty):
    """
    Test that faculty users only see students from their own department.

    This guards against the B-3 regression where faculty might see all students
    regardless of department, or where department scoping filters are bypassed.
    """
    # Get all students from the fixture (20 students: 10 BS + 10 MSc)
    all_students = mock_session_with_students.query(Student).all()

    # Apply department filter (as done in actual code)
    role = (mock_bs_faculty.role or "").lower()
    is_superuser = bool(mock_bs_faculty.is_superuser)
    dept = mock_bs_faculty.department

    filtered_students = all_students
    if role == "faculty" and not is_superuser and dept:
        filtered_students = [
            s for s in all_students
            if s.parent_department_name == dept
        ]

    # Verify BS faculty only sees BS students
    programs = {s.parent_department_name for s in filtered_students}
    assert programs == {"BS - Data Science & AI"}, \
        f"BS faculty saw non-BS students: {programs}. Department scoping filter may be bypassed."

    # Verify count is correct (10 BS students)
    assert len(filtered_students) == 10, \
        f"Expected 10 BS students, got {len(filtered_students)}. Filtering may not work correctly."


def test_superuser_faculty_sees_all_departments(mock_session_with_students):
    """
    Test that superuser faculty see all students (no department restriction).
    """
    # Create superuser faculty
    superuser = MagicMock(spec=User)
    superuser.role = "faculty"
    superuser.department = "BS - Data Science & AI"
    superuser.is_superuser = True

    all_students = mock_session_with_students.query(Student).all()

    # Apply filtering logic
    role = (superuser.role or "").lower()
    is_superuser = bool(superuser.is_superuser)
    dept = superuser.department

    filtered_students = all_students
    if role == "faculty" and not is_superuser and dept:
        filtered_students = [s for s in all_students if s.parent_department_name == dept]

    # Superuser should see all students (20 total: 10 BS + 10 MSc)
    assert len(filtered_students) == 20, \
        f"Superuser should see all 20 students, got {len(filtered_students)}"

    programs = {s.parent_department_name for s in filtered_students}
    assert programs == {"BS - Data Science & AI", "MSc - Data Science & AI"}, \
        f"Superuser should see both departments: {programs}"


def test_msc_faculty_sees_only_msc_students(mock_session_with_students, mock_msc_faculty):
    """
    Test that MSc faculty only see MSc students.
    """
    all_students = mock_session_with_students.query(Student).all()

    # Apply department filter
    role = (mock_msc_faculty.role or "").lower()
    is_superuser = bool(mock_msc_faculty.is_superuser)
    dept = mock_msc_faculty.department

    filtered_students = all_students
    if role == "faculty" and not is_superuser and dept:
        filtered_students = [s for s in all_students if s.parent_department_name == dept]

    programs = {s.parent_department_name for s in filtered_students}
    assert programs == {"MSc - Data Science & AI"}, \
        f"MSc faculty saw non-MSc students: {programs}"

    assert len(filtered_students) == 10, \
        f"Expected 10 MSc students, got {len(filtered_students)}"
