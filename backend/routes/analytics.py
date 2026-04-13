from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api import deps
from backend.core.constants import Role
from backend.schemas.common import APIResponse
from backend.services.analytics_service import AnalyticsService
from backend.utils.api import success_response

router = APIRouter()


@router.get("/risk/trend/{student_id}", response_model=APIResponse)
def get_student_risk_trend(
    student_id: str,
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(deps.get_db),
    current_user: deps.User = Depends(deps.require_role([Role.FACULTY, Role.RETENTION_TEAM, Role.ADMIN]))
):
    """
    Get detailed risk trend metrics for a specific student.
    """
    data = AnalyticsService.get_risk_trends(db, student_id, days)
    return success_response(data, message="Student risk trend")


@router.get("/analytics/top-risk-velocity", response_model=APIResponse)
def get_top_risk_velocity(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(deps.get_db),
    current_user: deps.User = Depends(deps.require_role([Role.FACULTY, Role.RETENTION_TEAM, Role.ADMIN]))
):
    """
    Get top students with the highest risk velocity.
    """
    data = AnalyticsService.get_top_risk_velocity(db, limit)
    return success_response(
        data,
        message="Top risk velocity students",
        meta={"pagination": {"limit": limit}},
    )


@router.get("/analytics/kpis", response_model=APIResponse)
def get_kpi_cards(
    db: Session = Depends(deps.get_db),
    current_user: deps.User = Depends(deps.require_role([Role.FACULTY, Role.RETENTION_TEAM, Role.ADMIN]))
):
    """
    Get aggregated KPI metrics for dashboard cards.
    """
    data = AnalyticsService.get_kpi_cards(db)
    return success_response(data, message="KPI cards")


@router.get("/analytics/drill-down", response_model=APIResponse)
def get_drill_down(
    metric: str = Query(..., description="The KPI metric to drill down into"),
    db: Session = Depends(deps.get_db),
    current_user: deps.User = Depends(deps.require_role([Role.FACULTY, Role.RETENTION_TEAM, Role.ADMIN]))
):
    """
    Get detailed data for a specific KPI metric.
    """
    data = AnalyticsService.get_drill_down(db, metric)
    return success_response(data, message="KPI drill-down")
