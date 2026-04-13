"""Idempotent, validated ETL ingestion for EWS retention data."""

import asyncio
import hashlib
import logging
import os
import redis as redis_lib
import threading
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
from backend.database.models.ingestion_run import IngestionRun
from backend.database.models.course_content_registry import CourseContentRegistry
from backend.database.models.intervention_log import InterventionLog
from backend.database.models.goals_and_risks import RiskSnapshot


logger = logging.getLogger(__name__)

# Redis distributed lock for cross-process ingestion synchronization


def _get_redis_lock():
    from backend.config import REDIS_URL
    r = redis_lib.from_url(REDIS_URL)
    return r.lock("ews_ingestion_lock", timeout=600, blocking_timeout=0)


@dataclass
class IngestionStats:
    """Tracks statistics and errors during data ingestion."""
    students_created: int = 0
    students_updated: int = 0
    enrollments_created: int = 0
    enrollments_updated: int = 0
    graded_components_added: int = 0
    risk_scores_updated: int = 0
    files_processed: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    seen_org_ids: set = field(default_factory=set)  # Track org IDs for soft delete (CROSS-1)

    def add_error(self, file_name: str, error_msg: str):
        """Record an error with the associated file."""
        self.errors.append({"file": file_name, "error": str(error_msg)})


def col(header: dict, *names: str):
    for n in names:
        if n in header:
            return header[n]
    return None


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

ABSENT_SENTINELS = {"A", "AB", "a", "-", "NP", "Exc", "EX", ""}

# Maps exam defaulter final remarks to normalized reason codes
DEFAULTER_REASON_MAP = {
    "full deffered":                      "deferred",
    "full deferred":                      "deferred",
    "will pursue in jan 2026":            "deferred",
    "refund requested after due date":    "dropout_intent",
    "no reason given":                    "unknown_high_risk",
    "health issue":                       "health_support",
    "personal commitment":                "personal",
    "exam clash":                         "scheduling",
    "can't contn prof commitment":        "dropout_intent",
    "activation pending":                 "not_activated",
    "preference not selected":            "not_activated",
}

DATE_FIELDS = {
    "last_system_login",
    "last_visited_date",
    "last_quiz_attempt_date",
    "last_scorm_completion_date",
    "last_scorm_visit_date",
    "last_assignment_submission_date",
}


async def _cleanup_uploaded_file(filepath: Path):
    """Delete uploaded file after successful ingestion."""
    try:
        if filepath and filepath.exists():
            filepath.unlink()
            logger.info(f"Cleaned up uploaded file: {filepath.name}")
    except Exception:
        logger.warning(f"Could not clean up file: {filepath}")  # non-fatal


