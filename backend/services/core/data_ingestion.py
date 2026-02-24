"""
Data Ingestion Service for EWS Retention Platform.

Parses all 3 XLSX files from data/raw/ and populates the database:
1. Engagement_Analysis.xlsx -> Student, Course, Enrollment
2. B.S and M.Sc Live Summary Data -> LiveSessionAttendance (course-level)
3. Trimester-1 2025 Attendance Quiz-Assignment-Exam -> GradedComponent, ExamRecord
"""

import logging
import openpyxl
from sqlalchemy.orm import Session

from backend.config import (
    ENGAGEMENT_DATA_PATH, QUIZ_EXAM_DATA_PATH,
    WEEK12_ENGAGEMENT_PATH, QUIZ_STATUS_9FEB_PATH,
    GRADED_QUIZ_10FEB_ORIG_PATH, GRADED_QUIZ_10FEB_1115AM_PATH, GRADED_QUIZ_10FEB_451PM_PATH,
    WEEK3_USAGE_PATH, WEEK5_USAGE_PATH,
)
from backend.database import (
    Student, Course, Enrollment,
    GradedComponent, ExamRecord,
)

logger = logging.getLogger(__name__)


def ingest_all_data(db: Session):
    """Master ingestion function. Idempotent — skips if data exists."""
    if db.query(Student).count() > 0:
        logger.info("Data already ingested. Skipping.")
        return

    logger.info("Starting data ingestion from XLSX files...")

    try:
        _ingest_engagement_data(db)
        _ingest_quiz_assignment_exam(db)
        _update_enrollments_from_latest(db)
        db.commit()
        logger.info("Data ingestion complete.")
    except Exception as e:
        db.rollback()
        logger.error(f"Data ingestion failed: {e}")
        raise


def _ingest_engagement_data(db: Session):
    """
    Parse Engagement_Analysis.xlsx:
    - Sheet 'Learner Usage main dump' -> Student, Course, Enrollment
    - Sheet 'Courses' -> Course content counts
    """
    logger.info(f"Reading {ENGAGEMENT_DATA_PATH}...")
    wb = openpyxl.load_workbook(str(ENGAGEMENT_DATA_PATH), read_only=True, data_only=True)

    # --- Parse 'Learner Usage main dump' sheet ---
    ws = wb['Learner Usage main dump']

    students_seen = {}
    courses_seen = {}
    enrollment_count = 0

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            # Header row
            continue

        vals = list(row)
        if len(vals) < 15 or vals[0] is None:
            continue

        course_code = str(vals[0]).strip()
        course_name = str(vals[1]).strip() if vals[1] else ''
        dept_name = str(vals[2]).strip().replace('&amp;', '&') if vals[2] else ''
        dept_code = str(vals[3]).strip() if vals[3] else ''
        semester_code = str(vals[4]).strip() if vals[4] else ''
        semester_name = str(vals[5]).strip() if vals[5] else ''
        username = str(vals[6]).strip() if vals[6] else ''
        org_id = str(vals[7]).strip() if vals[7] else ''
        old_new = str(vals[8]).strip() if vals[8] else ''
        first_name = str(vals[9]).strip() if vals[9] else ''
        last_name = str(vals[10]).strip() if vals[10] else ''
        is_active = bool(vals[11]) if vals[11] is not None else True
        content_completed = _safe_int(vals[12])
        content_required_w1w2 = _safe_int(vals[13])
        content_required = _safe_int(vals[14])

        if not username:
            continue

        # Upsert Student
        if username not in students_seen:
            student = Student(
                id=username,
                org_defined_id=org_id,
                first_name=first_name,
                last_name=last_name if last_name != '.' else '',
                old_new_student=old_new,
                is_active=is_active,
                parent_department_name=dept_name,
                parent_department_code=dept_code,
            )
            db.add(student)
            students_seen[username] = True

        # Upsert Course
        if course_code not in courses_seen:
            course = Course(
                id=course_code,
                name=course_name,
                semester_code=semester_code,
                semester_name=semester_name,
                content_required_w1w2=0,
                content_required_total=0,
            )
            db.add(course)
            courses_seen[course_code] = True

        # Create Enrollment
        enrollment = Enrollment(
            student_id=username,
            course_id=course_code,
            content_completed=content_completed,
            content_required=content_required,
            content_required_w1w2=content_required_w1w2,
        )
        db.add(enrollment)
        enrollment_count += 1

    db.flush()

    # --- Parse 'Courses' sheet for content counts ---
    try:
        ws_courses = wb['Courses']
        for i, row in enumerate(ws_courses.iter_rows(values_only=True)):
            if i == 0:
                continue  # Header

            vals = list(row)
            # T1 courses are in columns 6-10: course_name, week1, week2, lab, sum
            if len(vals) >= 11 and vals[6] is not None:
                cname = str(vals[6]).strip()
                w1 = _safe_int(vals[7])
                w2 = _safe_int(vals[8])
                lab = _safe_int(vals[9]) if vals[9] != '-' else 0
                total = _safe_int(vals[10])

                # Match by name to update course
                course = db.query(Course).filter(Course.name.ilike(f"%{cname}%")).first()
                if course:
                    course.week1_content = w1
                    course.week2_content = w2
                    course.lab_content = lab
                    course.content_required_w1w2 = w1 + w2
                    course.content_required_total = total

            # T2 courses in columns 0-4
            if len(vals) >= 5 and vals[0] is not None:
                cname = str(vals[0]).strip()
                w1 = _safe_int(vals[1])
                w2 = _safe_int(vals[2])
                lab = _safe_int(vals[3]) if vals[3] != '-' else 0
                total = _safe_int(vals[4])

                course = db.query(Course).filter(Course.name.ilike(f"%{cname}%")).first()
                if course:
                    course.week1_content = w1
                    course.week2_content = w2
                    course.lab_content = lab
                    course.content_required_w1w2 = w1 + w2
                    course.content_required_total = total

        db.flush()
    except Exception as e:
        logger.warning(f"Could not parse Courses sheet: {e}")

    wb.close()
    logger.info(f"Engagement data: {len(students_seen)} students, {len(courses_seen)} courses, {enrollment_count} enrollments")


