"""
Predictions API Routes for EWS Retention Platform.

Provides risk predictions calculated from real engagement data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import (
    get_db,
    get_current_user,
    require_resource_ownership,
    require_role,
)
from backend.core.constants import Role
from backend.services.student_service import StudentService
from backend.utils.api import success_response

router = APIRouter(
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_current_user)],
)


@router.get("/batch")
def get_all_predictions(
    include_decisions: bool = Query(
        False, description="Include intervention recommendations"
    ),
    # TODO: Bulk exports >500 should use async background task returning a download URL
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user=Depends(require_role([Role.ADMIN, Role.FACULTY, Role.RETENTION_TEAM])),
):
    """Get batch predictions for all students."""
    students = StudentService.get_all_students(db, skip=0, limit=limit)

    predictions = []
    for s in students:
        pred = StudentService.build_prediction_payload(s)

        if include_decisions:
            pred["intervention_recommendation"] = (
                StudentService.build_intervention_recommendation(s["risk_score"])
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
    db: Session = Depends(get_db),
    current_user=Depends(require_resource_ownership("student_id")),
):
    """
    Get prediction for a specific student.

    FERPA-compliant: Only staff (faculty/admin) or the student themselves
    can access this endpoint.
    """
    student = StudentService.get_student_by_id(db, student_id)

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    risk = student["risk_score"]
    response = StudentService.build_prediction_payload(student)

    if include_decisions:
        response["intervention_recommendation"] = (
            StudentService.build_intervention_recommendation(risk)
        )

    return success_response(response)
