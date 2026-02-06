from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db, get_student_by_id
from backend.app.models import Student
from backend.app.services import calculate_student_risk, batch_predict, get_signal_summary
from backend.app import schemas

router = APIRouter(
    responses={404: {"description": "Not found"}},
)

@router.get("/batch")
def get_all_predictions(
    include_decisions: bool = Query(False, description="Include intervention recommendations"),
    db: Session = Depends(get_db)
):
    """
    Get batch predictions for all students.
    
    Query params:
    - include_decisions: If true, include intervention recommendations for each student
    """
    students = db.query(Student).all()
    students_data = [
        {
            'id': s.id,
            'absrate7': s.absrate7,
            'q4mpa7': s.q4mpa7,
            'nsusp7': s.nsusp7,
            'mobility7': s.mobility7,
        }
        for s in students
    ]
    
    predictions = batch_predict(students_data, include_decisions=include_decisions)
    
    # Add signal summary
    signal_summary = get_signal_summary(predictions)
    
    return {
        "total_students": len(predictions),
        "predictions": predictions,
        "signal_summary": signal_summary
    }

@router.get("/{student_id}")
def get_student_prediction(
    student_id: str,
    include_decisions: bool = Query(True, description="Include intervention recommendations"),
    db: Session = Depends(get_db)
):
    """
    Get prediction for a specific student.
    
    Query params:
    - include_decisions: If true, include intervention recommendations (default: true)
    """
    student = get_student_by_id(db, student_id)
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    student_data = {
        'id': student.id,
        'absrate7': student.absrate7,
        'q4mpa7': student.q4mpa7,
        'nsusp7': student.nsusp7,
        'mobility7': student.mobility7,
    }
    
    prediction = calculate_student_risk(student_data, include_decisions=include_decisions)
    
    if not prediction:
        raise HTTPException(status_code=500, detail="Failed to calculate risk")
    
    prediction['student_id'] = student_id
    return prediction