def _ingest_quiz_assignment_exam(db: Session):
    """
    Parse _Trimester-1 2025 Attendance Quiz-Assignment-Exam 5Jan2025.xlsx:
    - Sheets 'BS Attendance', 'MSc Attendance' -> GradedComponent
    - Sheet 'Written Exam Marks' -> ExamRecord
    - Sheets 'Attendance-Slot-1', 'Attendance-Slot-2' -> ExamRecord
    - Sheet 'Exam Defaulter' -> ExamRecord (absent)
    """
    logger.info(f"Reading {QUIZ_EXAM_DATA_PATH}...")
    wb = openpyxl.load_workbook(str(QUIZ_EXAM_DATA_PATH), read_only=True, data_only=True)

    # --- BS Attendance (graded quizzes & assignments) ---
    _ingest_graded_sheet(db, wb, 'BS Attendance', program='BS')

    # --- MSc Attendance (graded quizzes & assignments) ---
    _ingest_graded_sheet(db, wb, 'MSc Attendance', program='MSc')

    # --- Written Exam Marks ---
    _ingest_written_exam_marks(db, wb)

    # --- Exam Attendance Slots ---
    _ingest_exam_attendance(db, wb, 'Attendance-Slot-1', slot='slot-1')
    _ingest_exam_attendance(db, wb, 'Attendance-Slot-2', slot='slot-2')

    # --- Exam Defaulters ---
    _ingest_exam_defaulters(db, wb)

    db.flush()
    wb.close()
    logger.info("Quiz/Assignment/Exam data ingested.")


