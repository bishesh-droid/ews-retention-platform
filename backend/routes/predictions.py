"""
Predictions API Routes for EWS Retention Platform.

Provides risk predictions calculated from real engagement data.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services.student_service import StudentService
from backend.database import Student

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.get("/batch")
def get_all_predictions(
    include_decisions: bool = Query(False, description="Include intervention recommendations"),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db)
):
    """Get batch predictions for all students."""
    students = StudentService.get_all_students(db, skip=0, limit=limit)

    predictions = []
    for s in students:
        pred = {
            "student_id": s["id"],
            "risk_score": s["risk_score"] / 100.0,  # Normalize to 0-1
            "engagement_score": (100 - s["risk_score"]) / 100.0,
            "retention_likelihood": s["retention_likelihood"],
            "model_version": "rule_based_v2",
            "signal_breakdown": {
                "academic_signal_score": s.get("graded_quiz_score", 0) / 100.0,
                "engagement_signal_score": s.get("content_completion_score", 0) / 100.0,
                "consistency_signal_score": s.get("exam_attendance_rate", 0) / 100.0,
                "intent_signal_score": s.get("graded_assignment_score", 0) / 100.0,
                "responsiveness_signal_score": s.get("exam_score", 0) / 100.0,
            },
            "top_risk_factors": [s.get("dominant_risk_factor", "Unknown")],
            "prediction_error": False,
        }

        if include_decisions:
            risk = s["risk_score"]
            if risk >= 80:
                category = "urgent"
                action = "Immediate outreach required"
                channels = ["whatsapp", "phone", "email"]
                team = "sales"
            elif risk >= 60:
                category = "mentor_outreach"
                action = "Schedule mentor meeting"
                channels = ["email", "mentor_call"]
                team = "faculty"
            elif risk >= 40:
                category = "gentle_reminder"
                action = "Send encouragement email"
                channels = ["email"]
                team = "automated"
            else:
                category = "no_action"
                action = "No intervention needed"
                channels = []
                team = "none"

            pred["intervention_recommendation"] = {
                "threshold_category": category,
                "action_type": action,
                "channels": channels,
                "assigned_team": team,
                "priority": "critical" if risk >= 80 else "high" if risk >= 60 else "medium" if risk >= 40 else "low",
                "urgency": category,
                "description": action,
            }

        predictions.append(pred)

    return {
        "total_students": len(predictions),
        "predictions": predictions,
    }


@router.get("/{student_id}")
def get_student_prediction(
    student_id: str,
    include_decisions: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get prediction for a specific student."""
    student = StudentService.get_student_by_id(db, student_id)

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    risk = student["risk_score"]

    response = {
        "student_id": student_id,
        "risk_score": risk / 100.0,
        "engagement_score": (100 - risk) / 100.0,
        "retention_likelihood": student["retention_likelihood"],
        "model_version": "rule_based_v2",
        "signal_breakdown": {
            "academic_signal_score": student.get("graded_quiz_score", 0) / 100.0,
            "engagement_signal_score": student.get("content_completion_score", 0) / 100.0,
            "consistency_signal_score": student.get("exam_attendance_rate", 0) / 100.0,
            "intent_signal_score": student.get("graded_assignment_score", 0) / 100.0,
            "responsiveness_signal_score": student.get("exam_score", 0) / 100.0,
        },
        "top_risk_factors": [student.get("dominant_risk_factor", "Unknown")],
        "prediction_error": False,
    }

    if include_decisions:
        if risk >= 80:
            category, action, channels, team = "urgent", "Immediate outreach", ["whatsapp", "phone", "email"], "sales"
        elif risk >= 60:
            category, action, channels, team = "mentor_outreach", "Schedule mentor meeting", ["email", "mentor_call"], "faculty"
        elif risk >= 40:
            category, action, channels, team = "gentle_reminder", "Send encouragement", ["email"], "automated"
        else:
            category, action, channels, team = "no_action", "No intervention needed", [], "none"

        response["intervention_recommendation"] = {
            "threshold_category": category,
            "action_type": action,
            "channels": channels,
            "assigned_team": team,
            "priority": "critical" if risk >= 80 else "high" if risk >= 60 else "medium" if risk >= 40 else "low",
            "urgency": category,
            "description": action,
        }

    return response
