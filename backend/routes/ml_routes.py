"""
ML prediction routes
--------------------
Thin HTTP layer delegating all prediction logic to services.
ML inference is executed off the main event loop via asyncio.to_thread
and is protected by a timeout so the server remains responsive.

All endpoints require a valid JWT.  Batch/cohort endpoints additionally
require a staff-level role (faculty / admin / retention team).
"""

from typing import Dict, List
import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.api.deps import get_current_user, get_db_async, require_role
from backend.database.models.user import User
from backend.services.ml_service import ml_service
from backend.services.student_service import StudentService
from backend.database.models.prediction import Prediction
from backend.database.models.student import Student
from backend.utils.api import success_response

router = APIRouter()

PREDICTION_TIMEOUT_SECONDS = 10.0
_STAFF_ROLES = ["faculty", "admin", "retention team"]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BatchPredictionRequest(BaseModel):
    student_ids: List[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/predict/{student_id}")
async def predict_student_risk(
    student_id: str,
    db: Session = Depends(get_db_async),
    _user: User = Depends(require_role(_STAFF_ROLES)),
):
    """
    Compute and return a dropout-risk prediction for a single student.
    Staff only.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    enrollments = StudentService._get_enrollment_dicts(db, student_id)
    graded = StudentService._get_graded_components(db, student_id)
    exams = StudentService._get_exam_records(db, student_id)

    try:
        result = await asyncio.wait_for(
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

    if result.get("prediction_error") and "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])

    # Persist prediction in this async endpoint thread/session.
    # (We deliberately do not pass the SQLAlchemy session into `to_thread`.)
    ml_service.persist_prediction(
        db=db,
        student_id=student_id,
        risk_score=float(result["risk_score"]),
        features=result.get("features") or {},
    )
    db.commit()

    return success_response(result, message="Prediction computed")


@router.post("/predict-batch")
async def predict_student_batch(
    request: BatchPredictionRequest,
    db: Session = Depends(get_db_async),
    _user: User = Depends(require_role(_STAFF_ROLES)),
):
    """
    Compute risk predictions for multiple students. Staff only.
    """
    results = []
    for student_id in request.student_ids:
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            continue
        enrollments = StudentService._get_enrollment_dicts(db, student_id)
        graded = StudentService._get_graded_components(db, student_id)
        exams = StudentService._get_exam_records(db, student_id)

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
    db: Session = Depends(get_db_async),
    _user: User = Depends(require_role(_STAFF_ROLES)),
) -> Dict:
    """
    Aggregate risk metrics for the current cohort. Staff only.
    """
    subq = (
        db.query(Prediction.student_id, Prediction.risk_score)
        .order_by(Prediction.student_id, desc(Prediction.prediction_timestamp))
        .distinct(Prediction.student_id)
        .all()
    )

    if not subq:
        total_students = db.query(Student).count()
        return success_response(
            {
                "average_risk": None,
                "high_risk_count": 0,
                "critical_risk_count": 0,
                "total_students": total_students,
                "note": "No predictions stored yet. Run /ml/predict/{id} first.",
            }
        )

    scores = []
    for _, raw_score in subq:
        if raw_score is None:
            continue
        s = float(raw_score)
        if s <= 1.0:
            s *= 100.0
        scores.append(s)

    if not scores:
        return success_response({"average_risk": None, "total_students": len(subq)})

    avg = round(sum(scores) / len(scores), 2)
    high_count = sum(1 for s in scores if s >= 70.0)
    critical_count = sum(1 for s in scores if s >= 85.0)

    return success_response(
        {
            "average_risk": avg,
            "high_risk_count": high_count,
            "critical_risk_count": critical_count,
            "total_students": len(scores),
        }
    )


@router.get("/trend-analysis")
async def get_trend_analysis(
    weeks: int = 8,
    db: Session = Depends(get_db_async),
    _user: User = Depends(require_role(_STAFF_ROLES)),
) -> Dict:
    """
    Weekly average risk score trend over the last N weeks. Staff only.
    """
    start = datetime.utcnow() - timedelta(weeks=weeks)
    preds = (
        db.query(Prediction)
        .filter(Prediction.prediction_timestamp >= start)
        .order_by(Prediction.prediction_timestamp.asc())
        .all()
    )

    if not preds:
        return success_response(
            {"weekly_trend": [], "note": "No predictions stored in the requested window."}
        )

    buckets: dict = {}
    for p in preds:
        if p.prediction_timestamp is None or p.risk_score is None:
            continue
        iso_year, iso_week, _ = p.prediction_timestamp.isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        s = float(p.risk_score)
        if s <= 1.0:
            s *= 100.0
        buckets.setdefault(key, []).append(s)

    trend = [
        {"week": k, "avg_risk": round(sum(v) / len(v), 2)}
        for k, v in sorted(buckets.items())
    ]

    return success_response({"weekly_trend": trend})


@router.get("/model-status")
async def get_model_status(
    _user: User = Depends(get_current_user),
) -> Dict:
    """Report the current ML pipeline status. Any authenticated user."""
    stats = ml_service.get_runtime_stats()
    return success_response(stats, message="ML pipeline status")
