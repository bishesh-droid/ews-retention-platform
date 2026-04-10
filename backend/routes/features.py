"""
Feature API Endpoints
Provides access to engineered features for students.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional

from backend.api.deps import get_db, get_current_user, require_resource_ownership
from backend.services.student_service import StudentService
from backend.database import Student, User
from backend.utils.api import success_response

router = APIRouter(
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_current_user)],
)


@router.get("/{student_id}")
def get_student_features(
    student_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_resource_ownership("student_id")),
):
    """
    Get computed engagement features for a student.

    FERPA-compliant: Only staff (faculty/admin) or the student themselves
    can access this endpoint.
    """
    student = StudentService.get_student_by_id(db, student_id)

    if not student:
        raise HTTPException(status_code=404, detail="No features found for student.")

    data = {
        "student_id": student_id,
        "computation_date": "latest",
        "academic_signals": {
            "assignment_completion_rate": student.get("assignment_score", 0) / 100.0,
            "average_grade": student.get("graded_quiz_score", 0) / 100.0,
            "deadline_adherence_score": student.get("graded_assignment_score", 0) / 100.0,
            "grade_trend": 0.0,
        },
        "engagement_signals": {
            "login_frequency": student.get("login_consistency_score", 0) / 100.0,
            "avg_session_duration": student.get("time_investment_score", 0) / 100.0,
            "video_completion_rate": student.get("content_completion_score", 0) / 100.0,
            "platform_interaction_score": student.get("discussion_engagement_score", 0) / 100.0,
        },
        "consistency_signals": {
            "attendance_rate": student.get("exam_attendance_rate", 0) / 100.0,
            "activity_regularity_score": student.get("login_consistency_score", 0) / 100.0,
            "missed_classes_count": 0,
            "attendance_trend": 0.0,
        },
        "intent_signals": {
            "engagement_trend": student.get("trend", "active"),
            "days_inactive": 0,
            "declining_performance_flag": student.get("trend") == "declining",
        },
        "responsiveness_signals": {
            "email_open_rate": 0.0,
            "message_reply_rate": 0.0,
            "avg_response_time_hours": 0.0,
        },
    }
    return success_response(data, message="Student features")


@router.post("/compute")
def compute_features(
    student_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger feature computation. Features are computed on-the-fly from enrollment data.

    FERPA-compliant: When student_id is provided, only staff or the student
    themselves can trigger computation.
    """
    if student_id:
        # Enforce resource ownership for per-student computation
        checker = require_resource_ownership("student_id")
        # Manually invoke checker with request context
        from fastapi import Request
        request = Request(scope={"type": "http", "path_params": {"student_id": student_id}})
        checker(request=request, current_user=current_user)

        student = StudentService.get_student_by_id(db, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        data = {
            "status": "success",
            "student_id": student_id,
            "computation_date": "now",
            "message": "Features computed successfully (on-the-fly from enrollment data)",
        }
        return success_response(data, message="Features computed")
    else:
        total = db.query(Student).count()
        data: Dict[str, Any] = {
            "status": "completed",
            "computed": total,
            "failed": 0,
            "message": f"Features are computed on-the-fly for all {total} students",
        }
        return success_response(data, message="Features compute summary")


@router.get("/signal-summary/{signal_category}")
def get_signal_summary(
    signal_category: str,
    db: Session = Depends(get_db)
):
    """Get summary statistics for a signal category across all students."""
    valid_categories = ["academic", "engagement", "consistency", "intent", "responsiveness"]
    if signal_category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid signal category. Must be one of: {valid_categories}"
        )

    students = StudentService.get_all_students(db, 0, 2000)

    signal_map = {
        "academic": lambda s: s.get("graded_quiz_score", 0) / 100.0,
        "engagement": lambda s: s.get("content_completion_score", 0) / 100.0,
        "consistency": lambda s: s.get("exam_attendance_rate", 0) / 100.0,
        "intent": lambda s: s.get("graded_assignment_score", 0) / 100.0,
        "responsiveness": lambda s: s.get("exam_score", 0) / 100.0,
    }

    values = [signal_map[signal_category](s) for s in students]

    if not values:
        data = {"signal_category": signal_category, "total_students": 0, "mean": 0, "median": 0}
        return success_response(data, message="Signal summary")

    values.sort()
    n = len(values)
    mean_val = sum(values) / n
    median_val = values[n // 2]

    low = sum(1 for v in values if v < 0.3)
    medium = sum(1 for v in values if 0.3 <= v < 0.7)
    high = sum(1 for v in values if v >= 0.7)

    data = {
        "signal_category": signal_category,
        "total_students": n,
        "mean": round(mean_val, 3),
        "median": round(median_val, 3),
        "distribution": {"low": low, "medium": medium, "high": high},
    }
    return success_response(data, message="Signal summary")
