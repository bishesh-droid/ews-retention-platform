"""
AI Academic Advisor API Routes (Stubbed)
Provides mock responses for AI-powered academic advising features.
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from backend.api.deps import get_db
from backend.services.student_service import StudentService
from fastapi import Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/advisor", tags=["AI Academic Advisor"])


class StudyPlanRequest(BaseModel):
    preferences: Optional[Dict[str, Any]] = None


@router.post("/study-plan/{student_id}")
def get_study_plan(
    student_id: str,
    request: Optional[StudyPlanRequest] = None,
    db: Session = Depends(get_db)
):
    """Generate a personalized study plan for a student."""
    student = StudentService.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    risk = student["risk_score"]
    weeks = []
    for week_num in range(1, 5):
        focus = "content completion" if student.get("content_completion_score", 0) < 50 else "quiz preparation"
        weeks.append({
            "week": week_num,
            "focus": focus,
            "goals": [
                f"Complete {5 + week_num} content modules",
                f"Attempt at least {week_num} practice quizzes",
                "Review lecture notes for 30 minutes daily",
            ],
            "estimated_hours": 10 + (5 if risk > 60 else 0),
        })

    return {
        "success": True,
        "student_id": student_id,
        "generated_at": datetime.now().isoformat(),
        "plan_duration_weeks": 4,
        "plan": {"weeks": weeks, "overall_goal": "Improve engagement and academic performance"},
        "context_summary": {"risk_score": risk, "dominant_factor": student.get("dominant_risk_factor", "")},
    }


@router.post("/faculty-summary/{student_id}")
def get_faculty_summary(
    student_id: str,
    include_talking_points: bool = True,
    db: Session = Depends(get_db)
):
    """Generate a faculty-appropriate student summary."""
    student = StudentService.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    talking_points = []
    if include_talking_points:
        if student.get("content_completion_score", 0) < 30:
            talking_points.append("Content completion is low - ask about study schedule challenges")
        if student.get("exam_attendance_rate", 0) < 80:
            talking_points.append("Has missed some exams - explore reasons and offer support")
        if student.get("discussion_engagement_score", 0) < 10:
            talking_points.append("Not participating in discussions - encourage peer collaboration")
        if not talking_points:
            talking_points.append("Student is performing well - recognize achievements and encourage continued effort")

    return {
        "success": True,
        "student_id": student_id,
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "overview": f"Student is enrolled in {student.get('total_courses', 0)} courses with {student.get('content_completion_score', 0):.0f}% content completion.",
            "engagement_level": student.get("trend", "unknown"),
            "key_concern": student.get("dominant_risk_factor", "None identified"),
            "talking_points": talking_points,
        },
        "data_sources": ["enrollment_data", "graded_components", "exam_records"],
    }


@router.get("/context/{student_id}")
def get_advisor_context(
    student_id: str,
    db: Session = Depends(get_db)
):
    """Get the advisor context for a student."""
    student = StudentService.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    return {
        "student_id": student_id,
        "context_generated_at": datetime.now().isoformat(),
        "student_profile": {
            "name": f"{student.get('first_name', '')} {student.get('last_name', '')}".strip(),
            "department": student.get("department", ""),
            "courses": student.get("total_courses", 0),
            "is_active": student.get("is_active", True),
        },
        "risk_assessment": {
            "risk_score": student["risk_score"],
            "risk_category": student["risk_category"],
            "dominant_factor": student.get("dominant_risk_factor", ""),
        },
        "academic_history": {
            "content_completion": student.get("content_completion_score", 0),
            "quiz_score": student.get("graded_quiz_score", 0),
            "exam_score": student.get("exam_score", 0),
        },
        "intervention_history": {"total_interventions": 0, "last_intervention": None},
        "advisor_hints": [
            f"Focus on {student.get('dominant_risk_factor', 'engagement')}",
            f"Student trend: {student.get('trend', 'unknown')}",
        ],
    }


@router.post("/motivational-message/{student_id}")
def get_motivational_message(
    student_id: str,
    tone: str = "encouraging",
    db: Session = Depends(get_db)
):
    """Generate a motivational message for a student."""
    student = StudentService.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

    risk = student["risk_score"]
    if tone == "celebratory" and risk < 30:
        message = "Congratulations on your excellent academic performance! Your hard work is clearly paying off."
    elif risk < 40:
        message = "You're doing great! Your consistent effort is showing in your results. Keep it up!"
    elif risk < 60:
        message = "Every step forward counts. You have the potential to succeed, and we're here to support you."
    else:
        message = "We believe in your ability to overcome challenges. Let's work together to find the support you need."

    return {
        "success": True,
        "student_id": student_id,
        "message": message,
        "tone": tone,
        "generated_at": datetime.now().isoformat(),
    }