async def ingest_all_data(db: Session, triggered_by: str = "startup", uploaded_filepath: Path = None):
    """
    Run ETL in a single transaction-safe flow with full audit logging.

    Args:
        db: SQLAlchemy session
        triggered_by: Source of ingestion trigger ("startup"|"api"|"manual")

    Idempotency:
    - Inserts use update-or-create semantics.
    - Running multiple times refreshes data instead of duplicating rows.

    Concurrency:
    - Only one ingestion can run at a time across all workers (Redis distributed lock).
      If another is in progress, raises RuntimeError.
    """
    # Acquire distributed lock to prevent concurrent ingestion across workers
    lock = _get_redis_lock()
    acquired = lock.acquire()
    if not acquired:
        logger.warning("Ingestion already in progress — skipping")
        raise RuntimeError("Ingestion lock is held by another process")

    try:
        stats = IngestionStats()
        run = IngestionRun(triggered_by=triggered_by, status="running")
        db.add(run)
        db.commit()
        start_time = time.time()

        try:
            await _run_ingestion(db, stats)
            run.status = "partial" if stats.errors else "success"
        except Exception as e:
            run.status = "failed"
            stats.add_error("ingest_all_data", str(e))
            db.rollback()
            logger.exception("Data ingestion failed.", extra={"run_id": run.id})
            raise
        finally:
            run.duration_seconds = round(time.time() - start_time, 2)
            run.students_created = stats.students_created
            run.students_updated = stats.students_updated
            run.enrollments_created = stats.enrollments_created
            run.enrollments_updated = stats.enrollments_updated
            run.graded_components_added = stats.graded_components_added
            run.risk_scores_updated = stats.risk_scores_updated
            run.files_processed = stats.files_processed
            run.errors = stats.errors
            db.commit()

            # Structured logging for monitoring (ERROR-2)
            logger.info(
                "Ingestion complete",
                extra={
                    "run_id": run.id,
                    "status": run.status,
                    "students_created": stats.students_created,
                    "students_updated": stats.students_updated,
                    "enrollments_processed": stats.enrollments_created + stats.enrollments_updated,
                    "duration_seconds": run.duration_seconds,
                    "error_count": len(stats.errors),
                }
            )

            # D12-1: Alert on ingestion failure
            if run.status == "failed":
                logger.critical(
                    "ALERT: Ingestion run failed — advisors may see stale data",
                    extra={
                        "run_id": run.id,
                        "error_count": len(stats.errors),
                        "first_error": stats.errors[0] if stats.errors else None,
                    }
                )
                # Optional: send to a Slack/email webhook if configured
                alert_webhook = os.getenv("ALERT_WEBHOOK_URL")
                if alert_webhook:
                    import httpx
                    try:
                        httpx.post(alert_webhook, json={
                            "text": f"EWS ingestion FAILED at {datetime.utcnow().isoformat()}. "
                            f"{len(stats.errors)} errors. Check logs for run_id={run.id}"
                        }, timeout=5)
                    except Exception:
                        pass  # Alert failure must not crash ingestion
    finally:
        # Release distributed lock (ignore errors if lock expired)
        try:
            lock.release()
        except Exception:
            pass  # Lock may have expired; that's fine


async def _run_ingestion(db: Session, stats: IngestionStats):
    """
    Internal ingestion logic with stats tracking.
    """
    owner_thread_id = threading.get_ident()
    _assert_session_thread(owner_thread_id)

    files = _build_file_map()
    _validate_required_files(files)

    logger.info("Starting data ingestion from XLSX files...")
    try:
        await _ingest_engagement_data(db, files, owner_thread_id, stats)
        await _ingest_quiz_assignment_exam(db, files, owner_thread_id, stats)
        await _update_enrollments_from_latest(db, files, owner_thread_id, stats)
        db.flush()

        # Infer enrollment outcomes from exam data for T1 cohort
        infer_outcomes_from_exam_data(db)

        # Backfill intervention outcomes after all risk scores updated
        backfill_intervention_outcomes(db)

        # Soft delete: deactivate students not in latest export (CROSS-1)
        # Get semester name from first course or use default
        semester_name = "current"
        if files.get("engagement"):
            from pathlib import Path
            semester_name = Path(files["engagement"]).stem
        await _deactivate_missing_students(db, stats.seen_org_ids, semester_name)

        logger.info("Data ingestion complete.")
    except Exception:
        db.rollback()
        raise


def backfill_intervention_outcomes(session: Session):
    """
    Backfill outcome fields for acted-upon interventions that are >= 7 days old.

    Compares current risk scores (from RiskSnapshot) with recommendation-time scores
    to determine if intervention was successful.

    Do not commit inside this function — caller owns the transaction.
    """
    cutoff = datetime.utcnow() - timedelta(days=7)
    pending_logs = session.query(InterventionLog).filter(
        InterventionLog.acted_on.is_(True),
        InterventionLog.follow_up_risk_score.is_(None),
        InterventionLog.recommended_at <= cutoff,
    ).all()

    for log in pending_logs:
        # Get latest risk snapshot for this student
        latest_snapshot = session.query(RiskSnapshot).filter(
            RiskSnapshot.student_id == log.student_org_id
        ).order_by(RiskSnapshot.timestamp.desc()).first()

        if not latest_snapshot:
            continue

        delta = latest_snapshot.risk_score - log.risk_score_at_recommendation
        log.follow_up_risk_score = latest_snapshot.risk_score
        log.follow_up_at = datetime.utcnow()
        log.outcome_delta = round(delta, 2)

        if delta <= -5.0:
            log.outcome = "improved"
        elif delta >= 5.0:
            log.outcome = "worsened"
        else:
            log.outcome = "unchanged"

    logger.info(f"Backfilled outcomes for {len(pending_logs)} intervention logs")


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


