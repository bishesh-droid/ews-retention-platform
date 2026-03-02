"""
Student API Controllers
-----------------------
HTTP handlers delegating to StudentService.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.api.deps import get_db
from backend.schemas.intervention import Intervention
from backend.database import Student, Prediction, RiskSnapshot, Intervention as DbIntervention
from backend.services.student_service import StudentService


router = APIRouter()


@router.get("/students/{student_id}/interventions", response_model=List[Intervention])
def get_student_interventions(student_id: str, db: Session = Depends(get_db)):
    """Get interventions for a specific student."""
    interventions = StudentService.get_interventions_by_student_id(db, student_id)
    if not interventions:
        raise HTTPException(status_code=404, detail=f"No interventions found for student '{student_id}'")
    return interventions


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """Get dashboard overview statistics."""
    return StudentService.get_overview_stats(db)


@router.get("/courses")
def get_courses(db: Session = Depends(get_db)):
    """Get all courses with content requirements."""
    return StudentService.get_courses(db)


@router.get("/courses/{course_id}/engagement")
def get_course_engagement(course_id: str, db: Session = Depends(get_db)):
    """Get engagement breakdown for a specific course."""
    engagement = StudentService.get_course_engagement(db, course_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found")
    return engagement


@router.get("/students")
def get_students(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=2000, description="Max records to return"),
    sort_by: str = Query("risk_score", description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    risk_min: Optional[float] = Query(None, ge=0, le=100, description="Min risk score"),
    risk_max: Optional[float] = Query(None, ge=0, le=100, description="Max risk score"),
    db: Session = Depends(get_db),
):
    """Get paginated list of students with engagement metrics."""
    students = StudentService.get_all_students(
        db, skip, limit, sort_by, order, risk_min, risk_max
    )

    total = db.query(Student).count()

    return {
        "students": students,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
    }


@router.get("/students/{student_id}")
def get_student_detail(student_id: str, db: Session = Depends(get_db)):
    """Get detailed engagement information for a single student."""
    student = StudentService.get_student_by_id(db, student_id)

    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")

    return student


@router.get("/students/{student_id}/weekly-summary")
def get_student_weekly_summary(student_id: str, db: Session = Depends(get_db)):
    """
    Get a lightweight weekly-style summary for the student portal.

    We derive summary metrics from current enrollment totals and (when available)
    the most recent stored predictions. This endpoint intentionally returns a
    stable, UI-friendly payload for the portal components.
    """
    student = StudentService.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")

    enrollments = StudentService._get_enrollment_dicts(db, student_id)

    total_study_minutes = int(
        round(sum((e.get("total_time_spent_seconds") or 0) for e in enrollments) / 60)
    )
    resources_viewed = int(sum((e.get("content_completed") or 0) for e in enrollments))
    assignments_completed = int(sum((e.get("num_assignment_submissions") or 0) for e in enrollments))

    # Attendance rate as 0..1 (student UI expects ratio)
    attendance_rate_pct = float(student.get("exam_attendance_rate") or 0)
    attendance_rate = max(0.0, min(1.0, attendance_rate_pct / 100.0))

    # Engagement improvement: use last two stored predictions if present
    engagement_improvement = 0.0
    preds = (
        db.query(Prediction)
        .filter(Prediction.student_id == student_id)
        .order_by(desc(Prediction.prediction_timestamp))
        .limit(2)
        .all()
    )
    if len(preds) == 2 and preds[0].engagement_score is not None and preds[1].engagement_score is not None:
        cur = float(preds[0].engagement_score)
        prev = float(preds[1].engagement_score)
        # Normalize: if stored as 0..1, convert to percent points
        if cur <= 1.0 and prev <= 1.0:
            engagement_improvement = round((cur - prev) * 100.0, 1)
        else:
            engagement_improvement = round(cur - prev, 1)

    payload = {
        "assignmentsCompleted": assignments_completed,
        "attendanceRate": round(attendance_rate, 4),
        "engagementImprovement": engagement_improvement,
        "missedAssignments": 0,
        "lowEngagementDays": 0,
        "totalStudyTimeMinutes": total_study_minutes,
        "facultyInteractions": 0,
        "resourcesViewed": resources_viewed,
    }

    return payload


@router.get("/students/{student_id}/risk-trend")
def get_student_risk_trend(
    student_id: str,
    limit: int = Query(8, ge=2, le=52, description="Number of points to return"),
    db: Session = Depends(get_db),
):
    """
    Return risk score trend points for the portal.

    Data source: stored `predictions` table (if populated). If there is no
    history, returns an empty list.
    """
    # Ensure student exists to provide a consistent 404 behavior
    exists = db.query(Student.id).filter(Student.id == student_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")

    preds = (
        db.query(Prediction)
        .filter(Prediction.student_id == student_id)
        .order_by(desc(Prediction.prediction_timestamp))
        .limit(limit)
        .all()
    )

    points = []
    for p in reversed(preds):
        ts = p.prediction_timestamp.isoformat() if p.prediction_timestamp else None
        raw_risk = p.risk_score
        if raw_risk is None:
            continue
        risk_val = float(raw_risk)
        # Normalize: if stored as 0..1 probability, convert to 0..100 percent
        if risk_val <= 1.0:
            risk_val *= 100.0
        points.append(
            {
                "timestamp": ts,
                "risk_score": round(max(0.0, min(100.0, risk_val)), 2),
            }
        )

    return {"student_id": student_id, "points": points}


@router.get("/at-risk")
def get_at_risk_students(
    threshold: float = Query(70.0, ge=0, le=100, description="Risk score threshold"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get students above a risk threshold."""
    students = StudentService.get_all_students(
        db, 0, limit, "risk_score", "desc", risk_min=threshold
    )
    return {
        "at_risk_students": students,
        "count": len(students),
        "threshold": threshold,
    }


