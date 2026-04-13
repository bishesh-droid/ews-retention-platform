"""
Async scheduler service for background jobs.

This module avoids blocking loops in the main thread and is safe to start/stop
from FastAPI lifespan.
"""

import asyncio
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from backend.database.models.academic import ExamRecord, GradedComponent
from backend.database.models.course import Course
from backend.database.models.enrollment import Enrollment
from backend.database.models.goals_and_risks import RiskSnapshot
from backend.database.models.intervention_log import InterventionLog
from backend.database.models.prediction import Prediction
from backend.database.models.student import Student
from backend.database.models.event import EngineeredFeatures
from sqlalchemy.dialects.postgresql import insert as pg_insert
import shutil
from pathlib import Path
import backend.config as settings
from backend.config import trimester_week_number
from backend.database.connection import SessionLocal
from backend.services.feature_engineering import FeatureEngineer
from backend.services.infrastructure.token_cleanup import purge_expired_revoked_tokens
from backend.services.calendar_scorer import get_current_week
from backend.services.risk_scoring import RiskScorer

logger = logging.getLogger(__name__)

# Async lock to prevent overlapping prediction jobs
_prediction_job_lock = asyncio.Lock()


@contextmanager
def db_session_scope():
    """Provide a transactional DB session scope for scheduler jobs."""
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _seconds_until(hour: int, minute: int, weekday: Optional[int] = None) -> float:
    """
    Calculate delay in seconds until next scheduled UTC execution time.

    weekday: Monday=0 ... Sunday=6. When omitted, schedule next daily run.
    """
    now = datetime.now(timezone.utc)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if weekday is None:
        if target <= now:
            target += timedelta(days=1)
    else:
        days_ahead = (weekday - now.weekday()) % 7
        if days_ahead == 0 and target <= now:
            days_ahead = 7
        target = target + timedelta(days=days_ahead)

    return max((target - now).total_seconds(), 1.0)