async def _ingest_engagement_data(db: Session, files: dict, owner_thread_id: int, stats: IngestionStats):
    _assert_session_thread(owner_thread_id)
    path = Path(files["engagement"])
    logger.info(f"Reading {path}...")
    sheet_name = "Learner Usage main dump"

    try:
        wb = await asyncio.to_thread(openpyxl.load_workbook, str(path), read_only=True, data_only=True)
    except (openpyxl.utils.exceptions.InvalidFileException,
            zipfile.BadZipFile,
            ValueError,
            KeyError) as e:
        logger.warning("Skipping unreadable file",
                       extra={"file": path.name, "error": type(e).__name__})
        stats.add_error(path.name, f"Unreadable file: {type(e).__name__}")
        return
    try:
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise ValueError(f"No rows in {path.name} -> '{sheet_name}'")
        logger.info("Processing engagement data", extra={"file": path.name, "rows": len(rows) - 1})

        header = {
            str(cell).strip().lower(): i
            for i, cell in enumerate(rows[0])
            if cell is not None
        }

        username_col = col(header, "username")
        if username_col is None:
            raise ValueError(
                f"Required column 'username' not found in {sheet_name}. Headers: {list(header.keys())}"
            )
        org_defined_id_col = col(header, "org defined id")
        if org_defined_id_col is None:
            raise ValueError(
                f"Required column 'org defined id' not found in {sheet_name}. Headers: {list(header.keys())}"
            )

        course_code_col = col(header, "course offering code")
        course_name_col = col(header, "course offering name")
        dept_name_col = col(header, "parent department name")
        dept_code_col = col(header, "parent department code")
        semester_code_col = col(header, "semester code")
        semester_name_col = col(header, "semester name")
        old_new_col = col(header, "old/new student")
        first_name_col = col(header, "first name")
        last_name_col = col(header, "last name")
        is_active_col = col(header, "is active")
        content_completed_col = col(header, "content completed")
        content_required_w1w2_col = col(header, "content required w1&2")
        content_required_col = col(
            header, "content required", "content required w1&2"
        )

        existing_students = {s.id: s for s in db.query(Student).all()}
        existing_courses = {c.id: c for c in db.query(Course).all()}
        enrollments = {
            (e.student_id, e.course_id): e for e in db.query(Enrollment).all()
        }

        def _cell_str(vals: list, idx):
            if idx is None or idx >= len(vals):
                return ""
            return _safe_str(vals[idx])

        def _cell_int(vals: list, idx):
            if idx is None or idx >= len(vals):
                return None
            return _safe_int(vals[idx])

        valid_rows = 0
        for row in rows[1:]:
            vals = list(row)
            course_code = _cell_str(vals, course_code_col)
            username = _cell_str(vals, username_col)
            if not course_code or not username:
                continue
            valid_rows += 1

            course_name = _cell_str(vals, course_name_col)
            dept_name = _cell_str(vals, dept_name_col).replace("&amp;", "&")
            dept_code = _cell_str(vals, dept_code_col)
            semester_code = _cell_str(vals, semester_code_col)
            semester_name = _cell_str(vals, semester_name_col)
            org_id = _cell_str(vals, org_defined_id_col)
            old_new = _cell_str(vals, old_new_col) or "new"
            first_name = _cell_str(vals, first_name_col)
            last_name = _cell_str(vals, last_name_col)
            if is_active_col is not None and is_active_col < len(vals):
                is_active = bool(vals[is_active_col]) if vals[is_active_col] is not None else True
            else:
                is_active = True

            student = existing_students.get(username)
            if not student:
                student = Student(id=username)
                db.add(student)
                existing_students[username] = student
                stats.students_created += 1
            else:
                stats.students_updated += 1
            student.org_defined_id = org_id
            student.first_name = first_name
            student.last_name = "" if last_name == "." else last_name

            # D2-3: Only update old_new_student on first creation or semester change
            if student.old_new_student is None:
                student.old_new_student = old_new  # first ingest — set from spreadsheet
            elif getattr(student, 'semester_code', None) != semester_code:
                # Student is returning from a previous semester — promote to "old"
                student.old_new_student = "old"
            # Otherwise: keep existing value — don't let stale spreadsheet data overwrite

            student.is_active = is_active
            student.parent_department_name = dept_name
            student.parent_department_code = dept_code
            # Track current semester for change detection on next ingest
            student.semester_code = semester_code

            # Track org_id for soft delete detection (CROSS-1)
            if org_id:
                stats.seen_org_ids.add(org_id)

            # D2-6: Auto-rescind stale ghost alerts if student has logged in
            login_count = _cell_int(vals, header.get("num logins")) or 0
            if login_count > 0:
                _rescind_stale_ghost_alerts(db, org_id, login_count)

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
                stats.enrollments_created += 1
            else:
                stats.enrollments_updated += 1

            # Detect self-paced optional courses
            is_optional = (
                "[SELF-PACED-OPTIONAL]" in (course_name or "").upper()
                or "SELF PACED" in (course_name or "").upper()
                or "FOUNDATION" in (course_name or "").upper()
            )
            enrollment.is_optional = is_optional

            v = _cell_int(vals, content_completed_col)
            if v is not None:
                enrollment.content_completed = v
            v = _cell_int(vals, content_required_w1w2_col)
            if v is not None:
                enrollment.content_required_w1w2 = v
            v = _cell_int(vals, content_required_col)
            if v is not None:
                enrollment.content_required = v
                # Upsert to registry for fallback lookup
                upsert_course_content_registry(
                    db,
                    course_offering_code=course_code,
                    course_name=course_name,
                    semester_name=semester_name or "",
                    content_required=v,
                    source_file=path.name,
                )

        if valid_rows == 0:
            stats.add_error(path.name, f"No valid data rows found in '{sheet_name}'")
            logger.warning("No valid engagement rows", extra={"file": path.name})
        else:
            stats.files_processed.append({"name": path.name, "rows": valid_rows})
            logger.info(
                "Engagement data processed",
                extra={
                    "file": path.name,
                    "valid_rows": valid_rows,
                    "students_created": stats.students_created,
                    "students_updated": stats.students_updated,
                },
            )

        _merge_course_content_sheet(db, wb)
        db.flush()
    finally:
        wb.close()


