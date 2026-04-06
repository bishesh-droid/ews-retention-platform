"""
Predictions API Routes for EWS Retention Platform.

Provides risk predictions calculated from real engagement data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_current_user
from backend.services.student_service import StudentService
from backend.database import Student
from backend.utils.api import success_response
from fastapi import Depends

router = APIRouter(
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_current_user)],
)


@router.get("/batch")
def get_all_predictions(
    include_decisions: bool = Query(False, description="Include intervention recommendations"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db)
):
    """Get batch predictions for all students."""
    students = StudentService.get_all_students(db, skip=0, limit=limit)

    predictions = []
    for s in students:
        pred = StudentService.build_prediction_payload(s)

        if include_decisions:
            pred["intervention_recommendation"] = StudentService.build_intervention_recommendation(
                s["risk_score"]
            )

        predictions.append(pred)

    payload = {
        "total_students": len(predictions),
        "predictions": predictions,
    }
    return success_response(payload)


@router.get("/{student_id}")
def get_student_prediction(
    student_id: str,
    include_decisions: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get prediction for a specific student."""
    student = StudentService.get_student_by_id(db, student_id)

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    risk = student["risk_score"]
    response = StudentService.build_prediction_payload(student)

    if include_decisions:
        response["intervention_recommendation"] = StudentService.build_intervention_recommendation(
            risk
        )

    return success_response(response)
