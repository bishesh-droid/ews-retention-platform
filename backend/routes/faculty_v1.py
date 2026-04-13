from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.api import deps
from backend.core.constants import Role
from backend.core.rate_limiting import limiter
from backend.schemas.common import APIResponse
from backend.services.student_service import StudentService

router = APIRouter()


@router.get("/students", response_model=APIResponse)
def get_faculty_students(
    current_user: deps.User = Depends(deps.require_role([Role.FACULTY])),
    db: Session = Depends(deps.get_db),
    limit: int = Query(200, ge=1, le=1000),
) -> Dict[str, Any]:
    """
    Get students assigned to or relevant for this faculty member.

    Until explicit faculty-student mappings exist, this returns a
    risk-sorted slice of the global student list sized for the UI.
    """
    students = StudentService.get_all_students(db, skip=0, limit=limit, sort_by="risk_score", order="desc")
    return {
        "students": students,
        "count": len(students),
    }


@router.get("/at-risk", response_model=APIResponse)
def get_faculty_at_risk_students(
    current_user: deps.User = Depends(deps.require_role([Role.FACULTY])),
    db: Session = Depends(deps.get_db),
    threshold: float = Query(60.0, ge=0, le=100, description="Risk score threshold for at-risk list"),
    limit: int = Query(200, ge=1, le=1000),
) -> Dict[str, Any]:
    """
    Get at-risk students for this faculty member.

    Threshold is applied to the 0–100 risk_score; higher = more risk.
    """
    all_students = StudentService.get_all_students(db, skip=0, limit=5000, sort_by="risk_score", order="desc")
    at_risk = [s for s in all_students if (s.get("risk_score") or 0) >= threshold][:limit]
    return {
        "students": at_risk,
        "count": len(at_risk),
        "threshold": threshold,
    }


@router.get("/alerts", response_model=APIResponse)
@limiter.limit("60/minute")
def get_engagement_alerts(
    request: Request,
    current_user: deps.User = Depends(deps.require_role([Role.FACULTY])),
    db: Session = Depends(deps.get_db),
    limit: int = Query(100, ge=1, le=1000),
) -> Dict[str, Any]:
    """
    Recent disengagement alerts for faculty review.

    Alerts are derived from current engagement metrics and risk scores:
    - Low attendance
    - Low quiz performance
    - Low engagement / time investment
    """
    students = StudentService.get_all_students(db, skip=0, limit=5000, sort_by="risk_score", order="desc")

    alerts: List[Dict[str, Any]] = []
    for s in students:
        reasons = []
        exam_attendance = s.get("exam_attendance_rate") or 0
        quiz_score = s.get("graded_quiz_score") or 0
        engagement = s.get("content_completion_score") or 0
        time_investment = s.get("time_investment_score") or 0

        if exam_attendance < 70:
            reasons.append("Low attendance")
        if quiz_score < 50:
            reasons.append("Low quiz performance")
        if engagement < 50 or time_investment < 50:
            reasons.append("Low platform engagement")

        if not reasons:
            continue

        alerts.append(
            {
                "student_id": s.get("id"),
                "name": f"{s.get('first_name') or ''} {s.get('last_name') or ''}".strip() or s.get("id"),
                "risk_score": s.get("risk_score") or 0,
                "exam_attendance_rate": exam_attendance,
                "graded_quiz_score": quiz_score,
                "primary_reason": reasons[0],
                "reasons": reasons,
                "department": s.get("department"),
            }
        )

    alerts_sorted = sorted(alerts, key=lambda a: (a["risk_score"], -(a["exam_attendance_rate"] or 0)))
    alerts_trimmed = alerts_sorted[:limit]

    return {
        "alerts": alerts_trimmed,
        "count": len(alerts_trimmed),
    }