def _int_or_zero(val):
    v = _safe_int(val)
    return 0 if v is None else v


def upsert_course_content_registry(
    db: Session,
    course_offering_code: str,
    course_name: str,
    semester_name: str,
    content_required: int,
    source_file: str = None,
) -> None:
    """
    Upsert a course content requirement into the registry.

    - If not found: INSERT with the given content_required
    - If found AND new content_required > existing: UPDATE and log
    - If found AND new content_required <= existing: skip (never reduce known max)
    """
    if not course_offering_code or not semester_name:
        return
    if not content_required or content_required <= 0:
        return

    existing = (
        db.query(CourseContentRegistry)
        .filter_by(course_offering_code=course_offering_code, semester_name=semester_name)
        .first()
    )

    # Also check objects pending in the session (not yet flushed to DB)
    if existing is None:
        existing = next(
            (
                obj for obj in db.new
                if isinstance(obj, CourseContentRegistry)
                and obj.course_offering_code == course_offering_code
                and obj.semester_name == semester_name
            ),
            None,
        )

    if not existing:
        # Insert new record
        registry = CourseContentRegistry(
            course_offering_code=course_offering_code,
            course_name=course_name or course_offering_code,
            semester_name=semester_name,
            content_required=content_required,
            source_file=source_file,
        )
        db.add(registry)
        logger.info(f"CourseContentRegistry created: {course_offering_code} ({semester_name}) = {content_required}")
    elif content_required > existing.content_required:
        # Update with higher value (content was added mid-trimester)
        old_value = existing.content_required
        existing.content_required = content_required
        existing.source_file = source_file
        logger.info(
            f"content_required updated for {course_offering_code} ({semester_name}): "
            f"{old_value} → {content_required} (source: {source_file})"
        )
    # else: existing >= new, skip to avoid reducing known maximum


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
                _int_or_zero(vals[1]),
                _int_or_zero(vals[2]),
                _int_or_zero(vals[3]) if vals[3] != "-" else 0,
                _int_or_zero(vals[4]),
            )

        # T1 block
        if len(vals) >= 11 and vals[6] is not None:
            _update_course_content_row(
                by_name,
                _safe_str(vals[6]),
                _int_or_zero(vals[7]),
                _int_or_zero(vals[8]),
                _int_or_zero(vals[9]) if vals[9] != "-" else 0,
                _int_or_zero(vals[10]),
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


async def _ingest_quiz_assignment_exam(db: Session, files: dict, owner_thread_id: int, stats: IngestionStats):
    _assert_session_thread(owner_thread_id)
    path = Path(files["quiz_exam"])
    if not path.exists():
        stats.add_error("quiz_exam", "Optional quiz/exam workbook not found")
        return

    try:
        wb = await asyncio.to_thread(openpyxl.load_workbook, str(path), read_only=True, data_only=True)
    except (openpyxl.utils.exceptions.InvalidFileException,
            zipfile.BadZipFile,
            ValueError,
            KeyError) as e:
        logger.warning("Skipping unreadable file",
                       extra={"file": path.name, "error": type(e).__name__})
        stats.add_error(path.name, f"Unreadable file: {type(e).__name__}")
        return
    try:
        _ingest_graded_sheet(db, wb, "BS Attendance", "BS", stats)
        _ingest_graded_sheet(db, wb, "MSc Attendance", "MSc", stats)
        _ingest_written_exam_marks(db, wb)
        _ingest_exam_attendance(db, wb, "Attendance-Slot-1", "slot-1")
        _ingest_exam_attendance(db, wb, "Attendance-Slot-2", "slot-2")
        _ingest_exam_defaulters(db, wb)
        db.flush()
    finally:
        wb.close()


def _ingest_graded_sheet(db: Session, wb, sheet_name: str, program: str, stats: IngestionStats):
    if sheet_name not in wb.sheetnames:
        stats.add_error(sheet_name, "Sheet not found, skipping")
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
        _ensure_student(db, student_id, bits_id, student_name, program, stats)

        for q_idx, col_idx in enumerate(quiz_cols):
            if col_idx >= len(vals):
                continue
            score_val = vals[col_idx]
            is_absent = score_val is None or str(score_val).strip() in ABSENT_SENTINELS
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
                stats,
            )

        for a_idx, col_idx in enumerate(assignment_cols):
            if col_idx >= len(vals):
                continue
            asn_val = vals[col_idx]
            is_absent = asn_val is None or str(asn_val).strip() in ABSENT_SENTINELS
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
                stats,
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
    stats: IngestionStats,
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
        stats.graded_components_added += 1
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
        org_defined_id_raw = _safe_str(vals[6]) if len(vals) > 6 else ""
        if not org_defined_id_raw and "@" in email:
            org_defined_id_raw = email.split("@", 1)[0]
        oid = org_defined_id_raw.upper()
        if oid.startswith("2025EM") or oid.startswith("2024EM"):
            program = "MSc"
        else:
            program = "BS"
        _ensure_student(db, email, org_defined_id_raw, student_name, program)

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

    # Read header to find UFM column
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        logger.warning(f"No rows in sheet '{sheet_name}'")
        return

    header = {str(cell).strip().lower(): i for i, cell in enumerate(rows[0]) if cell is not None}
    ufm_col = None
    for col_name, idx in header.items():
        if "ufm" in col_name:
            ufm_col = idx
            break

    for i, row in enumerate(rows[1:], start=1):
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

        # Read UFM flag if column exists
        if ufm_col is not None and ufm_col < len(vals):
            ufm_val = _safe_str(vals[ufm_col]).strip().lower()
            exam.ufm_flagged = ufm_val == "yes"

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

    # Read header to find FINAL REMARKS column
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        logger.warning("No rows in sheet 'Exam Defaulter'")
        return

    header = {str(cell).strip().lower(): i for i, cell in enumerate(rows[0]) if cell is not None}
    remarks_col = None
    for col_name, idx in header.items():
        if "final remarks" in col_name or "remarks" in col_name:
            remarks_col = idx
            break

    for i, row in enumerate(rows[1:], start=1):
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

        # Map FINAL REMARKS to normalized reason code
        if remarks_col is not None and remarks_col < len(vals):
            raw_remark = _safe_str(vals[remarks_col]).strip().lower()
            if raw_remark:
                mapped_reason = DEFAULTER_REASON_MAP.get(raw_remark, "unknown_high_risk")
                exam.defaulter_reason = mapped_reason


