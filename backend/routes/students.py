"""
Student API Routes for EWS Retention Platform.

All endpoints return data derived from Engagement_Analysis.xlsx
with calculated engagement and risk scores.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.api.deps import get_db
from backend.services.student_service import StudentService
from backend.schemas.intervention import Intervention
from backend.database import Student, Course, Enrollment
from backend.core.security import security_manager

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
    """
    Get dashboard overview statistics.

    Returns:
        - total_students: Unique learner count
        - at_risk_students: Count where risk_score >= 70
        - average_risk_score: Mean risk score (0-100)
        - risk_distribution: Counts by category (low/medium/high)
        - total_enrollments: Student-course enrollment count
        - total_courses: Course offering count
    """
    return StudentService.get_overview_stats(db)


@router.get("/courses")
def get_courses(db: Session = Depends(get_db)):
    """Get all courses with content requirements."""
    courses = db.query(Course).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "semester": c.semester_name,
            "content_required_w1w2": c.content_required_w1w2,
            "content_required_total": c.content_required_total,
            "week1_content": c.week1_content,
            "week2_content": c.week2_content,
        }
        for c in courses
    ]


@router.get("/courses/{course_id}/engagement")
def get_course_engagement(course_id: str, db: Session = Depends(get_db)):
    """Get engagement breakdown for a specific course."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail=f"Course '{course_id}' not found")

    enrollments = db.query(Enrollment).filter(Enrollment.course_id == course_id).all()

    zero_progress = sum(1 for e in enrollments if (e.content_completed or 0) == 0)
    low_progress = sum(1 for e in enrollments
                       if 0 < (e.content_completed or 0) <= ((e.content_required or 1) * 0.1))
    active = len(enrollments) - zero_progress - low_progress

    return {
        "course_id": course.id,
        "course_name": course.name,
        "total_enrolled": len(enrollments),
        "zero_progress": zero_progress,
        "low_progress_0_10": low_progress,
        "active_above_10": active,
        "avg_content_completed": round(
            sum(e.content_completed or 0 for e in enrollments) / max(len(enrollments), 1), 2
        ),
        "avg_time_spent_hours": round(
            sum(e.total_time_spent_seconds or 0 for e in enrollments) / max(len(enrollments), 1) / 3600, 2
        ),
    }


@router.get("/students")
def get_students(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=2000, description="Max records to return"),
    sort_by: str = Query("risk_score", description="Field to sort by"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    risk_min: Optional[float] = Query(None, ge=0, le=100, description="Min risk score"),
    risk_max: Optional[float] = Query(None, ge=0, le=100, description="Max risk score"),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of students with engagement metrics.

    Each student includes:
        - id: Student email
        - risk_score: Calculated 0-100 score
        - risk_category: low/medium/high
        - content_completion_score, quiz_engagement_score, etc.
        - trend: active/declining/inactive
        - per_course_breakdown: engagement per course
    """
    students = StudentService.get_all_students(
        db, skip, limit, sort_by, order, risk_min, risk_max
    )

    total = db.query(Student).count()

    return {
        "students": students,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit
    }


@router.get("/students/{student_id}")
def get_student_detail(student_id: str, db: Session = Depends(get_db)):
    """Get detailed engagement information for a single student."""
    student = StudentService.get_student_by_id(db, student_id)

    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")

    return student


@router.get("/at-risk")
def get_at_risk_students(
    threshold: float = Query(70.0, ge=0, le=100, description="Risk score threshold"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get students above a risk threshold."""
    students = StudentService.get_all_students(
        db, 0, limit, 'risk_score', 'desc', risk_min=threshold
    )
    return {
        "at_risk_students": students,
        "count": len(students),
        "threshold": threshold,
    }


@router.get("/risk-distribution")
def get_risk_distribution(db: Session = Depends(get_db)):
    """Get risk score distribution and percentiles."""
    students = db.query(Student).all()

    if not students:
        return {"histogram": [], "percentiles": {}}

    from backend.services.feature_engineering import FeatureEngineer
    from backend.services.risk_scoring import RiskScorer

    # Pre-fetch enrollments
    all_enrollments = db.query(Enrollment).all()
    enrollment_map = {}
    for e in all_enrollments:
        if e.student_id not in enrollment_map:
            enrollment_map[e.student_id] = []
        enrollment_map[e.student_id].append({
            'content_completed': e.content_completed,
            'content_required': e.content_required,
            'content_required_w1w2': e.content_required_w1w2,
            'quiz_completed': e.quiz_completed,
            'total_quiz_attempts': e.total_quiz_attempts,
            'discussion_posts_created': e.discussion_posts_created,
            'discussion_post_replies': e.discussion_post_replies,
            'discussion_posts_read': e.discussion_posts_read,
            'num_assignment_submissions': e.num_assignment_submissions,
            'total_time_spent_seconds': e.total_time_spent_seconds,
            'num_logins': e.num_logins,
        })

    risk_scores = []
    for student in students:
        enrollments = enrollment_map.get(student.id, [])
        features = FeatureEngineer.calculate_all_features(enrollments)
        risk_score = RiskScorer.calculate_risk_score(features)
        risk_scores.append(risk_score)

    # Histogram
    buckets = {}
    for score in risk_scores:
        bucket = int(score // 10) * 10
        bucket_label = f"{bucket}-{bucket + 10}"
        buckets[bucket_label] = buckets.get(bucket_label, 0) + 1

    histogram = [{"range": k, "count": v} for k, v in sorted(buckets.items())]

    # Percentiles
    sorted_scores = sorted(risk_scores)
    n = len(sorted_scores)

    def percentile(p):
        k = (n - 1) * p / 100
        f = int(k)
        c = k - f
        if f + 1 < n:
            return round(sorted_scores[f] + c * (sorted_scores[f + 1] - sorted_scores[f]), 2)
        return round(sorted_scores[f], 2)

    return {
        "histogram": histogram,
        "percentiles": {
            "p25": percentile(25),
            "p50": percentile(50),
            "p75": percentile(75),
            "p90": percentile(90),
        },
    }


@router.get("/analytics/trends")
def get_analytics_trends(db: Session = Depends(get_db)):
    """Get department and course-level analytics."""
    return StudentService.get_analytics_data(db)
