"""
Feedback Loop API Endpoints
Tracks student responses to interventions and measures effectiveness
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from backend.app.database import get_db
from backend.app.models import StudentResponse, Intervention
from backend.app import schemas

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.post("/response", status_code=201)
def record_student_response(
    response: schemas.StudentResponseCreate,
    db: Session = Depends(get_db)
):
    """
    Record student response to an intervention
    
    Example request body:
    {
        "student_id": "S001",
        "intervention_id": 123,
        "responded": true,
        "response_time_hours": 24.5,
        "behavioral_change_detected": true,
        "engagement_change_7days": 0.15,
        "attendance_change_7days": 0.10,
        "grade_change_next_assignment": 5.0,
        "retained": null
    }
    """
    # Verify intervention exists
    intervention = db.query(Intervention).filter(
        Intervention.id == response.intervention_id
    ).first()
    
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    
    # Create response record
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
    
    # Update intervention effectiveness score
    if db_response.behavioral_change_detected:
        changes = [
            response.engagement_change_7days or 0,
            response.attendance_change_7days or 0,
            (response.grade_change_next_assignment or 0) / 100.0  # Normalize grade change
        ]
        effectiveness = sum([c for c in changes if c > 0]) / 3.0
        intervention.effectiveness_score = max(0, min(1.0, effectiveness))
    else:
        intervention.effectiveness_score = 0.0
    
    db.commit()
    db.refresh(db_response)
    
    return {
        "status": "success",
        "response_id": db_response.id,
        "intervention_effectiveness": intervention.effectiveness_score,
        "message": "Student response recorded"
    }


@router.get("/effectiveness")
def get_intervention_effectiveness(
    threshold_category: Optional[str] = None,
    days_lookback: int = 90,
    db: Session = Depends(get_db)
):
    """
    Get intervention effectiveness metrics
    
    Query params:
    - threshold_category: Filter by category (gentle_reminder, mentor_outreach, urgent_intervention)
    - days_lookback: Number of days to look back (default 90)
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_lookback)
    
    # Get interventions with responses
    query = db.query(Intervention).join(
        StudentResponse,
        Intervention.id == StudentResponse.intervention_id
    ).filter(
        Intervention.date >= cutoff_date.date()
    )
    
    if threshold_category:
        query = query.filter(Intervention.threshold_category == threshold_category)
    
    interventions = query.all()
    
    if not interventions:
        return {
            "total_interventions": 0,
            "message": "No interventions found with responses in this period"
        }
    
    # Calculate metrics
    total = len(interventions)
    effectiveness_scores = [i.effectiveness_score for i in interventions if i.effectiveness_score is not None]
    
    # Group by threshold category
    by_category = {}
    for intervention in interventions:
        cat = intervention.threshold_category or "unknown"
        if cat not in by_category:
            by_category[cat] = []
        if intervention.effectiveness_score is not None:
            by_category[cat].append(intervention.effectiveness_score)
    
    category_stats = {}
    for cat, scores in by_category.items():
        if scores:
            import numpy as np
            category_stats[cat] = {
                "count": len(scores),
                "mean_effectiveness": float(np.mean(scores)),
                "median_effectiveness": float(np.median(scores)),
                "success_rate": sum(1 for s in scores if s >= 0.5) / len(scores)
            }
    
    # Calculate response rates
    total_interventions = db.query(Intervention).filter(
        Intervention.date >= cutoff_date.date()
    ).count()
    
    total_responses = db.query(StudentResponse).filter(
        StudentResponse.recorded_at >= cutoff_date
    ).count()
    
    response_rate = total_responses / max(total_interventions, 1)
    
    # Behavioral change rate
    behavioral_changes = db.query(StudentResponse).filter(
        StudentResponse.recorded_at >= cutoff_date,
        StudentResponse.behavioral_change_detected == True
    ).count()
    
    behavioral_change_rate = behavioral_changes / max(total_responses, 1)
    
    # Average response time
    responses = db.query(StudentResponse).filter(
        StudentResponse.recorded_at >= cutoff_date,
        StudentResponse.responded == True
    ).all()
    
    avg_response_time = 0.0
    if responses:
        response_times = [r.response_time_hours for r in responses if r.response_time_hours]
        if response_times:
            import numpy as np
            avg_response_time = float(np.mean(response_times))
    
    import numpy as np
    overall_effectiveness = float(np.mean(effectiveness_scores)) if effectiveness_scores else 0.0
    
    return {
        "period_days": days_lookback,
        "total_interventions": total_interventions,
        "total_responses": total_responses,
        "response_rate": round(response_rate, 3),
        "overall_effectiveness": round(overall_effectiveness, 3),
        "behavioral_change_rate": round(behavioral_change_rate, 3),
        "average_response_time_hours": round(avg_response_time, 1),
        "by_threshold_category": category_stats
    }


@router.get("/{student_id}/history")
def get_student_feedback_history(
    student_id: str,
    db: Session = Depends(get_db)
):
    """
    Get feedback history for a specific student
    """
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
            "recorded_at": response.recorded_at
        })
    
    return {
        "student_id": student_id,
        "total_responses": len(history),
        "history": history
    }