@router.get("/risk-distribution")
def get_risk_distribution(db: Session = Depends(get_db)):
    """Get risk score distribution and percentiles."""
    return StudentService.get_risk_distribution(db)


@router.get("/analytics/trends")
def get_analytics_trends(db: Session = Depends(get_db)):
    """Get department and course-level analytics."""
    return StudentService.get_analytics_data(db)


def _bucket_key(dt: datetime) -> str:
    # ISO week bucket: e.g. "2026-W09"
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _normalize_0_100(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(value)
    except Exception:
        return None
    if not (v == v):  # NaN
        return None
    if v <= 1.0:
        v *= 100.0
    return max(0.0, min(100.0, v))


@router.get("/analytics/risk-trends")
def get_cohort_risk_trends(
    weeks: int = Query(8, ge=1, le=52),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Cohort-level risk score time series derived from `risk_snapshots`.

    Returns empty series if no snapshots exist.
    """
    start = datetime.utcnow() - timedelta(weeks=weeks)
    snaps = (
        db.query(RiskSnapshot)
        .filter(RiskSnapshot.timestamp >= start)
        .order_by(RiskSnapshot.timestamp.asc())
        .all()
    )

    buckets: Dict[str, Dict[str, List[float]]] = {}
    for s in snaps:
        key = _bucket_key(s.timestamp)
        risk = _normalize_0_100(s.risk_score)
        if risk is None:
            continue
        if key not in buckets:
            buckets[key] = {"overall": [], "high": [], "critical": []}
        buckets[key]["overall"].append(risk)
        if risk >= 60:
            buckets[key]["high"].append(risk)
        if risk >= 80:
            buckets[key]["critical"].append(risk)

    labels = sorted(buckets.keys())

    def avg(arr: List[float]) -> Optional[float]:
        return round(sum(arr) / len(arr), 2) if arr else None

    payload = {
        "labels": labels,
        "series": {
            "overall": [avg(buckets[l]["overall"]) for l in labels],
            "high": [avg(buckets[l]["high"]) for l in labels],
            "critical": [avg(buckets[l]["critical"]) for l in labels],
        },
        "points": len(snaps),
    }
    return payload


@router.get("/analytics/engagement-trends")
def get_cohort_engagement_trends(
    weeks: int = Query(8, ge=1, le=52),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Cohort-level engagement score time series derived from `risk_snapshots.engagement_score`.
    """
    start = datetime.utcnow() - timedelta(weeks=weeks)
    snaps = (
        db.query(RiskSnapshot)
        .filter(RiskSnapshot.timestamp >= start)
        .order_by(RiskSnapshot.timestamp.asc())
        .all()
    )

    buckets: Dict[str, List[float]] = {}
    for s in snaps:
        key = _bucket_key(s.timestamp)
        eng = _normalize_0_100(s.engagement_score)
        if eng is None:
            continue
        buckets.setdefault(key, []).append(eng)

    labels = sorted(buckets.keys())
    values = [round(sum(buckets[l]) / len(buckets[l]), 2) for l in labels] if labels else []

    return {"labels": labels, "values": values, "points": len(snaps)}


@router.get("/analytics/performance-trends")
def get_cohort_performance_trends(
    weeks: int = Query(8, ge=1, le=52),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Cohort-level performance trend derived from stored `predictions.grades` (if available).
    """
    start = datetime.utcnow() - timedelta(weeks=weeks)
    preds = (
        db.query(Prediction)
        .filter(Prediction.prediction_timestamp >= start)
        .order_by(Prediction.prediction_timestamp.asc())
        .all()
    )

    buckets: Dict[str, List[float]] = {}
    for p in preds:
        if p.prediction_timestamp is None:
            continue
        g = p.grades
        if g is None:
            continue
        try:
            val = float(g)
        except Exception:
            continue
        if not (val == val):
            continue
        key = _bucket_key(p.prediction_timestamp)
        buckets.setdefault(key, []).append(val)

    labels = sorted(buckets.keys())
    values = [round(sum(buckets[l]) / len(buckets[l]), 3) for l in labels] if labels else []
    return {"labels": labels, "values": values, "points": len(preds)}


@router.get("/analytics/intervention-effectiveness")
def get_intervention_effectiveness(
    weeks: int = Query(12, ge=1, le=104),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Intervention effectiveness summary using real intervention records.

    Currently supports:
    - status breakdown
    - average risk improvement where `risk_score_at_trigger` is recorded
    """
    start_date = (datetime.utcnow() - timedelta(weeks=weeks)).date()
    interventions = (
        db.query(DbIntervention)
        .filter(DbIntervention.date >= start_date)
        .order_by(desc(DbIntervention.date), desc(DbIntervention.id))
        .all()
    )

    # Current risk map from computed student metrics
    students = StudentService.get_all_students(db, skip=0, limit=2000, sort_by="risk_score", order="desc")
    risk_now = {s["id"]: (s.get("risk_score") or 0) for s in students}

    status_counts: Dict[str, int] = {}
    improvements: List[float] = []
    before_vals: List[float] = []
    after_vals: List[float] = []

    for i in interventions:
        st = i.status or "Pending"
        status_counts[st] = status_counts.get(st, 0) + 1

        before = i.risk_score_at_trigger
        after = risk_now.get(i.student_id)
        if before is None or after is None:
            continue
        try:
            b = float(before)
            a = float(after)
        except Exception:
            continue
        if b <= 1.0:
            b *= 100.0
        improvements.append(b - a)
        before_vals.append(b)
        after_vals.append(a)

    avg_before = round(sum(before_vals) / len(before_vals), 2) if before_vals else None
    avg_after = round(sum(after_vals) / len(after_vals), 2) if after_vals else None
    avg_improve = round(sum(improvements) / len(improvements), 2) if improvements else None

    return {
        "window_weeks": weeks,
        "total_interventions": len(interventions),
        "status_breakdown": [{"status": k, "count": v} for k, v in sorted(status_counts.items(), key=lambda x: (-x[1], x[0]))],
        "risk": {
            "before_avg": avg_before,
            "after_avg": avg_after,
            "improvement_avg": avg_improve,
            "n": len(improvements),
        },
    }

