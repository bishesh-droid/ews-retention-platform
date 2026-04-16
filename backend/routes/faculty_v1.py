from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.api import deps
from backend.core.constants import Role
from backend.core.rate_limiting import limiter
from backend.schemas.common import APIResponse
from backend.services.student_service import StudentService
from backend.database.models.faculty_notification_pref import FacultyNotificationPref

router = APIRouter()


# ============================================================================
# E-1: Notification Preferences Schemas
# ============================================================================

class NotificationPrefsResponse(BaseModel):
    """Faculty notification preferences response."""
    id: int
    user_id: int
    notify_on_high_risk: bool
    notify_on_critical_risk: bool
    notification_channel: str  # "email" | "webhook"
    webhook_url: Optional[str] = None
    email_override: Optional[str] = None
    last_notified_at: Optional[datetime] = None
    cooldown_hours: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NotificationPrefsUpdate(BaseModel):
    """Faculty notification preferences update request."""
    notify_on_high_risk: Optional[bool] = None
    notify_on_critical_risk: Optional[bool] = None
    notification_channel: Optional[str] = Field(None, pattern=r"^(email|webhook)$")
    webhook_url: Optional[str] = Field(None, max_length=500)
    email_override: Optional[str] = Field(None, max_length=200)
    cooldown_hours: Optional[int] = Field(None, ge=1, le=168)  # 1 hour to 1 week


# ============================================================================
# E-1: Notification Preferences Endpoints
# ============================================================================

@router.get("/notification-prefs", response_model=APIResponse)
def get_notification_preferences(
    current_user: deps.User = Depends(deps.require_role([Role.FACULTY, Role.ADMIN, Role.RETENTION_TEAM])),
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """
    Get current user's notification preferences.

    Returns default preferences if none have been configured yet.
    """
    pref = (
        db.query(FacultyNotificationPref)
        .filter(FacultyNotificationPref.user_id == current_user.id)
        .first()
    )

    if not pref:
        # Return default preferences (not persisted until first update)
        return {
            "success": True,
            "message": "Notification preferences retrieved (defaults)",
            "data": {
                "id": None,
                "user_id": current_user.id,
                "notify_on_high_risk": True,
                "notify_on_critical_risk": True,
                "notification_channel": "email",
                "webhook_url": None,
                "email_override": None,
                "last_notified_at": None,
                "cooldown_hours": 24,
                "created_at": None,
                "updated_at": None,
            },
        }

    return {
        "success": True,
        "message": "Notification preferences retrieved",
        "data": NotificationPrefsResponse.model_validate(pref).model_dump(),
    }


@router.put("/notification-prefs", response_model=APIResponse)
def update_notification_preferences(
    update: NotificationPrefsUpdate,
    current_user: deps.User = Depends(deps.require_role([Role.FACULTY, Role.ADMIN, Role.RETENTION_TEAM])),
    db: Session = Depends(deps.get_db),
) -> Dict[str, Any]:
    """
    Update current user's notification preferences.

    - **notify_on_high_risk**: Enable/disable alerts for HIGH risk (>=70)
    - **notify_on_critical_risk**: Enable/disable alerts for CRITICAL risk (>=85)
    - **notification_channel**: "email" or "webhook"
    - **webhook_url**: Required if channel is "webhook"
    - **email_override**: Optional alternate email for notifications
    - **cooldown_hours**: Minimum hours between notifications for same student (1-168)
    """
    pref = (
        db.query(FacultyNotificationPref)
        .filter(FacultyNotificationPref.user_id == current_user.id)
        .first()
    )

    # Validate webhook URL if channel is webhook
    if update.notification_channel == "webhook" and update.webhook_url:
        if not update.webhook_url.startswith(("https://", "http://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="webhook_url must be a valid HTTP(S) URL",
            )

    if pref:
        # Update existing record
        if update.notify_on_high_risk is not None:
            pref.notify_on_high_risk = update.notify_on_high_risk
        if update.notify_on_critical_risk is not None:
            pref.notify_on_critical_risk = update.notify_on_critical_risk
        if update.notification_channel is not None:
            pref.notification_channel = update.notification_channel
        if update.webhook_url is not None:
            pref.webhook_url = update.webhook_url
        if update.email_override is not None:
            pref.email_override = update.email_override
        if update.cooldown_hours is not None:
            pref.cooldown_hours = update.cooldown_hours
        pref.updated_at = datetime.utcnow()
    else:
        # Create new record with defaults + updates
        pref = FacultyNotificationPref(
            user_id=current_user.id,
            notify_on_high_risk=update.notify_on_high_risk if update.notify_on_high_risk is not None else True,
            notify_on_critical_risk=update.notify_on_critical_risk if update.notify_on_critical_risk is not None else True,
            notification_channel=update.notification_channel or "email",
            webhook_url=update.webhook_url,
            email_override=update.email_override,
            cooldown_hours=update.cooldown_hours if update.cooldown_hours is not None else 24,
        )
        db.add(pref)

    try:
        db.commit()
        db.refresh(pref)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save preferences: {exc}",
        )

    return {
        "success": True,
        "message": "Notification preferences updated",
        "data": NotificationPrefsResponse.model_validate(pref).model_dump(),
    }


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
