"""
Decision API Endpoints
Provides intervention recommendations based on risk scores and decision thresholds
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import date, timedelta

from backend.app.database import get_db, get_student_by_id
from backend.app.models import Prediction, Intervention
from backend.app.services.core.decision_engine import (
    get_intervention_recommendation,
    should_trigger_intervention,
    get_message_template,
    calculate_intervention_priority
)
from backend.app import schemas
import json

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.get("/{student_id}")
def get_recommended_intervention(student_id: str, db: Session = Depends(get_db)):
    """
    Get intervention recommendation based on current risk score
    """
    student = get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Get latest prediction
    latest_prediction = db.query(Prediction).filter(
        Prediction.student_id == student_id
    ).order_by(Prediction.id.desc()).first()
    
    if not latest_prediction:
        raise HTTPException(status_code=404, detail="No prediction found for student")
    
    risk_score = latest_prediction.risk_score
    
    # Get last intervention date
    last_intervention = db.query(Intervention).filter(
        Intervention.student_id == student_id
    ).order_by(Intervention.date.desc()).first()
    
    days_since_last = None
    if last_intervention:
        days_since_last = (date.today() - last_intervention.date).days
    
    # Get recommendation
    recommendation = get_intervention_recommendation(risk_score)
    
    # Check if should trigger
    should_trigger = should_trigger_intervention(
        current_risk_score=risk_score,
        days_since_last_intervention=days_since_last
    )
    
    # Calculate priority
    priority = calculate_intervention_priority(
        risk_score=risk_score,
        engagement_trend=getattr(latest_prediction, 'intent_signal_score', None),
        days_inactive=None  # Would need to compute from engineered features
    )
    
    return {
        "student_id": student_id,
        "current_risk_score": risk_score,
        "risk_score_percent": round(risk_score * 100, 1),
        "threshold_category": recommendation["threshold_category"],
        "should_trigger": should_trigger,
        "days_since_last_intervention": days_since_last,
        "priority": priority,
        "recommended_action": recommendation,
        "signal_breakdown": {
            "academic": latest_prediction.academic_signal_score,
            "engagement": latest_prediction.engagement_signal_score,
            "consistency": latest_prediction.consistency_signal_score,
            "intent": latest_prediction.intent_signal_score,
            "responsiveness": latest_prediction.responsiveness_signal_score
        }
    }


@router.post("/execute")
def execute_intervention(
    intervention_request: schemas.InterventionCreate,
    db: Session = Depends(get_db)
):
    """
    Execute an intervention and log it
    
    Example request body:
    {
        "user": "admin_user",
        "action": "Mentor outreach initiated",
        "risk_score_at_trigger": 0.72,
        "threshold_category": "mentor_outreach",
        "channels": ["email", "mentor_call"],
        "assigned_team": "faculty"
    }
    """
    # Extract student_id from request or require it
    # For now, we'll need to add student_id to the request
    # This is a placeholder - you'd need to pass student_id
    
    db_intervention = Intervention(
        student_id="placeholder",  # Should come from request
        date=date.today(),
        user=intervention_request.user,
        action=intervention_request.action,
        risk_score_at_trigger=intervention_request.risk_score_at_trigger,
        threshold_category=intervention_request.threshold_category,
        channels=json.dumps(intervention_request.channels) if intervention_request.channels else None,
        assigned_team=intervention_request.assigned_team
    )
    
    db.add(db_intervention)
    db.commit()
    db.refresh(db_intervention)
    
    return {
        "status": "success",
        "intervention_id": db_intervention.id,
        "message": "Intervention logged successfully"
    }


@router.get("/pending/list")
def get_pending_interventions(
    priority: str = None,
    assigned_team: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get list of students who need interventions
    
    Query params:
    - priority: Filter by priority level
    - assigned_team: Filter by team (automated, faculty, sales)
    - limit: Max number of results
    """
    # Get all students with recent predictions
    recent_predictions = db.query(Prediction).order_by(
        Prediction.student_id, Prediction.id.desc()
    ).all()
    
    # Group by student_id and get latest
    student_predictions = {}
    for pred in recent_predictions:
        if pred.student_id not in student_predictions:
            student_predictions[pred.student_id] = pred
    
    pending = []
    
    for student_id, prediction in student_predictions.items():
        # Get recommendation
        recommendation = get_intervention_recommendation(prediction.risk_score)
        
        # Skip if no action needed
        if recommendation["threshold_category"] == "low_risk":
            continue
        
        # Get last intervention
        last_intervention = db.query(Intervention).filter(
            Intervention.student_id == student_id
        ).order_by(Intervention.date.desc()).first()
        
        days_since_last = None
        if last_intervention:
            days_since_last = (date.today() - last_intervention.date).days
        
        # Check if should trigger
        should_trigger = should_trigger_intervention(
            current_risk_score=prediction.risk_score,
            days_since_last_intervention=days_since_last
        )
        
        if not should_trigger:
            continue
        
        # Calculate priority
        priority_level = calculate_intervention_priority(
            risk_score=prediction.risk_score
        )
        
        # Apply filters
        if priority and priority_level != priority:
            continue
        if assigned_team and recommendation["assigned_team"] != assigned_team:
            continue
        
        pending.append({
            "student_id": student_id,
            "risk_score": prediction.risk_score,
            "risk_score_percent": round(prediction.risk_score * 100, 1),
            "threshold_category": recommendation["threshold_category"],
            "assigned_team": recommendation["assigned_team"],
            "priority": priority_level,
            "days_since_last_intervention": days_since_last,
            "recommended_channels": recommendation["channels"]
        })
    
    # Sort by priority and risk score
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    pending.sort(key=lambda x: (priority_order.get(x["priority"], 4), -x["risk_score"]))
    
    return {
        "total_pending": len(pending),
        "interventions": pending[:limit]
    }