async def _update_enrollments_from_latest(db: Session, files: dict, owner_thread_id: int, stats: IngestionStats):
    _assert_session_thread(owner_thread_id)
    course_name_to_id = {(_safe_str(c.name).lower()): c.id for c in db.query(Course).all() if c.name}
    enrollments = {(e.student_id, e.course_id): e for e in db.query(Enrollment).all()}

    sources = _snapshot_sources(files)
    for src in sources:
        path = Path(src["path"])
        if not path.exists():
            logger.warning(f"Skipping optional snapshot (not found): {path.name}")
            continue

        wb = await asyncio.to_thread(openpyxl.load_workbook, str(path), read_only=True, data_only=True)
        try:
            if src.get("learner_usage_sheet_by_prefix"):
                sheet = next((s for s in wb.sheetnames if s.startswith("Learner Usage")), None)
                if not sheet:
                    logger.warning(
                        f"No 'Learner Usage*' sheet in {path.name}. Found: {wb.sheetnames}"
                    )
                    continue
            else:
                sheet = src["sheet"]
                if sheet not in wb.sheetnames:
                    logger.warning(f"Skipping {path.name}: missing sheet '{sheet}'")
                    continue
            ws = wb[sheet]

            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                logger.warning(f"No rows in snapshot: {path.name}")
                continue
            header = {
                str(cell).strip().lower(): i
                for i, cell in enumerate(rows[0])
                if cell is not None
            }
            fields = dict(src["fields"])
            for f_name, names in src.get("header_resolved_fields", {}).items():
                idx = col(header, *names)
                if idx is not None:
                    fields[f_name] = idx

            merged_rows = 0
            for row in rows[1:]:
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

                _merge_enrollment_fields(enrollment, vals, fields)
                merged_rows += 1
                stats.enrollments_updated += 1

            if merged_rows == 0:
                stats.add_error(path.name, "No rows merged from snapshot source")
            else:
                stats.files_processed.append({"name": path.name, "rows": merged_rows})
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
            "learner_usage_sheet_by_prefix": True,
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
            "learner_usage_sheet_by_prefix": True,
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
            "header_resolved_fields": {
                "content_required": (
                    "content required w1,2,3",
                    "content required",
                ),
            },
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
    for fname, col in fields.items():
        if col >= len(vals):
            continue
        raw = vals[col]
        if fname in COUNTER_FIELDS:
            new_val = _safe_int(raw)
            if new_val is not None and new_val > (getattr(enrollment, fname) or 0):
                setattr(enrollment, fname, new_val)
        elif fname in DATE_FIELDS:
            existing = getattr(enrollment, fname, None)
            new_val = str(raw) if raw is not None else None
            if new_val is None:
                pass
            elif existing is None:
                setattr(enrollment, fname, new_val)
            elif new_val > existing:
                setattr(enrollment, fname, new_val)
        else:
            if raw is None:
                continue
            setattr(enrollment, fname, str(raw))


