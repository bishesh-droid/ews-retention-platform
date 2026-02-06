from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import get_db, get_student_by_id
from backend.app.schemas import Recommendation
from backend.app.services.infrastructure.recommender import get_recommendations

router = APIRouter(
    responses={404: {"description": "Not found"}},
)

@router.get("/{student_id}", response_model=List[Recommendation])
def get_recommendations_for_student(student_id: str, db: Session = Depends(get_db)):
    """
    Returns a list of recommendations for a given student.
    """
    student = get_student_by_id(db, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    
    recommendations = get_recommendations(student)
    
    return recommendations