def _ingest_graded_sheet(db: Session, wb, sheet_name: str, program: str):
    """
    Parse BS/MSc Attendance sheets.

    BS layout (row 2 is header):
        Col 2: BITS ID, Col 3: Email, Col 4: First Name
        Cols 7-10: Quiz 1-4 scores (max in header like '1 (8)')
        Col 11: Assignment 1 score (max in header like '1 (28)')
        Col 14: Subject, Col 15: Subject Code

    MSc layout (row 2 is header):
        Col 2: ID No., Col 3: Email, Col 4: Name
        Cols 7-8: Quiz 1-2, Col 9: Assignment 1, Col 10: Quiz 3
        Col 13: Subject, Col 14: Subject Code
    """
    try:
        ws = wb[sheet_name]
    except KeyError:
        logger.warning(f"Sheet '{sheet_name}' not found, skipping.")
        return

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 4:
        return

    # Row 2 has column headers (0-indexed: row index 2)
    header = list(rows[2])
    # Row 0 has the course name
    course_name = str(rows[0][7]) if rows[0][7] else ''
    # Row 1 has component type info
    subject_info = str(rows[1][12] if len(rows[1]) > 12 and rows[1][12] else '')

    graded_count = 0

    if program == 'BS':
        # Parse max scores from header: '1 (8)' -> max=8
        quiz_max_scores = []
        for col_idx in [7, 8, 9, 10]:
            if col_idx < len(header) and header[col_idx]:
                quiz_max_scores.append(_parse_max_score(str(header[col_idx])))
            else:
                quiz_max_scores.append(8.0)

        assignment_max = _parse_max_score(str(header[11])) if len(header) > 11 and header[11] else 28.0

        for row_idx in range(3, len(rows)):
            vals = list(rows[row_idx])
            if len(vals) < 16 or vals[2] is None:
                continue

            bits_id = str(vals[2]).strip()
            email = str(vals[3]).strip() if vals[3] else ''
            student_name = str(vals[4]).strip() if vals[4] else ''
            subject = str(vals[14]).strip() if len(vals) > 14 and vals[14] else course_name
            subject_code = str(vals[15]).strip() if len(vals) > 15 and vals[15] else ''

            student_id = email if email else f"{bits_id.lower()}@bitspilani-digital.edu.in"

            # Ensure student exists
            _ensure_student(db, student_id, bits_id, student_name, program)

            # Quiz scores (cols 7-10)
            for q_idx, col_idx in enumerate([7, 8, 9, 10]):
                if col_idx < len(vals):
                    score_val = vals[col_idx]
                    is_absent = (score_val == 'A' or score_val is None)
                    score = None if is_absent else _safe_float(score_val)

                    gc = GradedComponent(
                        student_id=student_id,
                        course_code=subject_code,
                        course_name=subject,
                        component_type='quiz',
                        component_number=q_idx + 1,
                        score=score,
                        max_score=quiz_max_scores[q_idx],
                        missed=is_absent,
                    )
                    db.add(gc)
                    graded_count += 1

            # Assignment score (col 11)
            if len(vals) > 11:
                asn_val = vals[11]
                is_absent = (asn_val == 'A' or asn_val is None)
                asn_score = None if is_absent else _safe_float(asn_val)

                gc = GradedComponent(
                    student_id=student_id,
                    course_code=subject_code,
                    course_name=subject,
                    component_type='assignment',
                    component_number=1,
                    score=asn_score,
                    max_score=assignment_max,
                    missed=is_absent,
                )
                db.add(gc)
                graded_count += 1

    elif program == 'MSc':
        # MSc layout: cols 7,8 = Quiz 1,2; col 9 = Assignment 1; col 10 = Quiz 3
        quiz_cols = [7, 8, 10]  # Quiz 1, 2, 3
        assignment_cols = [9]    # Assignment 1

        quiz_max_scores = []
        for col_idx in quiz_cols:
            if col_idx < len(header) and header[col_idx]:
                quiz_max_scores.append(_parse_max_score(str(header[col_idx])))
            else:
                quiz_max_scores.append(15.0)

        asn_max = _parse_max_score(str(header[9])) if len(header) > 9 and header[9] else 20.0

        for row_idx in range(3, len(rows)):
            vals = list(rows[row_idx])
            if len(vals) < 14 or vals[2] is None:
                continue

            bits_id = str(vals[2]).strip()
            email = str(vals[3]).strip() if vals[3] else ''
            student_name = str(vals[4]).strip() if vals[4] else ''
            subject = str(vals[13]).strip() if len(vals) > 13 and vals[13] else course_name
            subject_code = str(vals[14]).strip() if len(vals) > 14 and vals[14] else ''

            student_id = email if email else f"{bits_id.lower()}@bitspilani-digital.edu.in"

            _ensure_student(db, student_id, bits_id, student_name, program)

            # Quiz scores
            for q_idx, col_idx in enumerate(quiz_cols):
                if col_idx < len(vals):
                    score_val = vals[col_idx]
                    is_absent = (score_val == 'A' or score_val is None)
                    score = None if is_absent else _safe_float(score_val)

                    gc = GradedComponent(
                        student_id=student_id,
                        course_code=subject_code,
                        course_name=subject,
                        component_type='quiz',
                        component_number=q_idx + 1,
                        score=score,
                        max_score=quiz_max_scores[q_idx],
                        missed=is_absent,
                    )
                    db.add(gc)
                    graded_count += 1

            # Assignment
            for a_idx, col_idx in enumerate(assignment_cols):
                if col_idx < len(vals):
                    asn_val = vals[col_idx]
                    is_absent = (asn_val == 'A' or asn_val is None)
                    asn_score = None if is_absent else _safe_float(asn_val)

                    gc = GradedComponent(
                        student_id=student_id,
                        course_code=subject_code,
                        course_name=subject,
                        component_type='assignment',
                        component_number=a_idx + 1,
                        score=asn_score,
                        max_score=asn_max,
                        missed=is_absent,
                    )
                    db.add(gc)
                    graded_count += 1

    logger.info(f"  {sheet_name}: {graded_count} graded component records")


