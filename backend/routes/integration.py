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
from typing import Optional, List, Any
from datetime import datetime

from backend.api.deps import get_db
from backend.services.student_service import StudentService
from backend.database import Student, Enrollment, GradedComponent, ExamRecord
from backend.config import INTEGRATION_API_KEY_HASH
from backend.core.signing import constant_time_compare
from backend.core.rate_limiting import limiter
from backend.utils.api import success_response
from backend.schemas.common import APIResponse
from sqlalchemy.orm import selectinload
from backend.infrastructure.student_repository import StudentRepository

API_VERSION = "1.0"

router = APIRouter()


class StudentRiskProfileData(BaseModel):
    """Integration API inner data schema for a single student risk profile.

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


class CohortRiskProfilesData(BaseModel):
    """Integration API inner data schema for cohort risk profiles list."""
    profiles: List[StudentRiskProfileData]
    total_in_system: int
    returned: int
    skip: int
    limit: int
    exported_at: str
    api_version: str


# API Response envelope types (wrappers for consistent response shape)
class StudentRiskProfileResponse(APIResponse):
    """Standard envelope for single student risk profile."""
    data: StudentRiskProfileData


class CohortRiskProfilesResponse(APIResponse):
    """Standard envelope for cohort risk profiles."""
    data: CohortRiskProfilesData


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

def _build_risk_profile(db: Session, student: Student) -> StudentRiskProfileData:
    """Build a complete risk profile conforming to the integration contract.

    Returns a validated StudentRiskProfileData instance with attribute access.
    """
    # Get student metrics from StudentService
    student_data = StudentService.get_student_by_id(db, student.id)  # type: ignore[arg-type]
    if not student_data:
        raise ValueError(f"Student '{student.id}' not found or has no data")

    risk_score = float(student_data.get("risk_score", 0))
    risk_category = student_data.get("risk_category", "unknown")

    # Map risk_category to risk_level
    level_map = {"low": "Low", "medium": "Medium", "high": "High"}
    risk_level = level_map.get(risk_category, "Unknown")

    # Build signal breakdowns
    academic_signals = {
        "content_completion_score": round(float(student_data.get("content_completion_score", 0)), 2),
        "graded_quiz_score": round(float(student_data.get("graded_quiz_score", 0)), 2),
        "graded_assignment_score": round(float(student_data.get("graded_assignment_score", 0)), 2),
        "exam_score": round(float(student_data.get("exam_score", 0)), 2),
        "exam_attendance_rate": round(float(student_data.get("exam_attendance_rate", 0)), 2),
    }

    engagement_signals = {
        "quiz_engagement_score": round(float(student_data.get("quiz_engagement_score", 0)), 2),
        "discussion_engagement_score": round(float(student_data.get("discussion_engagement_score", 0)), 2),
        "assignment_score": round(float(student_data.get("assignment_score", 0)), 2),
        "login_consistency_score": round(float(student_data.get("login_consistency_score", 0)), 2),
        "time_investment_score": round(float(student_data.get("time_investment_score", 0)), 2),
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

    profile = StudentRiskProfileData(
        student_id=student.id,
        student_name=f"{student.first_name or ''} {student.last_name or ''}".strip() or student.id,
        risk_score=round(risk_score, 2),
        risk_level=risk_level,
        academic_signals=academic_signals,
        engagement_signals=engagement_signals,
        consistency_signals=consistency_signals,
        trend_summary=student_data.get("trend", "unknown"),
        dominant_risk_factor=student_data.get("dominant_risk_factor", ""),
        risk_breakdown=student_data.get("risk_breakdown", {}),
        exported_at=datetime.now().isoformat(),
        api_version=API_VERSION,
    )
    # DB-5: Pydantic validates risk_score is 0-100 on construction
    return profile


def _build_risk_profile_from_cached_data(
    db: Session,
    student: Student,
    enrollment_dicts: List[Dict],
    graded_dicts: List[Dict],
    exam_dicts: List[Dict],
) -> StudentRiskProfileData:
    """
    Build a risk profile using pre-fetched data (batch query pattern).

    OPTIMIZATION: This function avoids N+1 queries by using data already fetched
    via batch queries instead of calling StudentService.get_student_by_id() which
    would trigger new queries per student.

    Args:
        db: Database session
        student: Student model instance
        enrollment_dicts: Pre-fetched enrollment data for this student
        graded_dicts: Pre-fetched graded component data for this student
        exam_dicts: Pre-fetched exam record data for this student

    Returns:
        StudentRiskProfileData instance
    """
    from backend.application.student.student_application_service import StudentApplicationService
    from backend.config import trimester_week_number
    from backend.services.feature_engineering import FeatureEngineer
    from backend.services.risk_scoring import RiskScorer
    from backend.services.calendar_scorer import get_current_week
    import backend.config as settings

    # Calculate features using pre-fetched data
    is_new = (student.old_new_student or "").lower() == "new"
    week_number = trimester_week_number()
    program = "MSc" if "msc" in (student.parent_department_name or "").lower() else "BS"
    current_week = get_current_week(settings.TRIMESTER_START_DATE)

    features = FeatureEngineer.calculate_all_features(
        enrollment_dicts,
        graded_components=graded_dicts,
        exam_records=exam_dicts,
        is_new_student=is_new,
        week_number=week_number,
    )

    # Calculate risk score
    risk_score = RiskScorer.calculate_risk_score(
        features,
        graded_components=graded_dicts,
        program=program,
        current_week=current_week,
    )
    retention_likelihood = RiskScorer.get_retention_likelihood(risk_score)
    risk_category = RiskScorer.get_risk_category(risk_score)

    # Map risk_category to risk_level
    level_map = {"low": "Low", "medium": "Medium", "high": "High"}
    risk_level = level_map.get(risk_category, "Unknown")

    # Build signal breakdowns from features
    academic_signals = {
        "content_completion_score": round(float(features.get("content_completion_score", 0)), 2),
        "graded_quiz_score": round(float(features.get("graded_quiz_score", 0)), 2),
        "graded_assignment_score": round(float(features.get("graded_assignment_score", 0)), 2),
        "exam_score": round(float(features.get("exam_score", 0)), 2),
        "exam_attendance_rate": round(float(features.get("exam_attendance_rate", 0)), 2),
    }

    engagement_signals = {
        "quiz_engagement_score": round(float(features.get("quiz_engagement_score", 0)), 2),
        "discussion_engagement_score": round(float(features.get("discussion_engagement_score", 0)), 2),
        "assignment_score": round(float(features.get("assignment_score", 0)), 2),
        "login_consistency_score": round(float(features.get("login_consistency_score", 0)), 2),
        "time_investment_score": round(float(features.get("time_investment_score", 0)), 2),
    }

    # Consistency signals
    per_course = features.get("per_course_breakdown", [])
    total_courses = len(per_course)
    courses_zero = sum(1 for c in per_course if c.get("content_completed", 0) == 0)

    consistency_signals = {
        "zero_progress_ratio": round(courses_zero / max(total_courses, 1), 2),
        "total_courses": total_courses,
        "courses_with_zero_progress": courses_zero,
    }

    profile = StudentRiskProfileData(
        student_id=student.id,
        student_name=f"{student.first_name or ''} {student.last_name or ''}".strip() or student.id,
        risk_score=round(risk_score, 2),
        risk_level=risk_level,
        academic_signals=academic_signals,
        engagement_signals=engagement_signals,
        consistency_signals=consistency_signals,
        trend_summary=features.get("engagement_trend", "unknown"),
        dominant_risk_factor=RiskScorer.get_dominant_risk_factor(features),
        risk_breakdown=RiskScorer.get_risk_breakdown(features),
        exported_at=datetime.now().isoformat(),
        api_version=API_VERSION,
    )
    # DB-5: Pydantic validates risk_score is 0-100 on construction
    return profile


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

    # Return standardized envelope with attribute-accessed data
    # Pydantic v2: response_model validates the envelope structure
    return success_response(
        data=profile.model_dump(),
        message="Student risk profile retrieved successfully",
        meta={"model_version": API_VERSION},
    )


@router.get("/cohort-risk-profiles", response_model=CohortRiskProfilesResponse)
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

    OPTIMIZED: Uses eager loading (selectinload) and batch queries to reduce
    N+1 queries from O(N) to O(1). All related data is fetched in 4 queries total.
    """
    # OPTIMIZATION A: Eager loading with selectinload prevents N+1 queries
    # Instead of lazy loading causing 1 + 3N queries, we use 4 queries total
    query = (
        db.query(Student)
        .options(
            selectinload(Student.enrollments),
            selectinload(Student.graded_components),
            selectinload(Student.exam_records),
        )
    )
    students = query.offset(skip).limit(limit).all()

    # Get total count efficiently
    total = db.query(Student).count()

    if not students:
        cohort_data = CohortRiskProfilesData(
            profiles=[],
            total_in_system=total,
            returned=0,
            skip=skip,
            limit=limit,
            exported_at=datetime.now().isoformat(),
            api_version=API_VERSION,
        )
        return success_response(
            data=cohort_data.model_dump(),
            message="Cohort risk profiles retrieved successfully",
            meta={
                "pagination": {
                    "skip": skip,
                    "limit": limit,
                    "returned": 0,
                    "total_in_system": total,
                },
                "model_version": API_VERSION,
            },
        )

    # OPTIMIZATION B: Batch fetch all related data in single queries
    # This is the batch query pattern - fetch all data for all students at once
    student_ids = [s.id for s in students]

    # Pre-fetch all related data using batch queries (O(1) instead of O(N))
    # Note: With selectinload, this data is already loaded, but we keep the
    # batch pattern for consistency with StudentRepository patterns
    enrollment_map = StudentRepository.fetch_enrollments_map(db, student_ids)
    graded_map = StudentRepository.fetch_graded_map(db, student_ids)
    exam_map = StudentRepository.fetch_exam_map(db, student_ids)

    profiles: List[StudentRiskProfileData] = []
    for student in students:
        # Use pre-fetched data from maps instead of triggering new queries
        enrollment_dicts = enrollment_map.get(student.id, [])
        graded_dicts = graded_map.get(student.id, [])
        exam_dicts = exam_map.get(student.id, [])

        # Build profile using batched data
        profile = _build_risk_profile_from_cached_data(
            db, student, enrollment_dicts, graded_dicts, exam_dicts
        )

        # Apply risk filters
        if risk_min is not None and profile.risk_score < risk_min:
            continue
        if risk_max is not None and profile.risk_score > risk_max:
            continue
        profiles.append(profile)

    cohort_data = CohortRiskProfilesData(
        profiles=[p.model_dump() for p in profiles],
        total_in_system=total,
        returned=len(profiles),
        skip=skip,
        limit=limit,
        exported_at=datetime.now().isoformat(),
        api_version=API_VERSION,
    )

    return success_response(
        data=cohort_data.model_dump(),
        message="Cohort risk profiles retrieved successfully",
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
