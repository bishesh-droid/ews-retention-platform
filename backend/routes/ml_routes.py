"""
ML prediction routes
--------------------
Thin HTTP layer delegating all prediction logic to services.

TODO: No trained ML model exists yet. All predictions currently use
rule-based scoring (RiskScorer). This module is reserved for future ML.
See backend/ml/training/calibrate.py for the path to real ML.

ML inference (when available) will be executed off the main event loop
via asyncio.to_thread and protected by a timeout.

All endpoints require a valid JWT.  Batch/cohort endpoints additionally
require a staff-level role (faculty / admin / retention team).
"""

from typing import Dict, List
import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_, case, select

from backend.api.deps import get_current_user_async, get_db_async, require_role
from backend.application.student.student_application_service import (
    StudentApplicationService,
)
from backend.core.constants import Role
from backend.core.rate_limiting import limiter
from backend.database.models.user import User
from backend.services.ml_service import ml_service
from backend.services.student_service import StudentService
from backend.database.models.prediction import Prediction
from backend.database.models.student import Student
from backend.utils.api import success_response

router = APIRouter()

PREDICTION_TIMEOUT_SECONDS = 10.0
_STAFF_ROLES = Role.staff_roles()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class BatchPredictionRequest(BaseModel):
    student_ids: List[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/predict/{student_id}")
@limiter.limit("30/minute")
async def predict_student_risk(
    request: Request,
    student_id: str,
    db: AsyncSession = Depends(get_db_async),
    _user: User = Depends(require_role(_STAFF_ROLES)),
):
    """
    Compute and return a dropout-risk prediction for a single student.
    Staff only.
    """
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Run sync service calls in thread pool to avoid blocking event loop
    enrollments = await asyncio.to_thread(
        StudentService._get_enrollment_dicts, db, student_id  # type: ignore[arg-type]
    )
    graded = await asyncio.to_thread(
        StudentService._get_graded_components, db, student_id  # type: ignore[arg-type]
    )
    exams = await asyncio.to_thread(StudentService._get_exam_records, db, student_id)  # type: ignore[arg-type]

    try:
        pred_result: dict = await asyncio.wait_for(
            asyncio.to_thread(
                ml_service.predict_student,
                student_id,
                enrollments,
                graded,
                exams,
            ),
            timeout=PREDICTION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Prediction timed out")

    if pred_result.get("prediction_error") and "error" in pred_result:
        raise HTTPException(status_code=500, detail=pred_result["error"])

    # Persist prediction in this async endpoint thread/session.
    # (We deliberately do not pass the SQLAlchemy session into `to_thread`.)
    ml_service.persist_prediction(
        db=db,  # type: ignore[arg-type]
        student_id=student_id,
        risk_score=float(pred_result["risk_score"]),
        features=pred_result.get("features") or {},
    )
    await db.commit()

    return success_response(pred_result, message="Prediction computed")


@router.post("/predict-batch")
async def predict_student_batch(
    request: BatchPredictionRequest,
    db: AsyncSession = Depends(get_db_async),
    _user: User = Depends(require_role(_STAFF_ROLES)),
):
    """
    Compute risk predictions for multiple students. Staff only.
    """
    unique_ids = list(dict.fromkeys(request.student_ids))
    if not unique_ids:
        return success_response([], message="0 predictions computed")

    result = await db.execute(select(Student.id).where(Student.id.in_(unique_ids)))
    existing_ids = {sid for (sid,) in result.all()}
    target_ids = [sid for sid in unique_ids if sid in existing_ids]

    # Run sync service calls in thread pool to avoid blocking event loop
    enrollment_map = await asyncio.to_thread(
        StudentService._fetch_enrollments_map, db, target_ids  # type: ignore[arg-type]
    )
    graded_map = await asyncio.to_thread(
        StudentService._fetch_graded_map, db, target_ids  # type: ignore[arg-type]
    )
    exam_map = await asyncio.to_thread(StudentService._fetch_exam_map, db, target_ids)  # type: ignore[arg-type]

    results = []
    for student_id in target_ids:
        enrollments = enrollment_map.get(student_id, [])
        graded = graded_map.get(student_id, [])
        exams = exam_map.get(student_id, [])

        try:
            pred = await asyncio.wait_for(
                asyncio.to_thread(
                    ml_service.predict_student,
                    student_id,
                    enrollments,
                    graded,
                    exams,
                ),
                timeout=PREDICTION_TIMEOUT_SECONDS,
            )
            results.append(pred)
        except asyncio.TimeoutError:
            results.append({"student_id": student_id, "error": "timeout"})
        except Exception as exc:
            results.append({"student_id": student_id, "error": str(exc)})

    return success_response(results, message=f"{len(results)} predictions computed")


@router.get("/cohort-risk")
async def get_cohort_risk(
    db: AsyncSession = Depends(get_db_async),
    _user: User = Depends(require_role(_STAFF_ROLES)),
) -> Dict:
    """
    Aggregate risk metrics for the current cohort. Staff only.
    """
    # Build subquery for latest predictions per student
    latest_subq = (
        select(
            Prediction.student_id.label("student_id"),
            func.max(Prediction.prediction_timestamp).label("max_ts"),
        )
        .group_by(Prediction.student_id)
        .subquery()
    )

    stmt = select(
        func.count(Prediction.student_id).label("n"),
        func.avg(Prediction.risk_score).label("avg_risk"),
        func.sum(
            case(
                (Prediction.risk_score >= 70.0, 1),
                else_=0,
            )
        ).label("high_count"),
        func.sum(
            case(
                (Prediction.risk_score >= 85.0, 1),
                else_=0,
            )
        ).label("critical_count"),
    ).join(
        latest_subq,
        and_(
            Prediction.student_id == latest_subq.c.student_id,
            Prediction.prediction_timestamp == latest_subq.c.max_ts,
        ),
    )
    result = await db.execute(stmt)
    agg = result.one()

    # Calculate engagement patterns for the cohort
    engagement_patterns = StudentApplicationService.get_cohort_engagement_patterns(
        db, current_user=_user  # type: ignore[arg-type]
    )

    if not agg.n:
        count_result = await db.execute(select(func.count(Student.id)))
        total_students = count_result.scalar()
        return success_response(
            {
                "average_risk": None,
                "high_risk_count": 0,
                "critical_risk_count": 0,
                "total_students": total_students,
                "engagement_patterns": engagement_patterns,
                "note": "No predictions stored yet. Run /ml/predict/{id} first.",
            }
        )

    return success_response(
        {
            "average_risk": round(float(agg.avg_risk or 0.0), 2),
            "high_risk_count": int(agg.high_count or 0),
            "critical_risk_count": int(agg.critical_count or 0),
            "total_students": int(agg.n or 0),
            "engagement_patterns": engagement_patterns,
        }
    )


@router.get("/trend-analysis")
async def get_trend_analysis(
    weeks: int = 8,
    db: AsyncSession = Depends(get_db_async),
    _user: User = Depends(require_role(_STAFF_ROLES)),
) -> Dict:
    """
    Weekly average risk score trend over the last N weeks. Staff only.
    """
    start = datetime.utcnow() - timedelta(weeks=weeks)
    # PostgreSQL-compatible week key formatting (ISO week)
    week_key = func.to_char(Prediction.prediction_timestamp, "IYYY-IW")
    stmt = (
        select(
            week_key.label("week"),
            func.avg(Prediction.risk_score).label("avg_risk"),
        )
        .where(Prediction.prediction_timestamp >= start)
        .group_by(week_key)
        .order_by(week_key.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return success_response(
            {
                "weekly_trend": [],
                "note": "No predictions stored in the requested window.",
            }
        )
    trend = [{"week": w, "avg_risk": round(float(avg or 0.0), 2)} for w, avg in rows]

    return success_response({"weekly_trend": trend})


@router.get("/model-status")
async def get_model_status(
    _user: User = Depends(get_current_user_async),
) -> Dict:
    """Report the current ML pipeline status. Any authenticated user."""
    stats = ml_service.get_runtime_stats()
    return success_response(stats, message="ML pipeline status")


@router.get("/model-info")
async def get_model_info(
    _user: User = Depends(get_current_user_async),
) -> Dict:
    """
    Get detailed information about the loaded ML model.

    Returns:
        - model_type: Type of model (XGBoostClassifier or "none")
        - model_loaded: Whether a model is currently loaded
        - features: List of 12 DB-derived feature names used by the model
        - n_features: Number of features (12)
        - metrics: Model performance metrics (AUC-ROC, precision, recall, F1)
        - training_info: Training metadata (samples, class distribution, CV folds)
        - feature_importance: Ranked feature importance scores
    """
    info = ml_service.get_model_info()
    return success_response(info, message="Model information")
