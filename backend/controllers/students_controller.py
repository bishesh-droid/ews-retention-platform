"""
Student API Controllers
-----------------------
HTTP handlers delegating to StudentService.

All endpoints require a valid JWT (get_current_user).
Endpoints that expose per-student PII or aggregate institutional data
additionally require a staff-level role (faculty / admin / retention team).
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc

from fastapi import Request

from backend.api.deps import get_db, get_current_user, require_role
from backend.database.models.user import User
from backend.schemas.intervention import Intervention
from backend.database import Prediction, RiskSnapshot, Intervention as DbIntervention
from backend.database.models.student import Student
from backend.database.models.intervention_log import InterventionLog
from backend.presentation.student import build_weekly_summary_response
from backend.services.student_service import StudentService
from backend.services.risk_scoring import RiskScorer
from backend.core.audit_logger import log_data_access, log_bulk_data_access

router = APIRouter()

# Shorthand: any authenticated staff member (not a plain student account).
_STAFF_ROLES = ["faculty", "admin", "retention team"]

# Any logged-in advisor can act on interventions
_ADVISOR_ROLES = ["faculty", "admin", "retention team", "advisor"]


@router.get("/students/{student_id}/interventions", response_model=List[Intervention])
def get_student_interventions(
    student_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_STAFF_ROLES)),
):
    """Get interventions for a specific student. Staff only."""
    # Verify student exists and check department scoping
    target_student = db.query(Student).filter(Student.id == student_id).first()
    if not target_student:
        raise HTTPException(404, "Student not found")

    role = (getattr(_user, "role", "") or "").lower()
    if role == "faculty" and not getattr(_user, "is_superuser", False):
        user_dept = getattr(_user, "department", None)
        if user_dept and target_student.parent_department_name != user_dept:
            raise HTTPException(
                status_code=403,
                detail="Access denied — student is not in your department"
            )

    interventions = StudentService.get_interventions_by_student_id(db, student_id)
    if not interventions:
        raise HTTPException(status_code=404, detail=f"No interventions found for student '{student_id}'")
    return interventions


# =============================================================================
# Intervention Log Endpoints
# =============================================================================

@router.get("/students/{org_id}/intervention-logs")
def get_student_intervention_logs(
    org_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_STAFF_ROLES)),
):
    """
    Returns all InterventionLog records for this student, ordered by recommended_at DESC.
    Used on the student detail page to show advisor history.
    """
    logs = (
        db.query(InterventionLog)
        .filter(InterventionLog.student_org_id == org_id)
        .order_by(desc(InterventionLog.recommended_at))
        .all()
    )

    return [
        {
            "id": log.id,
            "student_org_id": log.student_org_id,
            "recommended_at": log.recommended_at.isoformat() if log.recommended_at else None,
            "intervention_type": log.intervention_type,
            "engagement_pattern": log.engagement_pattern,
            "risk_score_at_recommendation": log.risk_score_at_recommendation,
            "week_number": log.week_number,
            "semester_name": log.semester_name,
            "reviewed": log.reviewed,
            "acted_on": log.acted_on,
            "acted_on_at": log.acted_on_at.isoformat() if log.acted_on_at else None,
            "acted_on_by": log.acted_on_by,
            "dismissed_reason": log.dismissed_reason,
            "notes": log.notes,
            "outcome": log.outcome,
            "outcome_delta": log.outcome_delta,
        }
        for log in logs
    ]


@router.patch("/intervention-logs/{log_id}/act")
def act_on_intervention(
    log_id: int,
    body: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(_ADVISOR_ROLES)),
):
    """
    Mark an intervention as acted upon by the advisor.

    Body: {"notes": str (optional)}
    Sets acted_on=True, acted_on_at=now, acted_on_by=current_user.username
    """
    log = db.query(InterventionLog).filter(InterventionLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Intervention log not found")

    log.acted_on = True
    log.acted_on_at = datetime.utcnow()
    log.acted_on_by = getattr(current_user, "username", "unknown")
    log.reviewed = True

    notes = body.get("notes")
    if notes:
        log.notes = notes

    db.commit()

    return {
        "id": log.id,
        "student_org_id": log.student_org_id,
        "intervention_type": log.intervention_type,
        "acted_on": log.acted_on,
        "acted_on_at": log.acted_on_at.isoformat() if log.acted_on_at else None,
        "acted_on_by": log.acted_on_by,
        "reviewed": log.reviewed,
        "notes": log.notes,
    }


@router.patch("/intervention-logs/{log_id}/dismiss")
def dismiss_intervention(
    log_id: int,
    body: Dict[str, str] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(_ADVISOR_ROLES)),
):
    """
    Dismiss an intervention recommendation.

    Body: {"reason": str}
    Sets acted_on=False, reviewed=True, dismissed_reason=reason
    """
    log = db.query(InterventionLog).filter(InterventionLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Intervention log not found")

    reason = body.get("reason")
    if not reason:
        raise HTTPException(status_code=400, detail="reason is required")

    log.acted_on = False
    log.acted_on_at = datetime.utcnow()
    log.acted_on_by = getattr(current_user, "username", "unknown")
    log.reviewed = True
    log.dismissed_reason = reason

    db.commit()

    return {
        "id": log.id,
        "student_org_id": log.student_org_id,
        "intervention_type": log.intervention_type,
        "acted_on": log.acted_on,
        "reviewed": log.reviewed,
        "dismissed_reason": log.dismissed_reason,
        "acted_on_by": log.acted_on_by,
    }


@router.get("/intervention-logs/pending")
def get_pending_interventions(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_ADVISOR_ROLES)),
    program: Optional[str] = None,
    semester: Optional[str] = None,
    week: Optional[int] = None,
    type: Optional[str] = None,
):
    """
    Returns all pending (reviewed=False) InterventionLog records.
    Used as the advisor's action queue — their to-do list.

    Ordered by risk_score_at_recommendation DESC (highest risk first).
    """
    role = (getattr(_user, "role", "") or "").lower()
    is_superuser = getattr(_user, "is_superuser", False)

    # Scope query to department for faculty users
    query = db.query(InterventionLog).filter(InterventionLog.reviewed.is_(False))

    if role == "faculty" and not is_superuser:
        dept = getattr(_user, "department", None)
        if dept:
            # Join to Student to filter by department
            query = (
                query
                .join(Student, Student.org_defined_id == InterventionLog.student_org_id)
                .filter(Student.parent_department_name == dept)
            )

    if semester:
        query = query.filter(InterventionLog.semester_name == semester)
    if week:
        query = query.filter(InterventionLog.week_number == week)
    if type:
        query = query.filter(InterventionLog.intervention_type == type)

    # Join with Student to get name and support program filter
    query = query.join(Student, InterventionLog.student_org_id == Student.org_defined_id)

    if program:
        query = query.filter(Student.parent_department_name.ilike(f"%{program}%"))

    logs = query.order_by(desc(InterventionLog.risk_score_at_recommendation)).all()

    # Batch lookup students to avoid N+1 and missing relationship issues
    student_org_ids = [log.student_org_id for log in logs]
    student_map = {
        s.org_defined_id: s
        for s in db.query(Student)
        .filter(Student.org_defined_id.in_(student_org_ids))
        .all()
    } if student_org_ids else {}

    return [
        {
            "log_id": log.id,
            "student_org_id": log.student_org_id,
            "student_name": (
                f"{student_map[log.student_org_id].first_name} "
                f"{student_map[log.student_org_id].last_name}"
            ).strip() if log.student_org_id in student_map else "Unknown",
            "risk_score": log.risk_score_at_recommendation,
            "intervention_type": log.intervention_type,
            "engagement_pattern": log.engagement_pattern,
            "recommended_at": log.recommended_at.isoformat() if log.recommended_at else None,
            "week_number": log.week_number,
        }
        for log in logs
    ]


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get dashboard overview statistics. Any authenticated user."""
    return StudentService.get_overview_stats(db)


