"""
Routes Package
-------------
API route handlers.
"""

from fastapi import APIRouter
from . import (
    auth,
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
    integration,
    student_v1,
    faculty_v1,
    admin_v1,
    retention_v1,
    analytics,
    goals,
    reports,
    ml_routes,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(student_v1.router, prefix="/student", tags=["student"])
api_router.include_router(faculty_v1.router, prefix="/faculty", tags=["faculty"])
api_router.include_router(admin_v1.router, prefix="/admin", tags=["admin"])
api_router.include_router(retention_v1.router, prefix="/retention", tags=["retention"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(goals.router, prefix="/goals", tags=["goals"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(ml_routes.router, prefix="/ml", tags=["Machine Learning"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(features.router, prefix="/features", tags=["features"])
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(advisor.router, tags=["AI Academic Advisor"])
api_router.include_router(business.router, tags=["Business Intelligence"])
api_router.include_router(integration.router, prefix="/integration", tags=["Integration API"])
