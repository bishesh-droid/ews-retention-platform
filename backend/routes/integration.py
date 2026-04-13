"""
Integration API Routes — Data Contract for External Consumers
-------------------------------------------------------------
Read-only endpoints that expose structured student risk profiles
for consumption by the AI Academic Advisor (or any authorized service).

These endpoints do NOT modify any EWS data.
Authentication: X-API-Key-Hash + X-Timestamp headers with replay protection.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from backend.api.deps import get_db
from backend.services.student_service import StudentService
from backend.database import Student
from backend.config import INTEGRATION_API_KEY_HASH
from backend.core.signing import constant_time_compare
from backend.core.rate_limiting import limiter
from backend.utils.api import success_response

API_VERSION = "1.0"

router = APIRouter()


class StudentRiskProfileResponse(BaseModel):
    """Integration API response schema for student risk profile.
    
    DB-5: risk_score is ALWAYS on a 0-100 scale (not 0-1).
    """
    student_id: str
    student_name: str
    risk_score: float
    risk_level: str
    academic_signals: dict
    engagement_signals: dict
    consistency_signals: dict
    trend_summary: str
    dominant_risk_factor: str
    risk_breakdown: dict
    exported_at: str
    api_version: str

    @field_validator('risk_score')
    @classmethod
    def validate_risk_score(cls, v: float) -> float:
        """Validate risk_score is within 0-100 scale."""
        if not (0.0 <= v <= 100.0):
            raise ValueError(f'risk_score must be between 0 and 100, got {v}')
        return v


# ─── Authentication ─────────────────────────────────────────────────────────

async def verify_integration_key(
    request: Request,
    x_api_key_hash: str = Header(..., alias="X-API-Key-Hash"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
):
    """
    Validate signed request with timestamp-based replay protection.

    Client must send:
      - X-API-Key-Hash: SHA-256 hash of the raw API key
      - X-Timestamp: Unix timestamp (seconds since epoch)
    """
    if not INTEGRATION_API_KEY_HASH:
        raise HTTPException(
            status_code=503,
            detail="Integration API is not configured. Set INTEGRATION_API_KEY_HASH env var."
        )

    # Verify key hash matches (constant-time comparison)
    if not constant_time_compare(x_api_key_hash, INTEGRATION_API_KEY_HASH):
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Verify timestamp is within window (prevents replay attacks)
    try:
        ts = int(x_timestamp)
        if abs(time.time() - ts) > 300:  # 5-minute window
            raise HTTPException(status_code=403, detail="Request timestamp expired")
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid timestamp")

    return x_api_key_hash


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_risk_profile(db: Session, student: Student) -> dict:
    """Build a complete risk profile dict conforming to the integration contract."""
    # Get student metrics from StudentService
    student_data = StudentService.get_student_by_id(db, student.id)  # type: ignore[arg-type]
    if not student_data:
        return {}  # type: ignore[return-value]

    risk_score = student_data.get("risk_score", 0)
    risk_category = student_data.get("risk_category", "unknown")

    # Map risk_category to risk_level
    level_map = {"low": "Low", "medium": "Medium", "high": "High"}
    risk_level = level_map.get(risk_category, "Unknown")

    # Build signal breakdowns
    academic_signals = {
        "content_completion_score": round(student_data.get("content_completion_score", 0), 2),
        "graded_quiz_score": round(student_data.get("graded_quiz_score", 0), 2),
        "graded_assignment_score": round(student_data.get("graded_assignment_score", 0), 2),
        "exam_score": round(student_data.get("exam_score", 0), 2),
        "exam_attendance_rate": round(student_data.get("exam_attendance_rate", 0), 2),
    }

    engagement_signals = {
        "quiz_engagement_score": round(student_data.get("quiz_engagement_score", 0), 2),
        "discussion_engagement_score": round(student_data.get("discussion_engagement_score", 0), 2),
        "assignment_score": round(student_data.get("assignment_score", 0), 2),
        "login_consistency_score": round(student_data.get("login_consistency_score", 0), 2),
        "time_investment_score": round(student_data.get("time_investment_score", 0), 2),
    }

    # Consistency signals
    per_course = student_data.get("per_course_breakdown", [])
    total_courses = len(per_course)
    courses_zero = sum(1 for c in per_course if c.get("content_completed", 0) == 0)

    consistency_signals = {
        "zero_progress_ratio": round(courses_zero / max(total_courses, 1), 2),
        "total_courses": total_courses,
        "courses_with_zero_progress": courses_zero,
    }

    data = {
        "student_id": student.id,
        "student_name": f"{student.first_name or ''} {student.last_name or ''}".strip() or student.id,
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "academic_signals": academic_signals,
        "engagement_signals": engagement_signals,
        "consistency_signals": consistency_signals,
        "trend_summary": student_data.get("trend", "unknown"),
        "dominant_risk_factor": student_data.get("dominant_risk_factor", ""),
        "risk_breakdown": student_data.get("risk_breakdown", {}),
        "exported_at": datetime.now().isoformat(),
        "api_version": API_VERSION,
    }
    # Return validated Pydantic model (DB-5: validates risk_score is 0-100)
    return StudentRiskProfileResponse(**data)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/student-risk-profile/{student_id}", response_model=StudentRiskProfileResponse)
@limiter.limit("60/minute")
def get_student_risk_profile(
    request: Request,
    student_id: str,
    db: Session = Depends(get_db),
    _key: str = Depends(verify_integration_key),
):
    """
    Get full risk profile for a single student.

    Returns the strict data contract consumed by the AI Academic Advisor.
    This endpoint is read-only and does not modify any EWS data.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")

    profile = _build_risk_profile(db, student)
    if not profile:
        raise HTTPException(status_code=500, detail="Failed to build risk profile")

    # Return validated Pydantic model (DB-5: response_model validates risk_score is 0-100)
    return profile


@router.get("/cohort-risk-profiles")
@limiter.limit("10/minute")
def get_cohort_risk_profiles(
    request: Request,
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Max records"),
    risk_min: Optional[float] = Query(None, ge=0, le=100),
    risk_max: Optional[float] = Query(None, ge=0, le=100),
    db: Session = Depends(get_db),
    _key: str = Depends(verify_integration_key),
):
    """
    Get paginated batch of student risk profiles.

    Used by the AI Academic Advisor for cohort-level analysis.
    """
    query = db.query(Student)
    students = query.offset(skip).limit(limit).all()
    total = db.query(Student).count()

    profiles = []
    for student in students:
        profile = _build_risk_profile(db, student)
        if profile:
            # Apply risk filters after building profile
            score = profile["risk_score"]
            if risk_min is not None and score < risk_min:
                continue
            if risk_max is not None and score > risk_max:
                continue
            profiles.append(profile)

    data = {
        "profiles": profiles,
        "total_in_system": total,
        "returned": len(profiles),
        "skip": skip,
        "limit": limit,
        "exported_at": datetime.now().isoformat(),
        "api_version": API_VERSION,
    }
    return success_response(
        data,
        message="Cohort risk profiles",
        meta={
            "pagination": {
                "skip": skip,
                "limit": limit,
                "returned": len(profiles),
                "total_in_system": total,
            },
            "model_version": API_VERSION,
        },
    )
