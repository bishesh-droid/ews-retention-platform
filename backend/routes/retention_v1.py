from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import Student, Prediction
from backend.api import deps
from backend.core.constants import Role
from backend.schemas.common import APIResponse
from backend.utils.api import success_response

router = APIRouter()


@router.get("/risk-summary", response_model=APIResponse)
def get_retention_risk_summary(
    current_user: deps.User = Depends(deps.require_role([Role.RETENTION_TEAM])),
    db: Session = Depends(deps.get_db),
):
    """
    High-level risk summary for the retention team.
    """
    high_risk_count = db.query(Prediction).filter(Prediction.risk_score >= 70.0).count()
    data = {
        "high_risk_students": high_risk_count,
        "total_active_students": db.query(Student)
        .filter(Student.is_active.is_(True))
        .count(),
    }
    return success_response(data, message="Retention risk summary")


@router.get("/at-risk-students", response_model=APIResponse)
def get_at_risk_students(
    limit: int = 10,
    current_user: deps.User = Depends(deps.require_role([Role.RETENTION_TEAM])),
    db: Session = Depends(deps.get_db),
):
    """
    List top at-risk students for intervention.
    """
    students = (
        db.query(Prediction).order_by(Prediction.risk_score.desc()).limit(limit).all()
    )
    data = {
        "students": students,
        "limit": limit,
    }
    return success_response(
        data,
        message="At-risk students",
        meta={"pagination": {"limit": limit, "returned": len(students)}},
    )
