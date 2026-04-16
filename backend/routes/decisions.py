"""
Decision API Endpoints
Provides intervention recommendations based on risk scores.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from backend.api.deps import get_db, get_current_user
from backend.services.student_service import StudentService
from backend.database import Intervention

router = APIRouter(
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_current_user)],
)


def _get_recommendation(risk_score: float) -> dict:
    """Get intervention recommendation based on risk score (0-100 scale)."""
    if risk_score >= 80:
        return {
            "threshold_category": "urgent",
            "action_type": "urgent_intervention",
            "channels": ["whatsapp", "phone", "email"],
            "assigned_team": "sales",
            "urgency": "critical",
            "description": "Immediate outreach required - student at critical risk of dropout.",
        }
    elif risk_score >= 60:
        return {
            "threshold_category": "mentor_outreach",
            "action_type": "mentor_outreach",
            "channels": ["email", "mentor_call"],
            "assigned_team": "faculty",
            "urgency": "high",
            "description": "Schedule faculty mentor meeting to discuss academic support.",
        }
    elif risk_score >= 40:
        return {
            "threshold_category": "gentle_reminder",
            "action_type": "gentle_reminder",
            "channels": ["email"],
            "assigned_team": "automated",
            "urgency": "medium",
            "description": "Send automated encouragement and resource links.",
        }
    else:
        return {
            "threshold_category": "low_risk",
            "action_type": "no_action",
            "channels": [],
            "assigned_team": "none",
            "urgency": "none",
            "description": "No intervention needed - student is on track.",
        }


@router.get("/{student_id}")
def get_recommended_intervention(student_id: str, db: Session = Depends(get_db)):
    """Get intervention recommendation based on current risk score."""
    student = StudentService.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    risk_score = student["risk_score"]
    recommendation = _get_recommendation(risk_score)

    # Get last intervention
    last_intervention = (
        db.query(Intervention)
        .filter(Intervention.student_id == student_id)
        .order_by(Intervention.date.desc())
        .first()
    )

    days_since_last = None
    if last_intervention and last_intervention.date:
        days_since_last = (date.today() - last_intervention.date).days

    if risk_score >= 80:
        priority = "critical"
    elif risk_score >= 60:
        priority = "high"
    elif risk_score >= 40:
        priority = "medium"
    else:
        priority = "low"

    return {
        "student_id": student_id,
        "current_risk_score": risk_score,
        "risk_score_percent": round(risk_score, 1),
        "threshold_category": recommendation["threshold_category"],
        "should_trigger": risk_score >= 40
        and (days_since_last is None or days_since_last >= 7),
        "days_since_last_intervention": days_since_last,
        "priority": priority,
        "recommended_action": recommendation,
        "signal_breakdown": {
            "academic": student.get("graded_quiz_score", 0) / 100.0,
            "engagement": student.get("content_completion_score", 0) / 100.0,
            "consistency": student.get("exam_attendance_rate", 0) / 100.0,
            "intent": student.get("graded_assignment_score", 0) / 100.0,
            "responsiveness": student.get("exam_score", 0) / 100.0,
        },
    }


@router.get("/pending/list")
def get_pending_interventions(
    priority: str = None,
    assigned_team: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get list of students who need interventions."""
    _students_result = StudentService.get_all_students(
        db, 0, 500, "risk_score", "desc", risk_min=40.0
    )
    students = _students_result.get("students", [])

    pending = []
    for s in students:
        recommendation = _get_recommendation(s["risk_score"])

        if recommendation["threshold_category"] == "low_risk":
            continue

        priority_level = (
            "critical"
            if s["risk_score"] >= 80
            else "high" if s["risk_score"] >= 60 else "medium"
        )

        if priority and priority_level != priority:
            continue
        if assigned_team and recommendation["assigned_team"] != assigned_team:
            continue

        pending.append(
            {
                "student_id": s["id"],
                "risk_score": s["risk_score"],
                "risk_score_percent": round(s["risk_score"], 1),
                "threshold_category": recommendation["threshold_category"],
                "assigned_team": recommendation["assigned_team"],
                "priority": priority_level,
                "days_since_last_intervention": None,
                "recommended_channels": recommendation["channels"],
            }
        )

    return {
        "total_pending": len(pending),
        "interventions": pending[:limit],
    }
