"""
Feature API Endpoints
Provides access to engineered features and triggers feature computation
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from backend.app.database import get_db
from backend.app.models import EngineeredFeatures, Student
from backend.app.services.core.feature_service import compute_all_features
import json

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.get("/{student_id}")
def get_student_features(student_id: str, db: Session = Depends(get_db)):
    """
    Get latest engineered features for a student
    """
    # Get most recent features
    features = db.query(EngineeredFeatures).filter(
        EngineeredFeatures.student_id == student_id
    ).order_by(EngineeredFeatures.computation_date.desc()).first()
    
    if not features:
        raise HTTPException(status_code=404, detail="No features found for student. Try computing features first.")
    
    return {
        "student_id": features.student_id,
        "computation_date": features.computation_date,
        "academic_signals": {
            "assignment_completion_rate": features.assignment_completion_rate,
            "average_grade": features.average_grade,
            "deadline_adherence_score": features.deadline_adherence_score,
            "grade_trend": features.grade_trend
        },
        "engagement_signals": {
            "login_frequency": features.login_frequency,
            "avg_session_duration": features.avg_session_duration,
            "video_completion_rate": features.video_completion_rate,
            "platform_interaction_score": features.platform_interaction_score
        },
        "consistency_signals": {
            "attendance_rate": features.attendance_rate,
            "activity_regularity_score": features.activity_regularity_score,
            "missed_classes_count": features.missed_classes_count,
            "attendance_trend": features.attendance_trend
        },
        "intent_signals": {
            "engagement_trend": features.engagement_trend,
            "days_inactive": features.days_inactive,
            "declining_performance_flag": features.declining_performance_flag
        },
        "responsiveness_signals": {
            "email_open_rate": features.email_open_rate,
            "message_reply_rate": features.message_reply_rate,
            "avg_response_time_hours": features.avg_response_time_hours
        }
    }


@router.post("/compute")
def compute_features(
    student_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Trigger feature computation for a student or all students
    
    Query params:
    - student_id: Optional student ID. If omitted, computes for all students (async)
    """
    if student_id:
        # Compute for single student synchronously
        features = compute_all_features(student_id, db)
        
        if not features:
            raise HTTPException(status_code=500, detail="Failed to compute features")
        
        # Save features
        db.add(features)
        db.commit()
        db.refresh(features)
        
        return {
            "status": "success",
            "student_id": student_id,
            "computation_date": features.computation_date,
            "message": "Features computed successfully"
        }
    else:
        # Batch computation (would normally be async, but simplified here)
        students = db.query(Student).all()
        computed_count = 0
        failed_count = 0
        
        for student in students[:50]:  # Limit to 50 for demo
            features = compute_all_features(student.id, db)
            if features:
                db.add(features)
                computed_count += 1
            else:
                failed_count += 1
        
        db.commit()
        
        return {
            "status": "completed",
            "computed": computed_count,
            "failed": failed_count,
            "message": f"Batch feature computation completed for {computed_count} students"
        }


@router.get("/signal-summary/{signal_category}")
def get_signal_summary(
    signal_category: str,
    threshold_low: float = 0.3,
    threshold_high: float = 0.7,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for a specific signal category across all students
    
    Signal categories: academic, engagement, consistency, intent, responsiveness
    """
    valid_categories = ["academic", "engagement", "consistency", "intent", "responsiveness"]
    if signal_category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid signal category. Must be one of: {valid_categories}")
    
    # Get latest features for all students
    # This is a simplified query - in production you'd use window functions
    all_features = db.query(EngineeredFeatures).all()
    
    # Group by student and get latest
    latest_features = {}
    for f in all_features:
        if f.student_id not in latest_features or f.computation_date > latest_features[f.student_id].computation_date:
            latest_features[f.student_id] = f
    
    # Extract signal values based on category
    signal_mapping = {
        "academic": lambda f: (f.average_grade / 100.0 + f.assignment_completion_rate + f.deadline_adherence_score) / 3.0,
        "engagement": lambda f: (f.login_frequency / 10.0 + f.video_completion_rate + f.platform_interaction_score) / 3.0,
        "consistency": lambda f: (f.attendance_rate + f.activity_regularity_score) / 2.0,
        "intent": lambda f: max(0, 1.0 - (f.days_inactive / 30.0)),  # Invert days inactive
        "responsiveness": lambda f: (f.email_open_rate + f.message_reply_rate) / 2.0
    }
    
    values = []
    low_count = 0
    medium_count = 0
    high_count = 0
    
    for features in latest_features.values():
        try:
            value = signal_mapping[signal_category](features)
            values.append(value)
            
            if value < threshold_low:
                low_count += 1
            elif value < threshold_high:
                medium_count += 1
            else:
                high_count += 1
        except:
            continue
    
    import numpy as np
    
    return {
        "signal_category": signal_category,
        "total_students": len(values),
        "mean": float(np.mean(values)) if values else 0,
        "median": float(np.median(values)) if values else 0,
        "std_dev": float(np.std(values)) if values else 0,
        "distribution": {
            "low": low_count,
            "medium": medium_count,
            "high": high_count
        }
    }
