"""
ML prediction routes
--------------------
Thin HTTP layer delegating all prediction logic to services.
Ensures that heavy ML inference runs off the main event loop and
is protected by a timeout.
"""

from typing import List
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.ml_service import ml_service
from backend.utils.api import success_response

router = APIRouter()


PREDICTION_TIMEOUT_SECONDS = 5.0


class MLPredictionResponse(BaseModel):
    student_id: str
    dropout_probability: float | None = None
    risk_level: str | None = None
    top_risk_factors: List[str] | None = None
    predictions: dict | None = None
    features: dict | None = None
    error: str | None = None


class BatchPredictionRequest(BaseModel):
    student_ids: List[str]


@router.get("/predict/{student_id}", response_model=MLPredictionResponse)
async def predict_student_risk(student_id: str):
    """
    Get dropout prediction for a specific student.
    ML inference is executed in a worker thread with a timeout so that the
    FastAPI event loop remains responsive.
    """
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(ml_service.predict_student_cached, student_id),
            timeout=PREDICTION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Prediction timed out")

    error = result.get("error")
    if error:
        if error == "Student not found in processed data":
            raise HTTPException(status_code=404, detail="Student not found")
        raise HTTPException(status_code=500, detail=error)

    return success_response(result)


@router.post("/predict-batch", response_model=List[MLPredictionResponse])
async def predict_student_batch(request: BatchPredictionRequest):
    """
    Get dropout prediction for multiple students at once.
    ML inference is executed off the main thread and protected by a timeout.
    """
    try:
        results = await asyncio.wait_for(
            asyncio.to_thread(ml_service.batch_predict, request.student_ids),
            timeout=PREDICTION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Batch prediction timed out")

    valid_results = [r for r in results if "error" not in r]
    return success_response(valid_results)


@router.get("/cohort-risk")
async def get_cohort_risk():
    """
    Get aggregate risk metrics for the cohort.
    Currently returns static placeholder values.
    """
    payload = {
        "average_risk": 0.45,
        "high_risk_count": 120,
        "total_students": 1500,
    }
    return success_response(payload)


@router.get("/trend-analysis")
async def get_trend_analysis():
    """
    Get risk trend over time.
    Currently returns static placeholder values.
    """
    payload = {"monthly_trend": [0.4, 0.42, 0.45, 0.44]}
    return success_response(payload)
