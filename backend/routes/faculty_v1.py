from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from backend.database import Student
from backend.api import deps

router = APIRouter()

@router.get("/students")
def get_faculty_students(
    current_user: deps.User = Depends(deps.require_role(["Faculty"])),
    db: Session = Depends(deps.get_db)
):
    """
    Get students assigned to or relevant for this faculty member.
    """
    # For now, return all students as we don't have faculty-student assignment yet
    return db.query(Student).limit(100).all()

@router.get("/alerts")
def get_engagement_alerts(
    current_user: deps.User = Depends(deps.require_role(["Faculty"])),
    db: Session = Depends(deps.get_db)
):
    """
    Recent disengagement alerts for faculty review.
    """
    # Mocking for now, will integrate with Event engine later
    return {"alerts": []}
