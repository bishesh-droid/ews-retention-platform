from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import User
from backend.api import deps
from backend.core.constants import Role
from backend.schemas.common import APIResponse
from backend.services.goals_service import GoalsService

router = APIRouter()


@router.get("/{student_id}", response_model=APIResponse)
def get_student_goals(
    student_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(
        deps.require_role([Role.STUDENT, Role.FACULTY, Role.RETENTION_TEAM, Role.ADMIN])
    ),
):
    """
    Get all goals for a student. Students can only see their own goals.
    """
    if current_user.role == Role.STUDENT and current_user.email != student_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view other students' goals"
        )

    return GoalsService.get_student_goals(db, student_id)


@router.post("/", response_model=APIResponse)
def create_goal(
    student_id: str,
    goal_type: str,
    title: str,
    target_value: float,
    end_date: datetime,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(
        deps.require_role([Role.FACULTY, Role.RETENTION_TEAM, Role.ADMIN])
    ),
):
    """
    Create a new goal for a student (Faculty/Admin only).
    """
    goal = GoalsService.create_goal(
        db, student_id, goal_type, title, target_value, end_date
    )
    db.commit()
    return goal


@router.post("/{student_id}/sync", response_model=APIResponse)
def sync_goal_progress(
    student_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(
        deps.require_role([Role.FACULTY, Role.RETENTION_TEAM, Role.ADMIN])
    ),
):
    """
    Manually trigger progress sync for a student's goals.
    """
    GoalsService.update_goal_progress(db, student_id)
    db.commit()
    return {"status": "success"}
