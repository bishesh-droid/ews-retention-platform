from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from backend.database import Student, Prediction
from backend.api import deps
from backend.utils.api import success_response

router = APIRouter()

@router.get("/risk-summary")
def get_retention_risk_summary(
    current_user: deps.User = Depends(deps.require_role(["Retention Team"])),
    db: Session = Depends(deps.get_db)
):
    """
    High-level risk summary for the retention team.
    """
    high_risk_count = db.query(Prediction).filter(Prediction.risk_score >= 0.7).count()
    data = {
        "high_risk_students": high_risk_count,
        "total_active_students": db.query(Student).filter(Student.is_active == True).count(),
    }
    return success_response(data, message="Retention risk summary")

@router.get("/at-risk-students")
def get_at_risk_students(
    limit: int = 10,
    current_user: deps.User = Depends(deps.require_role(["Retention Team"])),
    db: Session = Depends(deps.get_db)
):
    """
    List top at-risk students for intervention.
    """
    students = db.query(Prediction).order_by(Prediction.risk_score.desc()).limit(limit).all()
    data = {
        "students": students,
        "limit": limit,
    }
    return success_response(
        data,
        message="At-risk students",
        meta={"pagination": {"limit": limit, "returned": len(students)}},
    )
