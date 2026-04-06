"""
Feedback Loop API Endpoints
Tracks student responses to interventions and measures effectiveness.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from backend.api.deps import get_db, get_current_user
from backend.database import StudentResponse, Intervention
from fastapi import Depends

router = APIRouter(
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_current_user)],
)


class StudentResponseCreate(BaseModel):
    student_id: str
    intervention_id: int
    responded: bool = False
    response_time_hours: Optional[float] = None
    behavioral_change_detected: bool = False
    engagement_change_7days: Optional[float] = None
    attendance_change_7days: Optional[float] = None
    grade_change_next_assignment: Optional[float] = None
    retained: Optional[bool] = None


@router.post("/response", status_code=201)
def record_student_response(response: StudentResponseCreate, db: Session = Depends(get_db)):
    """Record student response to an intervention."""
    intervention = db.query(Intervention).filter(Intervention.id == response.intervention_id).first()
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")

    db_response = StudentResponse(
        student_id=response.student_id,
        intervention_id=response.intervention_id,
        responded=response.responded,
        response_time_hours=response.response_time_hours,
        behavioral_change_detected=response.behavioral_change_detected,
        engagement_change_7days=response.engagement_change_7days,
        attendance_change_7days=response.attendance_change_7days,
        grade_change_next_assignment=response.grade_change_next_assignment,
        retained=response.retained,
        recorded_at=datetime.utcnow()
    )
    db.add(db_response)

    if db_response.behavioral_change_detected:
        changes = [
            response.engagement_change_7days or 0,
            response.attendance_change_7days or 0,
            (response.grade_change_next_assignment or 0) / 100.0,
        ]
        effectiveness = sum(c for c in changes if c > 0) / 3.0
        intervention.effectiveness_score = max(0, min(1.0, effectiveness))
    else:
        intervention.effectiveness_score = 0.0

    db.commit()
    db.refresh(db_response)

    return {
        "status": "success",
        "response_id": db_response.id,
        "intervention_effectiveness": intervention.effectiveness_score,
        "message": "Student response recorded",
    }


@router.get("/effectiveness")
def get_intervention_effectiveness(
    threshold_category: Optional[str] = None,
    days_lookback: int = 90,
    db: Session = Depends(get_db)
):
    """Get intervention effectiveness metrics."""
    cutoff_date = datetime.utcnow() - timedelta(days=days_lookback)

    total_interventions = db.query(Intervention).filter(
        Intervention.date >= cutoff_date.date()
    ).count()

    total_responses = db.query(StudentResponse).filter(
        StudentResponse.recorded_at >= cutoff_date
    ).count()

    if total_interventions == 0:
        return {
            "total_interventions": 0,
            "message": "No interventions found in this period",
        }

    response_rate = total_responses / max(total_interventions, 1)

    return {
        "period_days": days_lookback,
        "total_interventions": total_interventions,
        "total_responses": total_responses,
        "response_rate": round(response_rate, 3),
        "overall_effectiveness": 0.0,
        "behavioral_change_rate": 0.0,
        "average_response_time_hours": 0.0,
        "by_threshold_category": {},
    }


@router.get("/{student_id}/history")
def get_student_feedback_history(student_id: str, db: Session = Depends(get_db)):
    """Get feedback history for a specific student."""
    responses = db.query(StudentResponse).filter(
        StudentResponse.student_id == student_id
    ).order_by(StudentResponse.recorded_at.desc()).all()

    history = []
    for response in responses:
        intervention = db.query(Intervention).filter(
            Intervention.id == response.intervention_id
        ).first()

        history.append({
            "response_id": response.id,
            "intervention_id": response.intervention_id,
            "intervention_date": intervention.date if intervention else None,
            "intervention_type": intervention.threshold_category if intervention else None,
            "responded": response.responded,
            "response_time_hours": response.response_time_hours,
            "behavioral_change_detected": response.behavioral_change_detected,
            "engagement_change": response.engagement_change_7days,
            "attendance_change": response.attendance_change_7days,
            "grade_change": response.grade_change_next_assignment,
            "retained": response.retained,
            "recorded_at": response.recorded_at,
        })

    return {
        "student_id": student_id,
        "total_responses": len(history),
        "history": history,
    }
