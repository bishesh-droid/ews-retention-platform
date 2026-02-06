"""
CSV-Driven Student API Routes for EWS Retention Platform.

All endpoints return data derived directly from simulated_data.csv
with calculated risk scores and metrics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.api.deps import get_db
from backend.app.services.student_service import StudentService
from backend.app.schemas.intervention import Intervention

router = APIRouter()


@router.get("/students/{student_id}/interventions", response_model=List[Intervention])
def get_student_interventions(student_id: str, db: Session = Depends(get_db)):
    """
    Get interventions for a specific student.
    
    Args:
        student_id: The ID of the student.
        db: Database session.
        
    Returns:
        A list of Intervention objects for the student.
    """
    interventions = StudentService.get_interventions_by_student_id(db, student_id)
    if not interventions:
        raise HTTPException(status_code=404, detail=f"No interventions found for student '{student_id}'")
    return interventions


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """
    Get dashboard overview statistics.
    
    Returns:
        - total_students: Count of CSV rows
        - at_risk_students: Count where risk_score >= 70
        - average_risk_score: Mean risk score (0-100)
        - risk_distribution: Counts by category (low/medium/high)
        - graduation_rate: Percentage who graduated (nograd==0)
    """
    return StudentService.get_overview_stats(db)


@router.get("/students")
def get_students(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=2000, description="Max records to return"),
    sort_by: str = Query("risk_score", description="Field to sort by"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    risk_min: Optional[float] = Query(None, ge=0, le=100, description="Min risk score"),
    risk_max: Optional[float] = Query(None, ge=0, le=100, description="Max risk score"),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of students with calculated metrics.
    
    Each student includes:
        - id: Student name from CSV
        - risk_score: Calculated 0-100 score
        - risk_category: low/medium/high
        - attendance_score: Derived from absrate1-7
        - academic_score: Derived from q1mpa1-q4mpa7
        - behavioral_score: Derived from nsusp1-7
        - stability_score: Derived from mobility1-7
        - trend: improving/declining/stable
        - graduated: Boolean from nograd column
    """
    students = StudentService.get_all_students(
        db, skip, limit, sort_by, order, risk_min, risk_max
    )
    
    # Get total count for pagination
    from database import Student
    total = db.query(Student).count()
    
    return {
        "students": students,
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit
    }


@router.get("/students/{student_id}")
def get_student_detail(student_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information for a single student.
    
    Returns all calculated metrics plus year-by-year breakdown
    showing CSV columns per year.
    """
    student = StudentService.get_student_by_id(db, student_id)
    
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")
    
    return student


@router.get("/risk-distribution")
def get_risk_distribution(db: Session = Depends(get_db)):
    """
    Get risk score distribution and percentiles.
    
    Returns histogram buckets and statistical percentiles.
    """
    from database import Student
    students = db.query(Student).all()
    
    if not students:
        return {
            "histogram": [],
            "percentiles": {}
        }
    
    # Calculate risk scores for all students
    risk_scores = []
    for student in students:
        student_data = StudentService.student_to_dict(student)
        metrics = StudentService.calculate_student_metrics(student_data)
        risk_scores.append(metrics['risk_score'])
    
    # Create histogram buckets
    buckets = {}
    for score in risk_scores:
        bucket = int(score // 10) * 10
        bucket_label = f"{bucket}-{bucket+10}"
        buckets[bucket_label] = buckets.get(bucket_label, 0) + 1
    
    histogram = [
        {"range": k, "count": v}
        for k, v in sorted(buckets.items())
    ]
    
    # Calculate percentiles
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
            "p90": percentile(90)
        }
    }


@router.get("/analytics/trends")
def get_analytics_trends(db: Session = Depends(get_db)):
    """
    Get yearly trends and analytics data.
    
    Returns:
        - attendance_by_year: Average attendance per year (1-7)
        - academic_by_year: Average MPA per year (1-7)
    """
    return StudentService.get_analytics_data(db)