def _ingest_written_exam_marks(db: Session, wb):
    """Parse 'Written Exam Marks' sheet -> ExamRecord."""
    try:
        ws = wb['Written Exam Marks']
    except KeyError:
        logger.warning("Sheet 'Written Exam Marks' not found.")
        return

    count = 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # Header

        vals = list(row)
        if len(vals) < 17 or vals[5] is None:
            continue

        email = str(vals[5]).strip()
        course_code = str(vals[3]).strip() if vals[3] else ''
        student_name = str(vals[8]).strip() if vals[8] else ''
        semester_info = str(vals[10]).strip() if vals[10] else ''
        total_marks = _safe_float(vals[15])
        obtained_marks = _safe_float(vals[16])

        # Determine slot from semester info
        slot = 'slot-1' if 'Slot-1' in semester_info else 'slot-2' if 'Slot-2' in semester_info else 'unknown'

        student_id = email
        if not db.query(Student).filter(Student.id == student_id).first():
            # Student might not exist yet if they only appear in exam data
            program = 'MSc' if 'em' in email.lower() else 'BS'
            _ensure_student(db, student_id, '', student_name, program)

        exam = ExamRecord(
            student_id=student_id,
            course_code=course_code,
            course_name='',
            slot=slot,
            marks_obtained=obtained_marks,
            marks_total=total_marks,
            present=True,
            mode=None,
        )
        db.add(exam)
        count += 1

    logger.info(f"  Written Exam Marks: {count} records")


def _ingest_exam_attendance(db: Session, wb, sheet_name: str, slot: str):
    """Parse Attendance-Slot-1 / Attendance-Slot-2 sheets -> ExamRecord."""
    try:
        ws = wb[sheet_name]
    except KeyError:
        logger.warning(f"Sheet '{sheet_name}' not found.")
        return

    count = 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # Header

        vals = list(row)
        if len(vals) < 15 or vals[0] is None:
            continue

        bits_id = str(vals[0]).strip()
        exam_mode = str(vals[1]).strip() if vals[1] else ''
        email = str(vals[2]).strip() if vals[2] else ''
        student_name = str(vals[3]).strip() if vals[3] else ''
        course_code = str(vals[6]).strip() if vals[6] else ''
        course_name = str(vals[7]).strip() if vals[7] else ''
        status = str(vals[14]).strip() if vals[14] else ''
        program = str(vals[19]).strip() if len(vals) > 19 and vals[19] else ''

        student_id = email if email else f"{bits_id.lower()}@bitspilani-digital.edu.in"
        is_present = status.lower() == 'present'

        _ensure_student(db, student_id, bits_id, student_name, program)

        # Check if we already have an exam record with marks for this student+course+slot
        existing = db.query(ExamRecord).filter(
            ExamRecord.student_id == student_id,
            ExamRecord.course_code == course_code,
            ExamRecord.slot == slot,
        ).first()

        if existing:
            # Update with attendance info
            existing.present = is_present
            existing.mode = exam_mode
        else:
            exam = ExamRecord(
                student_id=student_id,
                course_code=course_code,
                course_name=course_name,
                slot=slot,
                marks_obtained=None,
                marks_total=0,
                present=is_present,
                mode=exam_mode,
            )
            db.add(exam)

        count += 1

    logger.info(f"  {sheet_name}: {count} records")


