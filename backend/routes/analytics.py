from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from backend.app.api import deps
from backend.services.analytics_service import AnalyticsService

router = APIRouter()

@router.get("/risk/trend/{student_id}")
def get_student_risk_trend(
    student_id: str,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(deps.get_db),
    current_user: deps.User = Depends(deps.require_role(["Faculty", "Retention Team", "Admin"]))
):
    """
    Get detailed risk trend metrics for a specific student.
    """
    return AnalyticsService.get_risk_trends(db, student_id, days)

@router.get("/analytics/top-risk-velocity")
def get_top_risk_velocity(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(deps.get_db),
    current_user: deps.User = Depends(deps.require_role(["Faculty", "Retention Team", "Admin"]))
):
    """
    Get top students with the highest risk velocity.
    """
    return AnalyticsService.get_top_risk_velocity(db, limit)

@router.get("/analytics/kpis")
def get_kpi_cards(
    db: Session = Depends(deps.get_db),
    current_user: deps.User = Depends(deps.require_role(["Faculty", "Retention Team", "Admin"]))
):
    """
    Get aggregated KPI metrics for dashboard cards.
    """
    return AnalyticsService.get_kpi_cards(db)

@router.get("/analytics/drill-down")
def get_drill_down(
    metric: str = Query(..., description="The KPI metric to drill down into"),
    db: Session = Depends(deps.get_db),
    current_user: deps.User = Depends(deps.require_role(["Faculty", "Retention Team", "Admin"]))
):
    """
    Get detailed data for a specific KPI metric.
    """
    return AnalyticsService.get_drill_down(db, metric)
