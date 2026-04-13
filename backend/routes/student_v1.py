from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import Student, Goal, RiskSnapshot
from backend.api import deps
from backend.core.constants import Role
from backend.schemas.common import APIResponse
from backend.utils.api import success_response

router = APIRouter()


@router.get("/me", response_model=APIResponse)
def get_my_profile(
    current_user: deps.User = Depends(deps.require_role([Role.STUDENT])),
    db: Session = Depends(deps.get_db)
):
    """
    Get current student's profile and disengagement risks.
    """
    student = db.query(Student).filter(Student.id == current_user.email).first()
    return success_response(student, message="Student profile")


@router.get("/goals", response_model=APIResponse)
def get_my_goals(
    current_user: deps.User = Depends(deps.require_role([Role.STUDENT])),
    db: Session = Depends(deps.get_db)
):
    """
    Get current student's active goals.
    """
    goals = db.query(Goal).filter(Goal.student_id == current_user.email).all()
    return success_response(
        goals,
        message="Student goals",
        meta={"pagination": {"total": len(goals)}},
    )


@router.get("/risk-history", response_model=APIResponse)
def get_my_risk_history(
    current_user: deps.User = Depends(deps.require_role([Role.STUDENT])),
    db: Session = Depends(deps.get_db)
):
    """
    Get current student's historical risk snapshots.
    """
    history = db.query(RiskSnapshot).filter(RiskSnapshot.student_id == current_user.email).all()
    return success_response(
        history,
        message="Student risk history",
        meta={"pagination": {"total": len(history)}},
    )