def derive_program_from_org_id(org_id: str) -> str:
    """
    Derive program (BS/MSc) from Org_Defined_Id prefix.

    B-3 Fix: This function checks for exact prefix "2025EM" or "2024EM"
    to identify MSc students, NOT use substring matching on email.

    Args:
        org_id: The Org_Defined_Id (e.g., "2025EB1100001" or "2025EM1100001")

    Returns:
        "MSc" if org_id starts with "2025EM" or "2024EM", otherwise "BS"
    """
    if not org_id:
        return "BS"
    oid = org_id.upper()
    if oid.startswith("2025EM") or oid.startswith("2024EM"):
        return "MSc"
    return "BS"


def _ensure_student(db: Session, student_id: str, org_id: str, name: str, program: str, stats: IngestionStats = None):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        student = Student(id=student_id)
        db.add(student)

    # Track org_id for soft delete detection (CROSS-1)
    if stats and org_id:
        stats.seen_org_ids.add(org_id)

    parts = _safe_str(name).split(None, 1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""

    # B-3 Fix: Derive program from org_id, not from the file's program column
    derived_program = derive_program_from_org_id(org_id)
    if derived_program == "MSc":
        dept_name = "MSc - Data Science & AI"
        dept_code = "dept_msc_dsai"
    else:
        dept_name = "BS - Data Science & AI"
        dept_code = "dept_bs_dsai"

    student.org_defined_id = org_id or student.org_defined_id
    student.first_name = first_name or student.first_name
    student.last_name = last_name or student.last_name
    student.old_new_student = student.old_new_student or "new"
    # Reactivate if previously deactivated
    if not student.is_active:
        student.is_active = True
        student.deactivated_at = None
        student.deactivation_reason = None
        logger.info(
            "Student reactivated",
            extra={
                "org_id_prefix": (org_id or "")[:4] + "…",
                "id_hash": hashlib.sha256((student_id or "").encode()).hexdigest()[:10],
            }
        )
    # B-3 Fix: Do NOT overwrite existing department assignments
    if not student.parent_department_name:
        student.parent_department_name = dept_name
        student.parent_department_code = dept_code


def _assert_session_thread(owner_thread_id: int):
    current_thread_id = threading.get_ident()
    if current_thread_id != owner_thread_id:
        raise RuntimeError(
            "Unsafe DB usage: SQLAlchemy session accessed from a different thread."
        )


async def _deactivate_missing_students(session, seen_org_ids: set, semester_name: str):
    """
    Mark students not in the latest export as inactive (soft delete).

    Args:
        session: SQLAlchemy session
        seen_org_ids: Set of org_defined_ids seen in current ingestion
        semester_name: Current semester for context logging
    """
    from backend.database.models.student import Student

    active_students = session.query(Student).filter(Student.is_active.is_(True)).all()
    deactivated_count = 0

    for student in active_students:
        if student.org_defined_id and student.org_defined_id not in seen_org_ids:
            student.is_active = False
            student.deactivated_at = datetime.utcnow()
            student.deactivation_reason = "not_in_latest_export"
            deactivated_count += 1
            logger.info(
                "Student deactivated",
                extra={
                    "org_id_prefix": (student.org_defined_id or "")[:4] + "…",
                    "id_hash": hashlib.sha256((student.id or "").encode()).hexdigest()[:10],
                    "reason": "not_in_latest_export",
                }
            )

    if deactivated_count:
        logger.info(f"Deactivated {deactivated_count} students not in latest export for {semester_name}")
        session.commit()


def _rescind_stale_ghost_alerts(db, org_id: str, current_login_count: int):
    """Auto-dismiss ghost alerts if student has logged in since the alert was raised."""
    if current_login_count <= 0 or not org_id:
        return

    stale_logs = (
        db.query(InterventionLog)
        .filter(
            InterventionLog.student_org_id == org_id,
            InterventionLog.intervention_type == "activation_outreach",
            InterventionLog.reviewed.is_(False),
        )
        .all()
    )

    for log in stale_logs:
        log.reviewed = True
        log.acted_on = False
        log.dismissed_reason = "student_became_active_auto"

    if stale_logs:
        logger.info(
            "Auto-dismissed stale ghost alerts",
            extra={
                "count": len(stale_logs),
                "org_id_prefix": (org_id or "")[:4] + "…",
            }
        )


def _safe_str(val) -> str:
    return str(val).strip() if val is not None else ""


def _safe_int(val):
    if val is None:
        return None
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return None


def _safe_float(val):
    if val is None:
        return None
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


def _parse_max_score(header_text: str) -> float:
    try:
        if "(" in header_text and ")" in header_text:
            inside = header_text.split("(")[1].split(")")[0]
            return float(inside)
    except (ValueError, IndexError):
        pass
    return 10.0


def infer_outcomes_from_exam_data(db: Session) -> int:
    """
    Infer final_outcome for T1 cohort from ExamRecord data.

    Rules:
    - If any exam has present=False AND defaulter_reason in ("dropout_intent", "unknown_high_risk"): dropped
    - If any exam has present=False AND defaulter_reason="deferred": deferred
    - If all exams have present=True AND marks_obtained/marks_total >= 0.40: completed
    - If all exams have present=True AND marks_obtained/marks_total < 0.40: active (still enrolled, didn't pass)
    - Otherwise: leave as None (unknown)

    Returns:
        Number of enrollments updated with inferred outcomes
    """
    from datetime import datetime

    # Get all students with exam records
    exam_records = db.query(ExamRecord).all()

    # Group exam records by student
    student_exams: dict = {}
    for exam in exam_records:
        if exam.student_id not in student_exams:
            student_exams[exam.student_id] = []
        student_exams[exam.student_id].append(exam)

    # Get enrollments for these students
    student_ids = list(student_exams.keys())
    enrollments = db.query(Enrollment).filter(Enrollment.student_id.in_(student_ids)).all()

    updated_count = 0
    now = datetime.utcnow()

    for enrollment in enrollments:
        exams = student_exams.get(enrollment.student_id, [])
        if not exams:
            continue

        outcome = None
        source = None

        # Check for defaulters (absent with reason)
        absent_exams = [e for e in exams if not e.present]
        for exam in absent_exams:
            reason = exam.defaulter_reason
            if reason in ("dropout_intent", "unknown_high_risk"):
                outcome = "dropped"
                source = "exam_data"
                break
            elif reason == "deferred":
                outcome = "deferred"
                source = "exam_data"
                break

        # If no defaulter outcome determined, check passed exams
        if outcome is None:
            present_exams = [e for e in exams if e.present]
            if present_exams:
                # Calculate overall pass rate across all present exams
                total_obtained = sum(e.marks_obtained or 0 for e in present_exams)
                total_marks = sum(e.marks_total or 0 for e in present_exams)

                if total_marks > 0:
                    pass_rate = total_obtained / total_marks
                    if pass_rate >= 0.40:
                        outcome = "completed"
                        source = "exam_data"
                    else:
                        # Still enrolled but didn't pass
                        outcome = "active"
                        source = "exam_data"

        # Update enrollment if we determined an outcome
        if outcome:
            enrollment.final_outcome = outcome
            enrollment.outcome_source = source
            enrollment.outcome_updated_at = now
            updated_count += 1

    db.commit()
    logger.info(f"Inferred outcomes for {updated_count} enrollments from exam data")
    return updated_count