def generate_daily_predictions() -> None:
    """Generate and persist risk predictions for all students."""
    logger.info("[SCHEDULER] Daily prediction job started.")
    with db_session_scope() as db:
        # Pre-load reference data (once per job)
        all_enrollments = (
            db.query(Enrollment, Course.name)
            .join(Course, Enrollment.course_id == Course.id, isouter=True)
            .all()
        )
        enrollment_map: dict = {}
        for enrollment, course_name in all_enrollments:
            enrollment_map.setdefault(enrollment.student_id, []).append(
                {
                    "course_name": course_name or "",
                    "content_completed": enrollment.content_completed,
                    "content_required": enrollment.content_required,
                    "content_required_w1w2": enrollment.content_required_w1w2,
                    "checklist_completed": enrollment.checklist_completed,
                    "quiz_completed": enrollment.quiz_completed,
                    "total_quiz_attempts": enrollment.total_quiz_attempts,
                    "discussion_posts_created": enrollment.discussion_posts_created,
                    "discussion_post_replies": enrollment.discussion_post_replies,
                    "discussion_posts_read": enrollment.discussion_posts_read,
                    "num_assignment_submissions": enrollment.num_assignment_submissions,
                    "total_time_spent_seconds": enrollment.total_time_spent_seconds,
                    "num_logins": enrollment.num_logins,
                }
            )

        graded_map: dict = {}
        for graded_component in db.query(GradedComponent).all():
            graded_map.setdefault(graded_component.student_id, []).append(
                {
                    "component_type": graded_component.component_type,
                    "component_number": graded_component.component_number,
                    "score": graded_component.score,
                    "max_score": graded_component.max_score,
                    "missed": graded_component.missed,
                    "course_name": graded_component.course_name,
                    "course_code": graded_component.course_code,
                }
            )

        exam_map: dict = {}
        for exam in db.query(ExamRecord).all():
            exam_map.setdefault(exam.student_id, []).append(
                {
                    "marks_obtained": exam.marks_obtained,
                    "marks_total": exam.marks_total,
                    "present": exam.present,
                }
            )

        # Keyset pagination: O(n) instead of O(n²) with OFFSET
        BATCH_SIZE = 100
        last_id = ""
        total_processed = 0
        created_predictions = 0
        created_snapshots = 0

        while True:
            batch = (
                db.query(Student)
                .filter(Student.is_active.is_(True), Student.id > last_id)
                .order_by(Student.id)
                .limit(BATCH_SIZE)
                .all()
            )
            if not batch:
                break
            last_id = batch[-1].id
            total_processed += len(batch)
            logger.info(f"Starting batch prediction for {len(batch)} students (batch ending at id={last_id})")
            processed = 0
            errors = 0

            for student in batch:
                try:
                    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                    wn = trimester_week_number(now_utc)
                    is_new = (student.old_new_student or "").lower() == "new"
                    program = "MSc" if "msc" in ((student.parent_department_name or "").lower()) else "BS"
                    current_week = get_current_week(settings.TRIMESTER_START_DATE)
                    features = FeatureEngineer.calculate_all_features(
                        enrollment_map.get(student.id, []),
                        graded_components=graded_map.get(student.id, []),
                        exam_records=exam_map.get(student.id, []),
                        is_new_student=is_new,
                        week_number=wn,
                    )
                    # ML-4: Add student_id and model_version for audit logging
                    features["student_id"] = student.id
                    features["model_version"] = settings.RISK_MODEL_VERSION
                    
                    risk_score = RiskScorer.calculate_risk_score(
                        features,
                        graded_components=graded_map.get(student.id, []) or [],
                        program=program,
                        current_week=current_week,
                    )
                    # Engagement is computed from observed behaviors (not the complement of risk):
                    # - content completion (60%)
                    # - attendance rate (40%)
                    # Stored as 0-1 in the DB.
                    attendance_rate = features.get("attendance_rate")
                    if attendance_rate is None:
                        attendance_rate = features.get("exam_attendance_rate", 0.0)
                    engagement_score_0_100 = (
                        float(features.get("content_completion_score", 0.0)) * 0.6
                        + float(attendance_rate or 0.0) * 0.4
                    )
                    engagement_score = max(0.0, min(1.0, engagement_score_0_100 / 100.0))

                    db.add(
                        Prediction(  # type: ignore[arg-type]
                            student_id=student.id,
                            risk_score=risk_score,  # 0-100 scale (DB-5)
                            engagement_score=engagement_score,
                            retention_likelihood=RiskScorer.get_retention_likelihood(risk_score),
                            model_version=settings.RISK_MODEL_VERSION,
                            prediction_timestamp=now_utc,
                        )
                    )
                    created_predictions += 1

                    # Upsert RiskSnapshot to avoid duplicates
                    snapshot_data = {
                        "student_id": student.id,
                        "risk_score": risk_score,  # 0-100 scale (DB-5)
                        "engagement_score": engagement_score,
                        "week_number": wn,
                        "semester_name": settings.CURRENT_SEMESTER_NAME,
                        "timestamp": now_utc,
                    }
                    stmt = pg_insert(RiskSnapshot).values(**snapshot_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['student_id', 'week_number', 'semester_name'],
                        set_={
                            'risk_score': snapshot_data['risk_score'],
                            'engagement_score': snapshot_data['engagement_score'],
                            'timestamp': snapshot_data['timestamp'],
                        }
                    )
                    db.execute(stmt)
                    created_snapshots += 1

                    # D5-2: Write features to EngineeredFeatures store for fast list queries
                    feat_record = db.query(EngineeredFeatures).filter(
                        EngineeredFeatures.student_id == student.id,
                        EngineeredFeatures.computation_date == datetime.utcnow().date()
                    ).first()
                    if feat_record:
                        feat_record.computation_date = datetime.utcnow().date()
                    else:
                        db.add(EngineeredFeatures(
                            student_id=student.id,
                            computation_date=datetime.utcnow().date(),
                        ))
                    processed += 1
                except Exception:
                    logger.exception(
                        "[SCHEDULER] Failed creating prediction for student_id=%s", student.id
                    )
                    errors += 1

    logger.info(
        "[SCHEDULER] Daily prediction job complete. students=%s predictions=%s snapshots=%s",
        total_processed,
        created_predictions,
        created_snapshots,
    )