def _ingest_exam_defaulters(db: Session, wb):
    """Parse 'Exam Defaulter' sheet -> mark students as absent."""
    try:
        ws = wb['Exam Defaulter']
    except KeyError:
        logger.warning("Sheet 'Exam Defaulter' not found.")
        return

    count = 0
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue  # Header

        vals = list(row)
        if len(vals) < 5 or vals[0] is None:
            continue

        bits_id = str(vals[0]).strip()
        student_name = str(vals[1]).strip() if vals[1] else ''
        program = str(vals[3]).strip() if vals[3] else ''
        status = str(vals[4]).strip() if vals[4] else ''

        if status.lower() not in ('absent', 'activation pending'):
            continue

        email = f"{bits_id.lower()}@bitspilani-digital.edu.in"
        _ensure_student(db, email, bits_id, student_name, program)

        # Check if a defaulter record already exists
        existing = db.query(ExamRecord).filter(
            ExamRecord.student_id == email,
            ExamRecord.course_code == 'EXAM_DEFAULT',
        ).first()

        if not existing:
            exam = ExamRecord(
                student_id=email,
                course_code='EXAM_DEFAULT',
                course_name='Exam Defaulter',
                slot='all',
                marks_obtained=0,
                marks_total=0,
                present=False,
                mode=None,
            )
            db.add(exam)
            count += 1

    logger.info(f"  Exam Defaulters: {count} records")