@router.get("/courses")
def get_courses(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get all courses with content requirements. Any authenticated user."""
    return StudentService.get_courses(db)


@router.get("/courses/{course_id}/engagement")
def get_course_engagement(
    course_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_STAFF_ROLES)),
):
    """Get engagement breakdown for a specific course. Staff only."""
    engagement = StudentService.get_course_engagement(db, course_id)
    if engagement is None:
        raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found")
    return engagement


@router.get("/students", response_model=None)
def get_students(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=2000),
    sort_by: str = Query("risk_score"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    risk_min: Optional[float] = Query(None, ge=0, le=100),
    risk_max: Optional[float] = Query(None, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(_STAFF_ROLES)),
):
    """Get paginated list of students with engagement metrics. Staff only."""
    students = StudentService.get_all_students(
        db,
        skip,
        limit,
        sort_by,
        order,
        risk_min,
        risk_max,
        current_user=current_user,
    )
    total = StudentService.get_student_count_filtered(
        db,
        risk_min=risk_min,
        risk_max=risk_max,
        current_user=current_user,
    )

    # FERPA audit logging: log bulk student data access
    student_ids = [s.get("id") for s in students if s.get("id")]
    log_bulk_data_access(
        db=db,
        user=current_user,
        action="READ",
        resource_type="student",
        resource_ids=student_ids,
        request=request,
    )

    return {
        "students": students,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
    }


@router.get("/students/{student_id}")
def get_student_detail(
    student_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(_STAFF_ROLES)),
):
    """Get detailed engagement information for a single student. Staff only."""
    student = StudentService.get_student_by_id(db, student_id, current_user=current_user)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")

    # FERPA audit logging: log individual student data access
    log_data_access(
        db=db,
        user=current_user,
        action="READ",
        resource_type="student",
        resource_id=student_id,
        request=request,
    )

    return student


@router.get("/students/{student_id}/weekly-summary")
def get_student_weekly_summary(
    student_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(_STAFF_ROLES)),
):
    """Get a lightweight weekly-style summary for the student portal. Staff only."""
    student = StudentService.get_student_by_id(db, student_id, current_user=current_user)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")

    # FERPA audit logging: log enrollment data access
    log_data_access(
        db=db,
        user=current_user,
        action="READ",
        resource_type="student_enrollment",
        resource_id=student_id,
        request=request,
        details={"endpoint": "weekly-summary"},
    )

    enrollments = StudentService._get_enrollment_dicts(db, student_id)

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
        if cur <= 1.0 and prev <= 1.0:
            engagement_improvement = round((cur - prev) * 100.0, 1)
        else:
            engagement_improvement = round(cur - prev, 1)

    return build_weekly_summary_response(student, enrollments, engagement_improvement)


@router.get("/students/{student_id}/risk-trend")
def get_student_risk_trend(
    student_id: str,
    request: Request,
    limit: int = Query(8, ge=2, le=52),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(_STAFF_ROLES)),
):
    """Return risk score trend points for a student. Staff only."""
    # FERPA audit logging: log prediction data access
    log_data_access(
        db=db,
        user=current_user,
        action="READ",
        resource_type="student_prediction",
        resource_id=student_id,
        request=request,
        details={"endpoint": "risk-trend", "limit": limit},
    )

    # Faculty are restricted to their department
    base = db.query(Student.id).filter(Student.id == student_id)
    role = (current_user.role or "").lower()
    if role == "faculty" and not current_user.is_superuser and current_user.department:
        base = base.filter(Student.parent_department_name == current_user.department)

    exists = base.first()
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
        if risk_val <= 1.0:
            risk_val *= 100.0
        points.append({
            "timestamp": ts,
            "risk_score": round(max(0.0, min(100.0, risk_val)), 2),
            "week_number": p.week_number,
            "semester": p.semester_name,
        })

    return {"student_id": student_id, "points": points}


@router.get("/at-risk")
def get_at_risk_students(
    threshold: float = Query(70.0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_STAFF_ROLES)),
):
    """Get students above a risk threshold. Staff only."""
    students = StudentService.get_all_students(db, 0, limit, "risk_score", "desc", risk_min=threshold)
    return {"at_risk_students": students, "count": len(students), "threshold": threshold}


@router.get("/risk-distribution")
def get_risk_distribution(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_STAFF_ROLES)),
):
    """Get risk score distribution and percentiles. Staff only."""
    return StudentService.get_risk_distribution(db)


@router.get("/analytics/trends")
def get_analytics_trends(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_STAFF_ROLES)),
):
    """Get department and course-level analytics. Staff only."""
    return StudentService.get_analytics_data(db)


def _bucket_key(dt: datetime) -> str:
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _normalize_0_100(value: Optional[float]) -> Optional[float]:
    return RiskScorer.normalize_risk_to_0_100(value)


@router.get("/analytics/risk-trends")
def get_cohort_risk_trends(
    weeks: int = Query(8, ge=1, le=52),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_STAFF_ROLES)),
) -> Dict[str, Any]:
    """Cohort-level risk score time series. Staff only."""
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

    return {
        "labels": labels,
        "series": {
            "overall": [avg(buckets[lbl]["overall"]) for lbl in labels],
            "high": [avg(buckets[lbl]["high"]) for lbl in labels],
            "critical": [avg(buckets[lbl]["critical"]) for lbl in labels],
        },
        "points": len(snaps),
    }


@router.get("/analytics/engagement-trends")
def get_cohort_engagement_trends(
    weeks: int = Query(8, ge=1, le=52),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_STAFF_ROLES)),
) -> Dict[str, Any]:
    """Cohort-level engagement score time series. Staff only."""
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
    values = [round(sum(buckets[lbl]) / len(buckets[lbl]), 2) for lbl in labels] if labels else []
    return {"labels": labels, "values": values, "points": len(snaps)}


@router.get("/analytics/performance-trends")
def get_cohort_performance_trends(
    weeks: int = Query(8, ge=1, le=52),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_STAFF_ROLES)),
) -> Dict[str, Any]:
    """Cohort-level performance trend. Staff only."""
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
    values = [round(sum(buckets[lbl]) / len(buckets[lbl]), 3) for lbl in labels] if labels else []
    return {"labels": labels, "values": values, "points": len(preds)}


@router.get("/analytics/intervention-effectiveness")
def get_intervention_effectiveness(
    weeks: int = Query(12, ge=1, le=104),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(_STAFF_ROLES)),
) -> Dict[str, Any]:
    """Intervention effectiveness summary. Staff only."""
    start_date = (datetime.utcnow() - timedelta(weeks=weeks)).date()
    interventions = (
        db.query(DbIntervention)
        .filter(DbIntervention.date >= start_date)
        .order_by(desc(DbIntervention.date), desc(DbIntervention.id))
        .all()
    )

    student_ids = list({i.student_id for i in interventions if i.student_id})
    risk_now = StudentService.get_latest_risk_scores_for_students(db, student_ids)

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
        "status_breakdown": [
            {"status": k, "count": v}
            for k, v in sorted(status_counts.items(), key=lambda x: (-x[1], x[0]))
        ],
        "risk": {
            "before_avg": avg_before,
            "after_avg": avg_after,
            "improvement_avg": avg_improve,
            "n": len(improvements),
        },
    }