def retrain_model_weekly() -> None:
    """Weekly retraining placeholder."""
    logger.info(
        "[SCHEDULER] Weekly retraining job skipped. No labelled training data available."
    )


def backup_sqlite_database():
    """D12-4: Automated SQLite backup job."""
    db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    if not db_path.exists():
        logger.warning("SQLite DB not found for backup", extra={"path": str(db_path)})
        return
    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    dest = backup_dir / f"sql_app_{timestamp}.db"
    shutil.copy2(db_path, dest)
    logger.info("SQLite backup created", extra={"backup": dest.name})

    # Retain only last 7 backups
    backups = sorted(backup_dir.glob("sql_app_*.db"))
    for old in backups[:-7]:
        old.unlink()
        logger.info("Old backup removed", extra={"backup": old.name})


def purge_old_records(db_session_factory) -> None:
    """
    GDPR Art. 5(1)(e) — data minimisation.
    Purge RiskSnapshots older than 12 months.
    Purge InterventionLogs older than 24 months.
    """
    with db_session_scope() as db:
        cutoff_snapshots = datetime.now(timezone.utc) - timedelta(days=365)
        cutoff_interventions = datetime.now(timezone.utc) - timedelta(days=730)

        deleted_snapshots = (
            db.query(RiskSnapshot)
            .filter(RiskSnapshot.timestamp < cutoff_snapshots)
            .delete(synchronize_session=False)
        )
        deleted_logs = (
            db.query(InterventionLog)
            .filter(InterventionLog.recommended_at < cutoff_interventions)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(
            "[SCHEDULER] GDPR purge complete",
            extra={
                "snapshots_deleted": deleted_snapshots,
                "intervention_logs_deleted": deleted_logs,
            }
        )


def cleanup_revoked_tokens() -> None:
    """
    SEC-4: Purge expired revoked tokens from the blocklist.
    Runs nightly to prevent the revoked_tokens table from growing indefinitely.
    """
    with db_session_scope() as db:
        deleted_count = purge_expired_revoked_tokens(db)
        logger.info(
            "[SCHEDULER] Token cleanup complete",
            extra={"revoked_tokens_deleted": deleted_count},
        )


class SchedulerService:
    """Lifespan-friendly async scheduler."""

    def __init__(self) -> None:
        self._daily_task: Optional[asyncio.Task] = None
        self._weekly_task: Optional[asyncio.Task] = None
        self._monthly_purge_task: Optional[asyncio.Task] = None
        self._backup_task: Optional[asyncio.Task] = None
        self._token_cleanup_task: Optional[asyncio.Task] = None
        self._started = False
        self._last_daily_run_at: Optional[datetime] = None
        self._last_daily_success_at: Optional[datetime] = None
        self._last_daily_error: Optional[str] = None
        self._last_weekly_run_at: Optional[datetime] = None
        self._last_weekly_success_at: Optional[datetime] = None
        self._last_weekly_error: Optional[str] = None
        self._last_purge_run_at: Optional[datetime] = None
        self._last_purge_success_at: Optional[datetime] = None
        self._last_purge_error: Optional[str] = None
        self._last_backup_run_at: Optional[datetime] = None
        self._last_backup_success_at: Optional[datetime] = None
        self._last_backup_error: Optional[str] = None
        self._last_token_cleanup_run_at: Optional[datetime] = None
        self._last_token_cleanup_success_at: Optional[datetime] = None
        self._last_token_cleanup_error: Optional[str] = None

    async def _run_daily_job_once(self, reason: str) -> None:
        # Skip if previous job still running (CROSS-4)
        if _prediction_job_lock.locked():
            logger.warning("[SCHEDULER] Daily prediction job skipped — previous run still in progress")
            return
        async with _prediction_job_lock:
            self._last_daily_run_at = datetime.now(timezone.utc)
            logger.info("[SCHEDULER] Triggering daily prediction job (%s).", reason)
            try:
                await asyncio.to_thread(generate_daily_predictions)
                self._last_daily_success_at = datetime.now(timezone.utc)
                self._last_daily_error = None
                logger.info("[SCHEDULER] Daily prediction job finished successfully.")
            except Exception as exc:
                self._last_daily_error = str(exc)
                logger.exception("[SCHEDULER] Daily prediction job failed (%s).", reason)

    async def _run_weekly_job_once(self, reason: str) -> None:
        self._last_weekly_run_at = datetime.now(timezone.utc)
        logger.info("[SCHEDULER] Triggering weekly retrain job (%s).", reason)
        try:
            await asyncio.to_thread(retrain_model_weekly)
            self._last_weekly_success_at = datetime.now(timezone.utc)
            self._last_weekly_error = None
            logger.info("[SCHEDULER] Weekly retrain job finished successfully.")
        except Exception as exc:
            self._last_weekly_error = str(exc)
            logger.exception("[SCHEDULER] Weekly retrain job failed (%s).", reason)

    async def _run_daily_loop(self) -> None:
        while True:
            await asyncio.sleep(_seconds_until(hour=3, minute=0))
            await self._run_daily_job_once(reason="scheduled-03:00-utc")

    async def _run_weekly_loop(self) -> None:
        while True:
            await asyncio.sleep(_seconds_until(hour=4, minute=0, weekday=6))
            await self._run_weekly_job_once(reason="scheduled-sunday-04:00-utc")

    async def _run_monthly_purge_once(self, reason: str) -> None:
        """Run GDPR data minimisation purge."""
        self._last_purge_run_at = datetime.now(timezone.utc)
        logger.info("[SCHEDULER] Triggering monthly GDPR purge job (%s).", reason)
        try:
            await asyncio.to_thread(purge_old_records, SessionLocal)
            self._last_purge_success_at = datetime.now(timezone.utc)
            self._last_purge_error = None
            logger.info("[SCHEDULER] Monthly GDPR purge job finished successfully.")
        except Exception as exc:
            self._last_purge_error = str(exc)
            logger.exception("[SCHEDULER] Monthly GDPR purge job failed (%s).", reason)

    async def _run_monthly_purge_loop(self) -> None:
        """Run on 1st of each month at 02:00 UTC."""
        while True:
            await asyncio.sleep(_seconds_until(hour=2, minute=0, weekday=None))
            await self._run_monthly_purge_once(reason="scheduled-monthly-02:00-utc")

    async def _run_backup_once(self, reason: str) -> None:
        """Run SQLite backup job."""
        self._last_backup_run_at = datetime.now(timezone.utc)
        logger.info("[SCHEDULER] Triggering backup job (%s).", reason)
        try:
            await asyncio.to_thread(backup_sqlite_database)
            self._last_backup_success_at = datetime.now(timezone.utc)
            self._last_backup_error = None
            logger.info("[SCHEDULER] Backup job finished successfully.")
        except Exception as exc:
            self._last_backup_error = str(exc)
            logger.exception("[SCHEDULER] Backup job failed (%s).", reason)

    async def _run_backup_loop(self) -> None:
        """Run daily at 03:00 UTC."""
        while True:
            await asyncio.sleep(_seconds_until(hour=3, minute=0))
            await self._run_backup_once(reason="scheduled-03:00-utc")

    async def _run_token_cleanup_once(self, reason: str) -> None:
        """Run revoked token cleanup job."""
        self._last_token_cleanup_run_at = datetime.now(timezone.utc)
        logger.info("[SCHEDULER] Triggering token cleanup job (%s).", reason)
        try:
            await asyncio.to_thread(cleanup_revoked_tokens)
            self._last_token_cleanup_success_at = datetime.now(timezone.utc)
            self._last_token_cleanup_error = None
            logger.info("[SCHEDULER] Token cleanup job finished successfully.")
        except Exception as exc:
            self._last_token_cleanup_error = str(exc)
            logger.exception("[SCHEDULER] Token cleanup job failed (%s).", reason)

    async def _run_token_cleanup_loop(self) -> None:
        """Run daily at 04:00 UTC (after backup)."""
        while True:
            await asyncio.sleep(_seconds_until(hour=4, minute=0))
            await self._run_token_cleanup_once(reason="scheduled-04:00-utc")

    async def start(self, run_daily_on_startup: bool = True) -> None:
        if self._started:
            logger.warning("[SCHEDULER] Start requested, but scheduler is already running.")
            return

        self._daily_task = asyncio.create_task(self._run_daily_loop(), name="scheduler-daily")
        self._weekly_task = asyncio.create_task(
            self._run_weekly_loop(), name="scheduler-weekly"
        )
        self._monthly_purge_task = asyncio.create_task(
            self._run_monthly_purge_loop(), name="scheduler-monthly-purge"
        )
        self._backup_task = asyncio.create_task(
            self._run_backup_loop(), name="scheduler-backup"
        )
        self._token_cleanup_task = asyncio.create_task(
            self._run_token_cleanup_loop(), name="scheduler-token-cleanup"
        )
        self._started = True
        logger.info(
            "[SCHEDULER] Started. Daily job: 03:00 UTC. Weekly job: Sunday 04:00 UTC. "
            "Monthly purge: 1st at 02:00 UTC. Daily backup: 03:00 UTC. "
            "Token cleanup: 04:00 UTC."
        )

        # Ensure predictions are generated in environments where the app may restart
        # after the daily schedule window has passed.
        if run_daily_on_startup:
            asyncio.create_task(
                self._run_daily_job_once(reason="startup-bootstrap"),
                name="scheduler-daily-startup-bootstrap",
            )

    async def stop(self) -> None:
        if not self._started:
            return

        tasks = [
            task for task in (self._daily_task, self._weekly_task, self._monthly_purge_task, self._backup_task, self._token_cleanup_task)
            if task is not None
        ]
        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._daily_task = None
        self._weekly_task = None
        self._backup_task = None
        self._token_cleanup_task = None
        self._started = False
        logger.info("[SCHEDULER] Stopped.")

    def get_status(self) -> dict:
        """Expose scheduler/job runtime status for observability."""
        return {
            "started": self._started,
            "daily": {
                "last_run_at": self._last_daily_run_at.isoformat() if self._last_daily_run_at else None,
                "last_success_at": self._last_daily_success_at.isoformat() if self._last_daily_success_at else None,
                "last_error": self._last_daily_error,
            },
            "weekly": {
                "last_run_at": self._last_weekly_run_at.isoformat() if self._last_weekly_run_at else None,
                "last_success_at": self._last_weekly_success_at.isoformat() if self._last_weekly_success_at else None,
                "last_error": self._last_weekly_error,
            },
            "monthly_purge": {
                "last_run_at": self._last_purge_run_at.isoformat() if self._last_purge_run_at else None,
                "last_success_at": self._last_purge_success_at.isoformat() if self._last_purge_success_at else None,
                "last_error": self._last_purge_error,
            },
            "backup": {
                "last_run_at": self._last_backup_run_at.isoformat() if self._last_backup_run_at else None,
                "last_success_at": self._last_backup_success_at.isoformat() if self._last_backup_success_at else None,
                "last_error": self._last_backup_error,
            },
            "token_cleanup": {
                "last_run_at": self._last_token_cleanup_run_at.isoformat() if self._last_token_cleanup_run_at else None,
                "last_success_at": self._last_token_cleanup_success_at.isoformat() if self._last_token_cleanup_success_at else None,
                "last_error": self._last_token_cleanup_error,
            },
        }


scheduler_service = SchedulerService()