def _update_enrollments_from_latest(db: Session):
    """
    Merge engagement data from ALL available snapshot files in chronological order.

    Strategy:
    - Counter fields (content, quizzes, logins, time): always keep the max value seen.
    - Date/string fields: overwrite with the latest non-null value.

    Sources processed (oldest → newest):
    1. Week 1-2 Student Engagement Analysis  (T1 snapshot, weeks 1-2)
    2. Graded Quiz 1 Status 9 Feb            (Feb 9 data dump, course matched by name)
    3. graded quiz 1 10 feb complete         (Feb 10, original export)
    4. graded quiz 1 10 feb 11:15 AM         (Feb 10, 11:15 AM export)
    5. Graded quiz 1 10 feb 4:51 PM          (Feb 10, 4:51 PM export)
    6. Learner usage week 3                  (week 3 snapshot)
    7. Learner usage week 5                  (week 5 snapshot — most recent)
    """
    # Counter fields: always take the highest value seen across all snapshots.
    COUNTER_FIELDS = {
        'content_completed', 'content_required', 'checklist_completed',
        'quiz_completed', 'total_quiz_attempts', 'discussion_posts_created',
        'discussion_post_replies', 'discussion_posts_read',
        'num_assignment_submissions', 'total_time_spent_seconds', 'num_logins',
    }

    # Build course name → course_id map for files that lack a course code column.
    course_name_to_id = {c.name.lower(): c.id for c in db.query(Course).all()}

    # Each source entry:
    #   path         – Path object
    #   sheet        – sheet name to read
    #   course_col   – column index of course_code (None if not available)
    #   cname_col    – column index of course_name (used only when course_col is None)
    #   user_col     – column index of username/email
    #   min_cols     – minimum row length to skip malformed rows
    #   fields       – {enrollment_attr: column_index} for every metric
    sources = [
        {
            'label':     'Week 1-2 T1 engagement',
            'path':      WEEK12_ENGAGEMENT_PATH,
            'sheet':     'Learner Usage main dump',
            'course_col': 0, 'user_col': 6, 'min_cols': 30,
            'fields': {
                'content_completed': 12, 'content_required': 14,
                'checklist_completed': 16, 'quiz_completed': 18, 'total_quiz_attempts': 19,
                'discussion_posts_created': 20, 'discussion_post_replies': 21,
                'discussion_posts_read': 22, 'last_discussion_post_date': 23,
                'num_assignment_submissions': 24, 'last_assignment_submission_date': 25,
                'total_time_spent_seconds': 26, 'last_visited_date': 27,
                'last_system_login': 28, 'num_logins': 29,
                'last_quiz_attempt_date': 31, 'last_scorm_completion_date': 32,
                'last_scorm_visit_date': 33,
            },
        },
        {
            'label':      'Graded Quiz Status 9 Feb (data dump)',
            'path':       QUIZ_STATUS_9FEB_PATH,
            'sheet':      'Data Dump - Learner Usage',
            'course_col': None, 'cname_col': 0, 'user_col': 3, 'min_cols': 22,
            'fields': {
                'content_completed': 7, 'content_required': 8,
                'checklist_completed': 9, 'quiz_completed': 10, 'total_quiz_attempts': 11,
                'discussion_posts_created': 12, 'discussion_post_replies': 13,
                'discussion_posts_read': 14, 'last_discussion_post_date': 15,
                'num_assignment_submissions': 16, 'last_assignment_submission_date': 17,
                'total_time_spent_seconds': 18, 'last_visited_date': 19,
                'last_system_login': 20, 'num_logins': 21,
                'last_quiz_attempt_date': 23, 'last_scorm_completion_date': 24,
            },
        },
        {
            'label':     'Graded Quiz (Feb 10, original complete)',
            'path':      GRADED_QUIZ_10FEB_ORIG_PATH,
            'sheet':     'Learner Usage-02-11-2026T10-14-',
            'course_col': 1, 'user_col': 7, 'min_cols': 29,
            'fields': {
                'content_completed': 14, 'content_required': 15,
                'checklist_completed': 16, 'quiz_completed': 17, 'total_quiz_attempts': 18,
                'discussion_posts_created': 19, 'discussion_post_replies': 20,
                'discussion_posts_read': 21, 'last_discussion_post_date': 22,
                'num_assignment_submissions': 23, 'last_assignment_submission_date': 24,
                'total_time_spent_seconds': 25, 'last_visited_date': 26,
                'last_system_login': 27, 'num_logins': 28,
                'last_quiz_attempt_date': 30, 'last_scorm_completion_date': 31,
                'last_scorm_visit_date': 32,
            },
        },
        {
            'label':     'Graded Quiz (Feb 10, 11:15 AM)',
            'path':      GRADED_QUIZ_10FEB_1115AM_PATH,
            'sheet':     'Learner Usage-02-10-2026T11-12-',
            'course_col': 1, 'user_col': 9, 'min_cols': 31,
            'fields': {
                'content_completed': 16, 'content_required': 17,
                'checklist_completed': 18, 'quiz_completed': 19, 'total_quiz_attempts': 20,
                'discussion_posts_created': 21, 'discussion_post_replies': 22,
                'discussion_posts_read': 23, 'last_discussion_post_date': 24,
                'num_assignment_submissions': 25, 'last_assignment_submission_date': 26,
                'total_time_spent_seconds': 27, 'last_visited_date': 28,
                'last_system_login': 29, 'num_logins': 30,
                'last_quiz_attempt_date': 32, 'last_scorm_completion_date': 33,
                'last_scorm_visit_date': 34,
            },
        },
        {
            'label':     'Graded Quiz (Feb 10, 4:51 PM)',
            'path':      GRADED_QUIZ_10FEB_451PM_PATH,
            'sheet':     'Learner Usage',
            'course_col': 1, 'user_col': 8, 'min_cols': 26,
            'fields': {
                'content_completed': 11, 'content_required': 12,
                'checklist_completed': 13, 'quiz_completed': 14, 'total_quiz_attempts': 15,
                'discussion_posts_created': 16, 'discussion_post_replies': 17,
                'discussion_posts_read': 18, 'last_discussion_post_date': 19,
                'num_assignment_submissions': 20, 'last_assignment_submission_date': 21,
                'total_time_spent_seconds': 22, 'last_visited_date': 23,
                'last_system_login': 24, 'num_logins': 25,
                'last_quiz_attempt_date': 27, 'last_scorm_completion_date': 28,
                'last_scorm_visit_date': 29,
            },
        },
        {
            'label':     'Learner usage week 3',
            'path':      WEEK3_USAGE_PATH,
            'sheet':     'Learner Usage',
            'course_col': 0, 'user_col': 4, 'min_cols': 32,
            'fields': {
                'content_completed': 10,
                'checklist_completed': 19, 'quiz_completed': 20, 'total_quiz_attempts': 21,
                'discussion_posts_created': 22, 'discussion_post_replies': 23,
                'discussion_posts_read': 24, 'last_discussion_post_date': 25,
                'num_assignment_submissions': 26, 'last_assignment_submission_date': 27,
                'total_time_spent_seconds': 28, 'last_visited_date': 29,
                'last_system_login': 30, 'num_logins': 31,
                'last_quiz_attempt_date': 33, 'last_scorm_completion_date': 34,
                'last_scorm_visit_date': 35,
            },
        },
        {
            'label':     'Learner usage week 5',
            'path':      WEEK5_USAGE_PATH,
            'sheet':     'Main Dump',
            'course_col': 1, 'user_col': 9, 'min_cols': 31,
            'fields': {
                'content_completed': 16, 'content_required': 17,
                'checklist_completed': 18, 'quiz_completed': 19, 'total_quiz_attempts': 20,
                'discussion_posts_created': 21, 'discussion_post_replies': 22,
                'discussion_posts_read': 23, 'last_discussion_post_date': 24,
                'num_assignment_submissions': 25, 'last_assignment_submission_date': 26,
                'total_time_spent_seconds': 27, 'last_visited_date': 28,
                'last_system_login': 29, 'num_logins': 30,
                'last_quiz_attempt_date': 32, 'last_scorm_completion_date': 33,
                'last_scorm_visit_date': 34,
            },
        },
    ]

    for src in sources:
        path = src['path']
        if not path.exists():
            logger.warning(f"Skipping (not found): {path.name}")
            continue

        logger.info(f"Merging [{src['label']}] from {path.name}...")
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        try:
            ws = wb[src['sheet']]
        except KeyError:
            logger.warning(f"  Sheet '{src['sheet']}' not found in {path.name}")
            wb.close()
            continue

        updated = 0
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue  # header row
            vals = list(row)
            if len(vals) < src['min_cols'] or vals[src['user_col']] is None:
                continue

            username = str(vals[src['user_col']]).strip()
            if not username:
                continue

            # Resolve course_id — either directly from a code column or via name lookup
            if src.get('course_col') is not None:
                course_id = str(vals[src['course_col']]).strip() if vals[src['course_col']] else ''
            else:
                cname_raw = vals[src.get('cname_col', 0)]
                course_name = str(cname_raw).strip().lower() if cname_raw else ''
                course_id = course_name_to_id.get(course_name, '')

            if not course_id:
                continue

            enrollment = db.query(Enrollment).filter(
                Enrollment.student_id == username,
                Enrollment.course_id == course_id,
            ).first()

            if not enrollment:
                continue

            # Merge each field
            for field, col in src['fields'].items():
                if col >= len(vals) or vals[col] is None:
                    continue
                raw = vals[col]
                if field in COUNTER_FIELDS:
                    new_val = _safe_int(raw)
                    if new_val > (getattr(enrollment, field) or 0):
                        setattr(enrollment, field, new_val)
                else:
                    # Date / string — most recent non-null value wins
                    setattr(enrollment, field, str(raw))

            updated += 1

        db.flush()
        logger.info(f"  -> {updated} enrollments updated.")
        wb.close()


