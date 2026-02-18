from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from backend.database import User
from backend.api import deps
from backend.services.goals_service import GoalsService

router = APIRouter()

@router.get("/{student_id}")
def get_student_goals(
    student_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(["Student", "Faculty", "Retention Team", "Admin"]))
):
    """
    Get all goals for a student. Students can only see their own goals.
    """
    if current_user.role == "Student" and current_user.email != student_id:
        raise HTTPException(status_code=403, detail="Not authorized to view other students' goals")
    
    return GoalsService.get_student_goals(db, student_id)

@router.post("/")
def create_goal(
    student_id: str,
    goal_type: str,
    title: str,
    target_value: float,
    end_date: datetime,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(["Faculty", "Retention Team", "Admin"]))
):
    """
    Create a new goal for a student (Faculty/Admin only).
    """
    return GoalsService.create_goal(db, student_id, goal_type, title, target_value, end_date)

@router.post("/{student_id}/sync")
def sync_goal_progress(
    student_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(["Faculty", "Retention Team", "Admin"]))
):
    """
    Manually trigger progress sync for a student's goals.
    """
    GoalsService.update_goal_progress(db, student_id)
    return {"status": "success"}
