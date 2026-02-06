"""
CSV-Driven API Server for EWS Retention Platform.

This server provides only the CSV-driven endpoints without dependencies
on the existing codebase infrastructure. All imports are self-contained.
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import uvicorn

# Direct imports without going through existing route structure
from backend.database import init_db, SessionLocal, Student
from backend.app.services.student_service import StudentService

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize FastAPI app
app = FastAPI(
    title="EWS Retention Platform - CSV API",
    description="CSV-driven analytics and risk scoring API",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all response headers to frontend
)


# ==================== API ENDPOINTS ====================

@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "EWS CSV-Driven API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "overview": "/api/v1/overview",
            "students_list": "/api/v1/students",
            "student_detail": "/api/v1/students/{id}",
            "risk_distribution": "/api/v1/risk-distribution",
            "analytics": "/api/v1/analytics/trends"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/v1/overview")
def get_overview(db: Session = Depends(get_db)):
    """Get dashboard overview statistics."""
    return StudentService.get_overview_stats(db)


# IMPORTANT: Specific routes MUST come before parameterized routes
# Otherwise /students/count matches as /students/{id} with id="count"

@app.get("/api/v1/students/count")
def get_student_count_endpoint(db: Session = Depends(get_db)):
    """Get total count of students (compatibility endpoint)."""
    total = db.query(Student).count()
    return {"total": total}


@app.get("/api/v1/students/")
def get_students_compat(
    limit: int = Query(1500, ge=1, le=2000),
    db: Session = Depends(get_db)
):
    """
    Get students list (compatibility endpoint with array response).
    Note: The /students endpoint (without trailing slash) returns paginated object.
    This one returns just the array for backward compatibility.
    """
    # Call StudentService directly to avoid parameter conflicts
    students = StudentService.get_all_students(db, 0, limit, "risk_score", "desc")
    return students


@app.get("/api/v1/students")
def get_students(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("risk_score"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    risk_min: Optional[float] = Query(None, ge=0, le=100),
    risk_max: Optional[float] = Query(None, ge=0, le=100),
    db: Session = Depends(get_db)
):
    """Get paginated list of students with calculated metrics."""
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


@app.get("/api/v1/students/{student_id}")
def get_student_detail(student_id: str, db: Session = Depends(get_db)):
    """Get detailed information for a single student."""
    student = StudentService.get_student_by_id(db, student_id)
    
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")
    
    return student


@app.get("/api/v1/risk-distribution")
def get_risk_distribution(db: Session = Depends(get_db)):
    """Get risk score distribution and percentiles."""
    students = db.query(Student).all()
    
    if not students:
        return {
            "histogram": [],
            "percentiles": {}
        }
    
    # Calculate risk scores
    risk_scores = []
    for student in students:
        student_data = StudentService.student_to_dict(student)
        metrics = StudentService.calculate_student_metrics(student_data)
        risk_scores.append(metrics['risk_score'])
    
    # Create histogram
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


@app.get("/api/v1/analytics/trends")
def get_analytics_trends(db: Session = Depends(get_db)):
    """Get yearly trends and analytics data."""
    return StudentService.get_analytics_data(db)


# ==================== COMPATIBILITY ENDPOINTS ====================
# These endpoints provide backward compatibility with the existing frontend
# IMPORTANT: Specific routes MUST come before parameterized routes

@app.get("/api/v1/predictions/batch")
def get_batch_predictions(
    limit: int = Query(1500, ge=1, le=2000),
    db: Session = Depends(get_db)
):
    """
    Get batch predictions (compatibility endpoint).
    Returns list of predictions in old format.
    """
    students = StudentService.get_all_students(db, 0, limit, "risk_score", "desc")
    
    predictions = []
    for student in students:
        predictions.append({
            "student_id": student["id"],
            "risk_score": student["risk_score"],
            "engagement_score": student["academic_score"],
            "retention_likelihood": student["retention_likelihood"],
            "attendance": student["attendance_score"],
            "assignments": (student["academic_score"] + student["attendance_score"]) / 2,
            "grades": student["academic_score"],
        })
    
    return predictions


@app.get("/api/v1/predictions/{student_id}")
def get_student_prediction(student_id: str, db: Session = Depends(get_db)):
    """
    Get prediction data for a student (compatibility endpoint).
    Maps new student data structure to old prediction format.
    """
    student = StudentService.get_student_by_id(db, student_id)
    
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")
    
    # Map to old prediction format
    return {
        "student_id": student["id"],
        "risk_score": student["risk_score"],
        "engagement_score": student["academic_score"],  # Map academic to engagement
        "retention_likelihood": student["retention_likelihood"],
        "attendance": student["attendance_score"],
        "assignments": (student["academic_score"] + student["attendance_score"]) / 2,  # Derived
        "grades": student["academic_score"],
        "academic_signal_score": student["academic_score"],
        "engagement_signal_score": student["behavioral_score"],
        "consistency_signal_score": student["stability_score"],
        "intent_signal_score": 100 - student["risk_score"],  # Inverse of risk
        "responsiveness_signal_score": 50.0,  # Stub value
        "model_version": "csv_driven_v1.0",
        "top_risk_factors": f"{student['dominant_risk_factor']}, trend={student['trend']}",
        "prediction_timestamp": "2024-01-01T00:00:00"  # Stub
    }


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    print("\n" + "="*60)
    print("  Initializing EWS CSV-Driven API")
    print("="*60)
    init_db()
    print("  ✓ Database initialized")
    print("  ✓ API ready")
    print("  ✓ Compatibility endpoints enabled")
    print("="*60 + "\n")


if __name__ == "__main__":
    uvicorn.run(
        "csv_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
