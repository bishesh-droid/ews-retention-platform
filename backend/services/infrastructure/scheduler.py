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
from backend.database.models.prediction import Prediction
from backend.database.models.student import Student
from backend.database.session import SessionLocal
from backend.services.feature_engineering import FeatureEngineer
from backend.services.risk_scoring import RiskScorer

logger = logging.getLogger(__name__)


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
        students = db.query(Student).all()

        all_enrollments = (
            db.query(Enrollment, Course.name)
            .join(Course, Enrollment.course_id == Course.id, isouter=True)
            .all()
        )
        enrollment_map = {}
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

        graded_map = {}
        for graded_component in db.query(GradedComponent).all():
            graded_map.setdefault(graded_component.student_id, []).append(
                {
                    "component_type": graded_component.component_type,
                    "score": graded_component.score,
                    "max_score": graded_component.max_score,
                    "missed": graded_component.missed,
                }
            )

        exam_map = {}
        for exam in db.query(ExamRecord).all():
            exam_map.setdefault(exam.student_id, []).append(
                {
                    "marks_obtained": exam.marks_obtained,
                    "marks_total": exam.marks_total,
                    "present": exam.present,
                }
            )

        created_predictions = 0
        created_snapshots = 0
        for student in students:
            try:
                features = FeatureEngineer.calculate_all_features(
                    enrollment_map.get(student.id, []),
                    graded_components=graded_map.get(student.id, []),
                    exam_records=exam_map.get(student.id, []),
                )
                risk_score = RiskScorer.calculate_risk_score(features)
                now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

                db.add(
                    Prediction(
                        student_id=student.id,
                        risk_score=risk_score / 100.0,
                        engagement_score=(100.0 - risk_score) / 100.0,
                        retention_likelihood=RiskScorer.get_retention_likelihood(risk_score),
                        model_version="rule-based-v1",
                        prediction_timestamp=now_utc,
                    )
                )
                created_predictions += 1

                db.add(
                    RiskSnapshot(
                        student_id=student.id,
                        risk_score=risk_score / 100.0,
                        engagement_score=(100.0 - risk_score) / 100.0,
                        timestamp=now_utc,
                    )
                )
                created_snapshots += 1
            except Exception:
                logger.exception(
                    "[SCHEDULER] Failed creating prediction for student_id=%s", student.id
                )

    logger.info(
        "[SCHEDULER] Daily prediction job complete. students=%s predictions=%s snapshots=%s",
        len(students),
        created_predictions,
        created_snapshots,
    )


def retrain_model_weekly() -> None:
    """Weekly retraining placeholder."""
    logger.info(
        "[SCHEDULER] Weekly retraining job skipped. No labelled training data available."
    )


class SchedulerService:
    """Lifespan-friendly async scheduler."""

    def __init__(self) -> None:
        self._daily_task: Optional[asyncio.Task] = None
        self._weekly_task: Optional[asyncio.Task] = None
        self._started = False

    async def _run_daily_loop(self) -> None:
        while True:
            await asyncio.sleep(_seconds_until(hour=3, minute=0))
            try:
                await asyncio.to_thread(generate_daily_predictions)
            except Exception:
                logger.exception("[SCHEDULER] Daily job crashed.")

    async def _run_weekly_loop(self) -> None:
        while True:
            await asyncio.sleep(_seconds_until(hour=4, minute=0, weekday=6))
            try:
                await asyncio.to_thread(retrain_model_weekly)
            except Exception:
                logger.exception("[SCHEDULER] Weekly job crashed.")

    async def start(self) -> None:
        if self._started:
            logger.warning("[SCHEDULER] Start requested, but scheduler is already running.")
            return

        self._daily_task = asyncio.create_task(self._run_daily_loop(), name="scheduler-daily")
        self._weekly_task = asyncio.create_task(
            self._run_weekly_loop(), name="scheduler-weekly"
        )
        self._started = True
        logger.info(
            "[SCHEDULER] Started. Daily job: 03:00 UTC. Weekly job: Sunday 04:00 UTC."
        )

    async def stop(self) -> None:
        if not self._started:
            return

        tasks = [task for task in (self._daily_task, self._weekly_task) if task is not None]
        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._daily_task = None
        self._weekly_task = None
        self._started = False
        logger.info("[SCHEDULER] Stopped.")


scheduler_service = SchedulerService()
