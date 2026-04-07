"""Idempotent, validated ETL ingestion for EWS retention data."""

import logging
import threading
from pathlib import Path

import openpyxl
from sqlalchemy.orm import Session

from backend.config import (
    ENGAGEMENT_DATA_PATH,
    GRADED_QUIZ_10FEB_1115AM_PATH,
    GRADED_QUIZ_10FEB_451PM_PATH,
    GRADED_QUIZ_10FEB_ORIG_PATH,
    QUIZ_EXAM_DATA_PATH,
    QUIZ_STATUS_9FEB_PATH,
    WEEK12_ENGAGEMENT_PATH,
    WEEK3_USAGE_PATH,
    WEEK5_USAGE_PATH,
)
from backend.database import Course, Enrollment, ExamRecord, GradedComponent, Student

logger = logging.getLogger(__name__)

COUNTER_FIELDS = {
    "content_completed",
    "content_required",
    "checklist_completed",
    "quiz_completed",
    "total_quiz_attempts",
    "discussion_posts_created",
    "discussion_post_replies",
    "discussion_posts_read",
    "num_assignment_submissions",
    "total_time_spent_seconds",
    "num_logins",
}


def ingest_all_data(db: Session):
    """
    Run ETL in a single transaction-safe flow.

    Idempotency:
    - Inserts use update-or-create semantics.
    - Running multiple times refreshes data instead of duplicating rows.
    """
    owner_thread_id = threading.get_ident()
    _assert_session_thread(owner_thread_id)

    files = _build_file_map()
    _validate_required_files(files)

    logger.info("Starting data ingestion from XLSX files...")
    try:
        _ingest_engagement_data(db, files, owner_thread_id)
        _ingest_quiz_assignment_exam(db, files, owner_thread_id)
        _update_enrollments_from_latest(db, files, owner_thread_id)
        db.flush()
        logger.info("Data ingestion complete.")
    except Exception:
        db.rollback()
        logger.exception("Data ingestion failed.")
        raise


def _build_file_map() -> dict:
    """Centralized input paths (no hardcoded paths in ETL logic)."""
    return {
        "engagement": ENGAGEMENT_DATA_PATH,
        "quiz_exam": QUIZ_EXAM_DATA_PATH,
        "week12": WEEK12_ENGAGEMENT_PATH,
        "quiz_9feb": QUIZ_STATUS_9FEB_PATH,
        "quiz_10feb_orig": GRADED_QUIZ_10FEB_ORIG_PATH,
        "quiz_10feb_1115": GRADED_QUIZ_10FEB_1115AM_PATH,
        "quiz_10feb_451": GRADED_QUIZ_10FEB_451PM_PATH,
        "week3": WEEK3_USAGE_PATH,
        "week5": WEEK5_USAGE_PATH,
    }


