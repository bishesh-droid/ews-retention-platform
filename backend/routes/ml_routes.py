from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from backend.services.ml_service import ml_service
from pydantic import BaseModel

router = APIRouter()

class MLPredictionResponse(BaseModel):
    student_id: str
    dropout_probability: Optional[float] = None
    risk_level: Optional[str] = None
    top_risk_factors: Optional[List[str]] = None
    predictions: Optional[dict] = None
    features: Optional[dict] = None
    error: Optional[str] = None

@router.get("/predict/{student_id}", response_model=MLPredictionResponse)
async def predict_student_risk(student_id: str):
    """
    Get dropout prediction for a specific student.
    """
    result = ml_service.predict_student(student_id)
    if "error" in result:
        # If student not found, we might return 404, or just the error object
        if result["error"] == "Student not found in processed data":
             raise HTTPException(status_code=404, detail="Student not found")
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@router.get("/cohort-risk")
async def get_cohort_risk():
    """
    Get aggregate risk metrics for the cohort.
    (Mock implementation / Placeholder for now)
    """
    return {
        "average_risk": 0.45,
        "high_risk_count": 120,
        "total_students": 1500
    }

@router.get("/trend-analysis")
async def get_trend_analysis():
    """
    Get risk trend over time.
    (Mock implementation)
    """
    return {
        "monthly_trend": [0.4, 0.42, 0.45, 0.44]
    }