# ---- Helpers ----

def _ensure_student(db: Session, student_id: str, org_id: str, name: str, program: str):
    """Create student if not exists."""
    existing = db.query(Student).filter(Student.id == student_id).first()
    if existing:
        return

    # Split name into first/last
    parts = name.strip().split(None, 1) if name else ['', '']
    first_name = parts[0] if parts else ''
    last_name = parts[1] if len(parts) > 1 else ''

    # Determine department from program
    if 'msc' in program.lower() or 'ms' in program.lower():
        dept_name = 'MSc - Data Science & AI'
        dept_code = 'dept_msc_dsai'
    else:
        dept_name = 'BS - Data Science & AI'
        dept_code = 'dept_bs_dsai'

    student = Student(
        id=student_id,
        org_defined_id=org_id,
        first_name=first_name,
        last_name=last_name,
        old_new_student='new',
        is_active=True,
        parent_department_name=dept_name,
        parent_department_code=dept_code,
    )
    db.add(student)
    db.flush()


def _safe_int(val):
    """Convert value to int, returning 0 for non-numeric."""
    if val is None:
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _safe_float(val):
    """Convert value to float, returning 0.0 for non-numeric."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _parse_max_score(header_text: str) -> float:
    """Parse max score from header like '1 (8)' -> 8.0."""
    try:
        if '(' in header_text and ')' in header_text:
            inside = header_text.split('(')[1].split(')')[0]
            return float(inside)
    except (ValueError, IndexError):
        pass
    return 10.0  # Default
