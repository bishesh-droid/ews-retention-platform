"""
Routes Package
-------------
API route handlers.
"""

from fastapi import APIRouter
from . import (
    students,
    predictions,
    llm,
    events,
    features,
    decisions,
    feedback,
    recommendations,
    advisor,
    business,
)

api_router = APIRouter()
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(features.router, prefix="/features", tags=["features"])
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(advisor.router, tags=["AI Academic Advisor"])
api_router.include_router(business.router, tags=["Business Intelligence"])