def _validate_required_files(files: dict):
    """Fail fast if core ETL sources are missing."""
    required = ("engagement",)
    missing = [str(files[key]) for key in required if not Path(files[key]).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required ETL input file(s): {', '.join(missing)}")


def _ingest_engagement_data(db: Session, files: dict, owner_thread_id: int):
    _assert_session_thread(owner_thread_id)
    path = Path(files["engagement"])
    logger.info(f"Reading {path}...")

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    try:
        ws = wb["Learner Usage main dump"]
        existing_students = {s.id: s for s in db.query(Student).all()}
        existing_courses = {c.id: c for c in db.query(Course).all()}
        enrollments = {
            (e.student_id, e.course_id): e for e in db.query(Enrollment).all()
        }

        valid_rows = 0
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue
            vals = list(row)
            if len(vals) < 15:
                continue

            course_code = _safe_str(vals[0])
            username = _safe_str(vals[6])
            if not course_code or not username:
                continue
            valid_rows += 1

            course_name = _safe_str(vals[1])
            dept_name = _safe_str(vals[2]).replace("&amp;", "&")
            dept_code = _safe_str(vals[3])
            semester_code = _safe_str(vals[4])
            semester_name = _safe_str(vals[5])
            org_id = _safe_str(vals[7])
            old_new = _safe_str(vals[8]) or "new"
            first_name = _safe_str(vals[9])
            last_name = _safe_str(vals[10])
            is_active = bool(vals[11]) if vals[11] is not None else True

            student = existing_students.get(username)
            if not student:
                student = Student(id=username)
                db.add(student)
                existing_students[username] = student
            student.org_defined_id = org_id
            student.first_name = first_name
            student.last_name = "" if last_name == "." else last_name
            student.old_new_student = old_new
            student.is_active = is_active
            student.parent_department_name = dept_name
            student.parent_department_code = dept_code

            course = existing_courses.get(course_code)
            if not course:
                course = Course(id=course_code)
                db.add(course)
                existing_courses[course_code] = course
            course.name = course_name
            course.semester_code = semester_code
            course.semester_name = semester_name
            course.content_required_w1w2 = course.content_required_w1w2 or 0
            course.content_required_total = course.content_required_total or 0

            key = (username, course_code)
            enrollment = enrollments.get(key)
            if not enrollment:
                enrollment = Enrollment(student_id=username, course_id=course_code)
                db.add(enrollment)
                enrollments[key] = enrollment
            enrollment.content_completed = _safe_int(vals[12])
            enrollment.content_required_w1w2 = _safe_int(vals[13])
            enrollment.content_required = _safe_int(vals[14])

        if valid_rows == 0:
            raise ValueError(
                f"No valid data rows found in {path.name} -> 'Learner Usage main dump'"
            )

        _merge_course_content_sheet(db, wb)
        db.flush()
        logger.info(f"Engagement ingestion complete with {valid_rows} valid rows.")
    finally:
        wb.close()


def _merge_course_content_sheet(db: Session, wb):
    """Merge course content counts from optional 'Courses' sheet."""
    if "Courses" not in wb.sheetnames:
        logger.warning("Optional sheet 'Courses' missing; skipping course content merge.")
        return

    courses = db.query(Course).all()
    by_name = {(_safe_str(c.name).lower()): c for c in courses if c.name}
    ws_courses = wb["Courses"]

    for i, row in enumerate(ws_courses.iter_rows(values_only=True)):
        if i == 0:
            continue
        vals = list(row)

        # T2 block
        if len(vals) >= 5 and vals[0] is not None:
            _update_course_content_row(
                by_name,
                _safe_str(vals[0]),
                _safe_int(vals[1]),
                _safe_int(vals[2]),
                _safe_int(vals[3]) if vals[3] != "-" else 0,
                _safe_int(vals[4]),
            )

        # T1 block
        if len(vals) >= 11 and vals[6] is not None:
            _update_course_content_row(
                by_name,
                _safe_str(vals[6]),
                _safe_int(vals[7]),
                _safe_int(vals[8]),
                _safe_int(vals[9]) if vals[9] != "-" else 0,
                _safe_int(vals[10]),
            )


def _update_course_content_row(by_name: dict, course_name: str, w1: int, w2: int, lab: int, total: int):
    if not course_name:
        return
    course = by_name.get(course_name.lower())
    if not course:
        return
    course.week1_content = w1
    course.week2_content = w2
    course.lab_content = lab
    course.content_required_w1w2 = w1 + w2
    course.content_required_total = total


def _ingest_quiz_assignment_exam(db: Session, files: dict, owner_thread_id: int):
    _assert_session_thread(owner_thread_id)
    path = Path(files["quiz_exam"])
    if not path.exists():
        logger.warning(
            "Optional quiz/exam workbook not found; skipping graded/exam ingestion: %s",
            path,
        )
        return
    logger.info(f"Reading {path}...")

    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    try:
        _ingest_graded_sheet(db, wb, "BS Attendance", "BS")
        _ingest_graded_sheet(db, wb, "MSc Attendance", "MSc")
        _ingest_written_exam_marks(db, wb)
        _ingest_exam_attendance(db, wb, "Attendance-Slot-1", "slot-1")
        _ingest_exam_attendance(db, wb, "Attendance-Slot-2", "slot-2")
        _ingest_exam_defaulters(db, wb)
        db.flush()
    finally:
        wb.close()


def _ingest_graded_sheet(db: Session, wb, sheet_name: str, program: str):
    if sheet_name not in wb.sheetnames:
        logger.warning(f"Sheet '{sheet_name}' not found, skipping.")
        return

    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 4:
        logger.warning(f"Sheet '{sheet_name}' has insufficient rows, skipping.")
        return

    header = list(rows[2])
    course_name = _safe_str(rows[0][7] if len(rows[0]) > 7 else "")
    graded_map = {
        (g.student_id, g.course_code, g.component_type, g.component_number): g
        for g in db.query(GradedComponent).all()
    }
    valid_rows = 0

    if program == "BS":
        quiz_cols = [7, 8, 9, 10]
        assignment_cols = [11]
        quiz_max_scores = [_parse_max_score(_safe_str(header[c])) if c < len(header) else 8.0 for c in quiz_cols]
        assignment_max = _parse_max_score(_safe_str(header[11])) if len(header) > 11 else 28.0
    else:
        quiz_cols = [7, 8, 10]
        assignment_cols = [9]
        quiz_max_scores = [_parse_max_score(_safe_str(header[c])) if c < len(header) else 15.0 for c in quiz_cols]
        assignment_max = _parse_max_score(_safe_str(header[9])) if len(header) > 9 else 20.0

    for row_idx in range(3, len(rows)):
        vals = list(rows[row_idx])
        if len(vals) < 5 or vals[2] is None:
            continue

        bits_id = _safe_str(vals[2])
        email = _safe_str(vals[3])
        student_name = _safe_str(vals[4])
        subject = _safe_str(vals[14] if program == "BS" and len(vals) > 14 else vals[13] if len(vals) > 13 else course_name)
        subject_code = _safe_str(vals[15] if program == "BS" and len(vals) > 15 else vals[14] if len(vals) > 14 else "")
        student_id = email if email else f"{bits_id.lower()}@bitspilani-digital.edu.in"
        if not student_id:
            continue

        valid_rows += 1
        _ensure_student(db, student_id, bits_id, student_name, program)

        for q_idx, col_idx in enumerate(quiz_cols):
            if col_idx >= len(vals):
                continue
            score_val = vals[col_idx]
            is_absent = score_val in ("A", None)
            score = None if is_absent else _safe_float(score_val)
            _upsert_graded_component(
                db,
                graded_map,
                student_id,
                subject_code,
                subject,
                "quiz",
                q_idx + 1,
                score,
                quiz_max_scores[q_idx],
                is_absent,
            )

        for a_idx, col_idx in enumerate(assignment_cols):
            if col_idx >= len(vals):
                continue
            asn_val = vals[col_idx]
            is_absent = asn_val in ("A", None)
            score = None if is_absent else _safe_float(asn_val)
            _upsert_graded_component(
                db,
                graded_map,
                student_id,
                subject_code,
                subject,
                "assignment",
                a_idx + 1,
                score,
                assignment_max,
                is_absent,
            )

    if valid_rows == 0:
        raise ValueError(f"No valid rows found in required sheet '{sheet_name}'.")
    logger.info(f"  {sheet_name}: merged {valid_rows} learner rows.")


def _upsert_graded_component(
    db: Session,
    graded_map: dict,
    student_id: str,
    course_code: str,
    course_name: str,
    component_type: str,
    component_number: int,
    score: float,
    max_score: float,
    missed: bool,
):
    key = (student_id, course_code, component_type, component_number)
    gc = graded_map.get(key)
    if not gc:
        gc = GradedComponent(
            student_id=student_id,
            course_code=course_code,
            component_type=component_type,
            component_number=component_number,
        )
        db.add(gc)
        graded_map[key] = gc
    gc.course_name = course_name
    gc.score = score
    gc.max_score = max_score
    gc.missed = missed


def _ingest_written_exam_marks(db: Session, wb):
    if "Written Exam Marks" not in wb.sheetnames:
        logger.warning("Sheet 'Written Exam Marks' not found.")
        return

    ws = wb["Written Exam Marks"]
    exam_map = {(e.student_id, e.course_code, e.slot): e for e in db.query(ExamRecord).all()}
    valid_rows = 0

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        vals = list(row)
        if len(vals) < 17 or vals[5] is None:
            continue

        email = _safe_str(vals[5])
        course_code = _safe_str(vals[3])
        student_name = _safe_str(vals[8])
        semester_info = _safe_str(vals[10])
        if not email or not course_code:
            continue

        valid_rows += 1
        slot = "slot-1" if "Slot-1" in semester_info else "slot-2" if "Slot-2" in semester_info else "unknown"
        program = "MSc" if "em" in email.lower() else "BS"
        _ensure_student(db, email, "", student_name, program)

        key = (email, course_code, slot)
        exam = exam_map.get(key)
        if not exam:
            exam = ExamRecord(student_id=email, course_code=course_code, slot=slot)
            db.add(exam)
            exam_map[key] = exam
        exam.course_name = exam.course_name or ""
        exam.marks_obtained = _safe_float(vals[16])
        exam.marks_total = _safe_float(vals[15])
        exam.present = True

    if valid_rows == 0:
        raise ValueError("No valid rows found in required sheet 'Written Exam Marks'.")


def _ingest_exam_attendance(db: Session, wb, sheet_name: str, slot: str):
    if sheet_name not in wb.sheetnames:
        logger.warning(f"Sheet '{sheet_name}' not found.")
        return

    ws = wb[sheet_name]
    exam_map = {(e.student_id, e.course_code, e.slot): e for e in db.query(ExamRecord).all()}
    valid_rows = 0

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        vals = list(row)
        if len(vals) < 15 or vals[0] is None:
            continue

        bits_id = _safe_str(vals[0])
        exam_mode = _safe_str(vals[1])
        email = _safe_str(vals[2])
        student_name = _safe_str(vals[3])
        course_code = _safe_str(vals[6])
        course_name = _safe_str(vals[7])
        status = _safe_str(vals[14]).lower()
        program = _safe_str(vals[19]) if len(vals) > 19 else ""
        student_id = email if email else f"{bits_id.lower()}@bitspilani-digital.edu.in"

        if not student_id or not course_code:
            continue
        valid_rows += 1

        _ensure_student(db, student_id, bits_id, student_name, program)
        key = (student_id, course_code, slot)
        exam = exam_map.get(key)
        if not exam:
            exam = ExamRecord(student_id=student_id, course_code=course_code, slot=slot)
            db.add(exam)
            exam_map[key] = exam
        exam.course_name = course_name
        exam.present = status == "present"
        exam.mode = exam_mode
        if exam.marks_total is None:
            exam.marks_total = 0

    if valid_rows == 0:
        raise ValueError(f"No valid rows found in required sheet '{sheet_name}'.")


def _ingest_exam_defaulters(db: Session, wb):
    if "Exam Defaulter" not in wb.sheetnames:
        logger.warning("Sheet 'Exam Defaulter' not found.")
        return

    ws = wb["Exam Defaulter"]
    exam_map = {(e.student_id, e.course_code, e.slot): e for e in db.query(ExamRecord).all()}

    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        vals = list(row)
        if len(vals) < 5 or vals[0] is None:
            continue
        bits_id = _safe_str(vals[0])
        student_name = _safe_str(vals[1])
        program = _safe_str(vals[3])
        status = _safe_str(vals[4]).lower()
        if status not in ("absent", "activation pending"):
            continue

        email = f"{bits_id.lower()}@bitspilani-digital.edu.in"
        _ensure_student(db, email, bits_id, student_name, program)
        key = (email, "EXAM_DEFAULT", "all")
        exam = exam_map.get(key)
        if not exam:
            exam = ExamRecord(student_id=email, course_code="EXAM_DEFAULT", slot="all")
            db.add(exam)
            exam_map[key] = exam
        exam.course_name = "Exam Defaulter"
        exam.marks_obtained = 0
        exam.marks_total = 0
        exam.present = False
        exam.mode = None


def _update_enrollments_from_latest(db: Session, files: dict, owner_thread_id: int):
    _assert_session_thread(owner_thread_id)
    course_name_to_id = {(_safe_str(c.name).lower()): c.id for c in db.query(Course).all() if c.name}
    enrollments = {(e.student_id, e.course_id): e for e in db.query(Enrollment).all()}

    sources = _snapshot_sources(files)
    for src in sources:
        path = Path(src["path"])
        if not path.exists():
            logger.warning(f"Skipping optional snapshot (not found): {path.name}")
            continue

        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
        try:
            if src["sheet"] not in wb.sheetnames:
                logger.warning(f"Skipping {path.name}: missing sheet '{src['sheet']}'")
                continue
            ws = wb[src["sheet"]]

            merged_rows = 0
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                if i == 0:
                    continue
                vals = list(row)
                if len(vals) < src["min_cols"] or vals[src["user_col"]] is None:
                    continue
                username = _safe_str(vals[src["user_col"]])
                if not username:
                    continue

                if src.get("course_col") is not None:
                    course_id = _safe_str(vals[src["course_col"]]) if src["course_col"] < len(vals) else ""
                else:
                    cname_raw = vals[src.get("cname_col", 0)] if src.get("cname_col", 0) < len(vals) else ""
                    course_id = course_name_to_id.get(_safe_str(cname_raw).lower(), "")

                if not course_id:
                    continue
                enrollment = enrollments.get((username, course_id))
                if not enrollment:
                    continue

                _merge_enrollment_fields(enrollment, vals, src["fields"])
                merged_rows += 1

            if merged_rows == 0:
                logger.warning(f"No rows merged from snapshot source: {path.name}")
            else:
                logger.info(f"Merged {merged_rows} rows from {path.name}.")
        finally:
            wb.close()


def _snapshot_sources(files: dict) -> list:
    return [
        {
            "label": "Week 1-2 T1 engagement",
            "path": files["week12"],
            "sheet": "Learner Usage main dump",
            "course_col": 0,
            "user_col": 6,
            "min_cols": 30,
            "fields": {
                "content_completed": 12,
                "content_required": 14,
                "checklist_completed": 16,
                "quiz_completed": 18,
                "total_quiz_attempts": 19,
                "discussion_posts_created": 20,
                "discussion_post_replies": 21,
                "discussion_posts_read": 22,
                "last_discussion_post_date": 23,
                "num_assignment_submissions": 24,
                "last_assignment_submission_date": 25,
                "total_time_spent_seconds": 26,
                "last_visited_date": 27,
                "last_system_login": 28,
                "num_logins": 29,
                "last_quiz_attempt_date": 31,
                "last_scorm_completion_date": 32,
                "last_scorm_visit_date": 33,
            },
        },
        {
            "label": "Graded Quiz Status 9 Feb",
            "path": files["quiz_9feb"],
            "sheet": "Data Dump - Learner Usage",
            "course_col": None,
            "cname_col": 0,
            "user_col": 3,
            "min_cols": 22,
            "fields": {
                "content_completed": 7,
                "content_required": 8,
                "checklist_completed": 9,
                "quiz_completed": 10,
                "total_quiz_attempts": 11,
                "discussion_posts_created": 12,
                "discussion_post_replies": 13,
                "discussion_posts_read": 14,
                "last_discussion_post_date": 15,
                "num_assignment_submissions": 16,
                "last_assignment_submission_date": 17,
                "total_time_spent_seconds": 18,
                "last_visited_date": 19,
                "last_system_login": 20,
                "num_logins": 21,
                "last_quiz_attempt_date": 23,
                "last_scorm_completion_date": 24,
            },
        },
        {
            "label": "Graded Quiz Feb 10 original",
            "path": files["quiz_10feb_orig"],
            "sheet": "Learner Usage-02-11-2026T10-14-",
            "course_col": 1,
            "user_col": 7,
            "min_cols": 29,
            "fields": {
                "content_completed": 14,
                "content_required": 15,
                "checklist_completed": 16,
                "quiz_completed": 17,
                "total_quiz_attempts": 18,
                "discussion_posts_created": 19,
                "discussion_post_replies": 20,
                "discussion_posts_read": 21,
                "last_discussion_post_date": 22,
                "num_assignment_submissions": 23,
                "last_assignment_submission_date": 24,
                "total_time_spent_seconds": 25,
                "last_visited_date": 26,
                "last_system_login": 27,
                "num_logins": 28,
                "last_quiz_attempt_date": 30,
                "last_scorm_completion_date": 31,
                "last_scorm_visit_date": 32,
            },
        },
        {
            "label": "Graded Quiz Feb 10 11:15",
            "path": files["quiz_10feb_1115"],
            "sheet": "Learner Usage-02-10-2026T11-12-",
            "course_col": 1,
            "user_col": 9,
            "min_cols": 31,
            "fields": {
                "content_completed": 16,
                "content_required": 17,
                "checklist_completed": 18,
                "quiz_completed": 19,
                "total_quiz_attempts": 20,
                "discussion_posts_created": 21,
                "discussion_post_replies": 22,
                "discussion_posts_read": 23,
                "last_discussion_post_date": 24,
                "num_assignment_submissions": 25,
                "last_assignment_submission_date": 26,
                "total_time_spent_seconds": 27,
                "last_visited_date": 28,
                "last_system_login": 29,
                "num_logins": 30,
                "last_quiz_attempt_date": 32,
                "last_scorm_completion_date": 33,
                "last_scorm_visit_date": 34,
            },
        },
        {
            "label": "Graded Quiz Feb 10 4:51",
            "path": files["quiz_10feb_451"],
            "sheet": "Learner Usage",
            "course_col": 1,
            "user_col": 8,
            "min_cols": 26,
            "fields": {
                "content_completed": 11,
                "content_required": 12,
                "checklist_completed": 13,
                "quiz_completed": 14,
                "total_quiz_attempts": 15,
                "discussion_posts_created": 16,
                "discussion_post_replies": 17,
                "discussion_posts_read": 18,
                "last_discussion_post_date": 19,
                "num_assignment_submissions": 20,
                "last_assignment_submission_date": 21,
                "total_time_spent_seconds": 22,
                "last_visited_date": 23,
                "last_system_login": 24,
                "num_logins": 25,
                "last_quiz_attempt_date": 27,
                "last_scorm_completion_date": 28,
                "last_scorm_visit_date": 29,
            },
        },
        {
            "label": "Learner usage week 3",
            "path": files["week3"],
            "sheet": "Learner Usage",
            "course_col": 0,
            "user_col": 4,
            "min_cols": 32,
            "fields": {
                "content_completed": 10,
                "checklist_completed": 19,
                "quiz_completed": 20,
                "total_quiz_attempts": 21,
                "discussion_posts_created": 22,
                "discussion_post_replies": 23,
                "discussion_posts_read": 24,
                "last_discussion_post_date": 25,
                "num_assignment_submissions": 26,
                "last_assignment_submission_date": 27,
                "total_time_spent_seconds": 28,
                "last_visited_date": 29,
                "last_system_login": 30,
                "num_logins": 31,
                "last_quiz_attempt_date": 33,
                "last_scorm_completion_date": 34,
                "last_scorm_visit_date": 35,
            },
        },
        {
            "label": "Learner usage week 5",
            "path": files["week5"],
            "sheet": "Main Dump",
            "course_col": 1,
            "user_col": 9,
            "min_cols": 31,
            "fields": {
                "content_completed": 16,
                "content_required": 17,
                "checklist_completed": 18,
                "quiz_completed": 19,
                "total_quiz_attempts": 20,
                "discussion_posts_created": 21,
                "discussion_post_replies": 22,
                "discussion_posts_read": 23,
                "last_discussion_post_date": 24,
                "num_assignment_submissions": 25,
                "last_assignment_submission_date": 26,
                "total_time_spent_seconds": 27,
                "last_visited_date": 28,
                "last_system_login": 29,
                "num_logins": 30,
                "last_quiz_attempt_date": 32,
                "last_scorm_completion_date": 33,
                "last_scorm_visit_date": 34,
            },
        },
    ]


def _merge_enrollment_fields(enrollment: Enrollment, vals: list, fields: dict):
    for field, col in fields.items():
        if col >= len(vals) or vals[col] is None:
            continue
        raw = vals[col]
        if field in COUNTER_FIELDS:
            new_val = _safe_int(raw)
            if new_val > (getattr(enrollment, field) or 0):
                setattr(enrollment, field, new_val)
        else:
            setattr(enrollment, field, str(raw))


def _ensure_student(db: Session, student_id: str, org_id: str, name: str, program: str):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        student = Student(id=student_id)
        db.add(student)

    parts = _safe_str(name).split(None, 1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""

    if "msc" in _safe_str(program).lower() or "ms" in _safe_str(program).lower():
        dept_name = "MSc - Data Science & AI"
        dept_code = "dept_msc_dsai"
    else:
        dept_name = "BS - Data Science & AI"
        dept_code = "dept_bs_dsai"

    student.org_defined_id = org_id or student.org_defined_id
    student.first_name = first_name or student.first_name
    student.last_name = last_name or student.last_name
    student.old_new_student = student.old_new_student or "new"
    student.is_active = True if student.is_active is None else student.is_active
    student.parent_department_name = dept_name
    student.parent_department_code = dept_code


def _assert_session_thread(owner_thread_id: int):
    current_thread_id = threading.get_ident()
    if current_thread_id != owner_thread_id:
        raise RuntimeError(
            "Unsafe DB usage: SQLAlchemy session accessed from a different thread."
        )


def _safe_str(val) -> str:
    return str(val).strip() if val is not None else ""


def _safe_int(val):
    if val is None:
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _safe_float(val):
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _parse_max_score(header_text: str) -> float:
    try:
        if "(" in header_text and ")" in header_text:
            inside = header_text.split("(")[1].split(")")[0]
            return float(inside)
    except (ValueError, IndexError):
        pass
    return 10.0
