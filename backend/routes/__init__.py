"""
Routes Package
-------------
API route handlers.

DEAD ROUTE AUDIT (CROSS-5):
- predictions: Legacy endpoint — not called by frontend. Consider disabling before production.
- events: Unused — no frontend calls. Remove in next cleanup sprint.
- feedback: Placeholder — not fully implemented. Remove before production.
"""

from fastapi import APIRouter
from . import (
    auth,
    students,
    # TODO: re-enable when implemented - predictions router is legacy and unused
    # predictions,
    llm,
    # TODO: re-enable when implemented - events router is unused
    # events,
    features,
    decisions,
    # TODO: re-enable when implemented - feedback router is placeholder
    # feedback,
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
    monitoring,
    interventions,
    audit,
)

api_router = APIRouter()
# API-2: Auth routes at root /auth (not /api/v1/auth) to avoid prefix conflict
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(student_v1.router, prefix="/student", tags=["student"])
api_router.include_router(faculty_v1.router, prefix="/faculty", tags=["faculty"])
api_router.include_router(admin_v1.router, prefix="/admin", tags=["admin"])
api_router.include_router(audit.router, prefix="/audit-log", tags=["audit"])  # FERPA compliance
api_router.include_router(retention_v1.router, prefix="/retention", tags=["retention"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(goals.router, prefix="/goals", tags=["goals"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
# TODO: re-enable when implemented - predictions router is legacy and unused
# api_router.include_router(predictions.router, prefix="/predictions",
#                           tags=["predictions"])  # Legacy — not called by frontend (CROSS-5)
api_router.include_router(ml_routes.router, prefix="/ml", tags=["Machine Learning"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
# TODO: re-enable when implemented - events router is unused
# api_router.include_router(events.router, prefix="/events", tags=["events"])
# Unused — remove in cleanup sprint (CROSS-5)
api_router.include_router(features.router, prefix="/features", tags=["features"])
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
# TODO: re-enable when implemented - feedback router is placeholder
# api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
# Placeholder — not implemented (CROSS-5)
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
api_router.include_router(advisor.router, tags=["AI Academic Advisor"])
api_router.include_router(business.router, tags=["Business Intelligence"])
api_router.include_router(integration.router, prefix="/integration", tags=["Integration API"])
api_router.include_router(monitoring.router, tags=["monitoring"])
api_router.include_router(interventions.router, tags=["interventions"])
