"""
Business Metrics API Routes

Endpoints for business intelligence and executive reporting:
- Retention metrics
- Revenue at risk calculations
- Intervention ROI analysis
- Retention funnel data
"""

from fastapi import APIRouter, HTTPException, Header, Query, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services.student_service import StudentService
from backend.config import (
    AVERAGE_STUDENT_LTV,
    TUITION_PER_SEMESTER,
    INTERVENTION_COST_PER_STUDENT,
    TARGET_RETENTION_RATE,
    INTERVENTION_THRESHOLDS
)
from backend.utils.api import success_response

router = APIRouter(prefix="/business", tags=["Business Intelligence"])


# Response Models
class RetentionMetricsResponse(BaseModel):
    total_enrolled: int
    retention_rate: float
    target_retention_rate: float
    gap_to_target: float
    at_risk_count: int
    high_risk_count: int
    critical_risk_count: int
    period: str
    calculated_at: str


class RevenueAtRiskResponse(BaseModel):
    total_enrolled_revenue: float
    revenue_at_risk: float
    high_risk_revenue: float
    critical_risk_revenue: float
    percentage_at_risk: float
    average_student_ltv: float
    risk_breakdown: List[Dict[str, Any]]
    calculated_at: str


class InterventionROIResponse(BaseModel):
    period: str
    interventions_triggered: int
    estimated_recovered: int
    total_intervention_cost: float
    revenue_saved: float
    roi_multiple: float
    cost_per_retained_student: float
    breakdown: Dict[str, Any]
    calculated_at: str


class RetentionFunnelResponse(BaseModel):
    stages: List[Dict[str, Any]]
    conversion_rates: List[Dict[str, Any]]
    period: str
    calculated_at: str


class ExecutiveSummaryResponse(BaseModel):
    headline_metrics: Dict[str, Any]
    trends: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    recommended_actions: List[str]
    calculated_at: str


class DepartmentComparisonRow(BaseModel):
    department: str
    student_count: int
    avg_risk_score: float


class RetentionForecastPoint(BaseModel):
    period: str
    optimistic_retention_rate: float
    baseline_retention_rate: float
    pessimistic_retention_rate: float
    optimistic_retained_revenue: float
    baseline_retained_revenue: float
    pessimistic_retained_revenue: float


class CohortHeatmapRow(BaseModel):
    cohort: str
    Low: float
    Medium: float
    High: float
    Critical: float


def _get_risk_counts(students):
    """Count students by risk level using risk_score (0-100 scale)."""
    at_risk = 0
    high_risk = 0
    critical = 0
    for s in students:
        score = s["risk_score"]
        if score >= 40:
            at_risk += 1
        if score >= 70:
            high_risk += 1
        if score >= 85:
            critical += 1
    return at_risk, high_risk, critical


def _risk_tier(score: float) -> str:
    if score <= 40:
        return "Low"
    if score <= 70:
        return "Medium"
    if score <= 85:
        return "High"
    return "Critical"


@router.get("/metrics/retention")
def get_retention_metrics(
    period: str = Query(default="current_semester"),
    db: Session = Depends(get_db)
):
    """Get retention rate and enrollment metrics."""
    stats = StudentService.get_overview_stats(db)
    students = StudentService.get_all_students(db, 0, 5000)

    total_enrolled = stats["total_students"]
    at_risk_count, high_risk_count, critical_risk_count = _get_risk_counts(students)

    estimated_dropouts = (high_risk_count * 0.25) + (critical_risk_count * 0.50)
    retention_rate = (total_enrolled - estimated_dropouts) / total_enrolled if total_enrolled > 0 else 0

    data = RetentionMetricsResponse(
        total_enrolled=total_enrolled,
        retention_rate=round(retention_rate, 4),
        target_retention_rate=TARGET_RETENTION_RATE,
        gap_to_target=round(TARGET_RETENTION_RATE - retention_rate, 4),
        at_risk_count=at_risk_count,
        high_risk_count=high_risk_count,
        critical_risk_count=critical_risk_count,
        period=period,
        calculated_at=datetime.now().isoformat()
    )
    return success_response(data.dict(), message="Retention metrics")


@router.get("/metrics/revenue-at-risk")
def get_revenue_at_risk(db: Session = Depends(get_db)):
    """Calculate total revenue at risk from potential dropouts."""
    students = StudentService.get_all_students(db, 0, 5000)
    total_enrolled = len(students)
    total_enrolled_revenue = total_enrolled * AVERAGE_STUDENT_LTV

    revenue_breakdown = {
        "critical": {"count": 0, "revenue": 0.0, "dropout_rate": 0.50},
        "high": {"count": 0, "revenue": 0.0, "dropout_rate": 0.25},
        "moderate": {"count": 0, "revenue": 0.0, "dropout_rate": 0.10},
        "low": {"count": 0, "revenue": 0.0, "dropout_rate": 0.02},
    }

    for s in students:
        score = s["risk_score"]
        if score >= 85:
            cat = "critical"
        elif score >= 70:
            cat = "high"
        elif score >= 40:
            cat = "moderate"
        else:
            cat = "low"
        revenue_breakdown[cat]["count"] += 1
        revenue_breakdown[cat]["revenue"] += AVERAGE_STUDENT_LTV * revenue_breakdown[cat]["dropout_rate"]

    high_risk_revenue = revenue_breakdown["high"]["revenue"]
    critical_risk_revenue = revenue_breakdown["critical"]["revenue"]
    total_revenue_at_risk = sum(c["revenue"] for c in revenue_breakdown.values())

    breakdown_list = [
        {
            "category": cat,
            "student_count": data["count"],
            "revenue_at_risk": round(data["revenue"], 2),
            "avg_value_per_student": round(AVERAGE_STUDENT_LTV * data["dropout_rate"], 2),
            "dropout_probability": data["dropout_rate"],
        }
        for cat, data in revenue_breakdown.items()
        if data["count"] > 0
    ]

    data = RevenueAtRiskResponse(
        total_enrolled_revenue=round(total_enrolled_revenue, 2),
        revenue_at_risk=round(total_revenue_at_risk, 2),
        high_risk_revenue=round(high_risk_revenue, 2),
        critical_risk_revenue=round(critical_risk_revenue, 2),
        percentage_at_risk=round((total_revenue_at_risk / total_enrolled_revenue) * 100, 2) if total_enrolled_revenue > 0 else 0,
        average_student_ltv=AVERAGE_STUDENT_LTV,
        risk_breakdown=breakdown_list,
        calculated_at=datetime.now().isoformat()
    )
    return success_response(data.dict(), message="Revenue at risk metrics")


@router.get("/metrics/intervention-roi")
def get_intervention_roi(
    period: str = Query(default="quarterly"),
    db: Session = Depends(get_db)
):
    """Calculate ROI for retention interventions."""
    students = StudentService.get_all_students(db, 0, 5000)

    threshold = INTERVENTION_THRESHOLDS["no_action"]
    at_risk_students = [s for s in students if s["risk_score"] >= threshold]

    interventions_triggered = int(len(at_risk_students) * 0.6)
    recovery_rate = 0.35
    estimated_recovered = int(interventions_triggered * recovery_rate)

    staff_time_cost = interventions_triggered * 2.5 * 45
    platform_cost = 5000
    incentive_cost = min(25000, estimated_recovered * 150)
    training_cost = 3500

    total_cost = staff_time_cost + platform_cost + incentive_cost + training_cost
    cost_per_student = total_cost / estimated_recovered if estimated_recovered > 0 else 0
    revenue_saved = estimated_recovered * AVERAGE_STUDENT_LTV
    roi_multiple = (revenue_saved - total_cost) / total_cost if total_cost > 0 else 0

    data = InterventionROIResponse(
        period=period,
        interventions_triggered=interventions_triggered,
        estimated_recovered=estimated_recovered,
        total_intervention_cost=round(total_cost, 2),
        revenue_saved=round(revenue_saved, 2),
        roi_multiple=round(roi_multiple, 2),
        cost_per_retained_student=round(cost_per_student, 2),
        breakdown={
            "staff_time": round(staff_time_cost, 2),
            "platform_tools": platform_cost,
            "student_incentives": round(incentive_cost, 2),
            "training": training_cost,
            "recovery_rate": recovery_rate,
            "avg_student_ltv": AVERAGE_STUDENT_LTV,
        },
        calculated_at=datetime.now().isoformat()
    )
    return success_response(data.dict(), message="Intervention ROI metrics")


@router.get("/funnel")
def get_retention_funnel(
    period: str = Query(default="current_semester"),
    db: Session = Depends(get_db)
):
    """Get retention funnel data."""
    students = StudentService.get_all_students(db, 0, 5000)
    total_enrolled = len(students)

    at_risk = len([s for s in students if s["risk_score"] > 40])
    high_risk = len([s for s in students if s["risk_score"] > 70])
    interventions = int(at_risk * 0.6)
    recovered = int(interventions * 0.35)
    dropped = int(high_risk * 0.25)

    stages = [
        {"name": "Total Enrolled", "count": total_enrolled, "color": "#3B82F6"},
        {"name": "At-Risk Identified", "count": at_risk, "color": "#F59E0B"},
        {"name": "Intervention Triggered", "count": interventions, "color": "#8B5CF6"},
        {"name": "Recovered", "count": recovered, "color": "#10B981"},
        {"name": "Dropped", "count": dropped, "color": "#EF4444"},
    ]

    conversion_rates = []
    for i in range(1, len(stages) - 1):
        if stages[i - 1]["count"] > 0:
            rate = (stages[i]["count"] / stages[i - 1]["count"]) * 100
            conversion_rates.append({
                "from": stages[i - 1]["name"],
                "to": stages[i]["name"],
                "rate": round(rate, 1),
            })

    data = RetentionFunnelResponse(
        stages=stages,
        conversion_rates=conversion_rates,
        period=period,
        calculated_at=datetime.now().isoformat()
    )
    return success_response(data.dict(), message="Retention funnel")


@router.get("/executive-summary")
def get_executive_summary(db: Session = Depends(get_db)):
    """Get executive summary dashboard data."""
    stats = StudentService.get_overview_stats(db)
    students = StudentService.get_all_students(db, 0, 5000)

    total_enrolled = stats["total_students"]
    at_risk_count, high_risk_count, critical_risk_count = _get_risk_counts(students)

    estimated_dropouts = int(high_risk_count * 0.25)
    retention_rate = (total_enrolled - estimated_dropouts) / total_enrolled if total_enrolled > 0 else 0
    revenue_at_risk = high_risk_count * AVERAGE_STUDENT_LTV * 0.25

    alerts = []
    if high_risk_count > total_enrolled * 0.15:
        alerts.append({
            "severity": "high",
            "message": f"{high_risk_count} students ({(high_risk_count / total_enrolled) * 100:.1f}%) are high-risk",
            "action": "Review intervention capacity",
        })
    if retention_rate < TARGET_RETENTION_RATE - 0.03:
        alerts.append({
            "severity": "medium",
            "message": f"Retention rate {retention_rate * 100:.1f}% below target {TARGET_RETENTION_RATE * 100:.0f}%",
            "action": "Increase intervention frequency",
        })

    actions = []
    if high_risk_count > 50:
        actions.append("Schedule department review of high-risk cohorts")
    if revenue_at_risk > 500000:
        actions.append("Escalate to sales leadership for immediate attention")
    actions.append("Review intervention effectiveness metrics weekly")

    data = ExecutiveSummaryResponse(
        headline_metrics={
            "total_enrolled": total_enrolled,
            "retention_rate": round(retention_rate * 100, 1),
            "revenue_at_risk": round(revenue_at_risk, 2),
            "high_risk_count": high_risk_count,
        },
        trends={
            "retention_trend": "+2.1%",
            "risk_trend": "-3.5%",
            "intervention_effectiveness": "+8%",
        },
        alerts=alerts,
        recommended_actions=actions,
        calculated_at=datetime.now().isoformat()
    )
    return success_response(data.dict(), message="Executive summary")


@router.get("/departments/comparison")
def get_department_comparison(db: Session = Depends(get_db)):
    """
    Department comparison for BI dashboards.

    Returns student counts and average risk score per department.
    """
    analytics = StudentService.get_analytics_data(db)
    dept_rows = analytics.get("department_summary", []) if isinstance(analytics, dict) else []
    payload = [
        {
            "department": d.get("department", "Unknown"),
            "student_count": int(d.get("student_count") or 0),
            "avg_risk_score": float(d.get("avg_risk_score") or 0),
        }
        for d in dept_rows
    ]
    # Sort largest cohorts first
    payload.sort(key=lambda r: (-r["student_count"], r["department"]))
    return success_response(payload, message="Department comparison")


@router.get("/forecast/retention")
def get_retention_forecast(
    horizon_months: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db),
):
    """
    Simple retention forecast for BI charts (deterministic heuristic).

    Produces optimistic/baseline/pessimistic retention rates and retained revenue.
    """
    retention = get_retention_metrics(db=db, period="current_semester")
    # retention is success_response envelope already
    retention_data = retention.get("data") if isinstance(retention, dict) else None
    if isinstance(retention_data, dict) and "retention_rate" in retention_data:
        baseline_rate = float(retention_data.get("retention_rate") or 0)  # 0..1
        target_rate = float(retention_data.get("target_retention_rate") or TARGET_RETENTION_RATE)
    else:
        baseline_rate = 0.0
        target_rate = TARGET_RETENTION_RATE

    total_enrolled = int(retention_data.get("total_enrolled") or 0) if isinstance(retention_data, dict) else 0
    base_revenue = total_enrolled * AVERAGE_STUDENT_LTV

    # optimistic moves toward target; pessimistic decays modestly below baseline
    optimistic_rate = min(1.0, max(baseline_rate, target_rate))
    pessimistic_rate = max(0.0, baseline_rate - max(0.02, abs(target_rate - baseline_rate) * 0.5))

    points: List[Dict[str, Any]] = []
    for m in range(1, horizon_months + 1):
        label = f"+{m} mo"
        # Apply small drift factors over time
        opt = min(1.0, optimistic_rate * (1 - 0.001 * m))
        base = max(0.0, baseline_rate * (1 - 0.002 * m))
        pess = max(0.0, pessimistic_rate * (1 - 0.003 * m))

        points.append(
            RetentionForecastPoint(
                period=label,
                optimistic_retention_rate=round(opt, 4),
                baseline_retention_rate=round(base, 4),
                pessimistic_retention_rate=round(pess, 4),
                optimistic_retained_revenue=round(base_revenue * opt, 2),
                baseline_retained_revenue=round(base_revenue * base, 2),
                pessimistic_retained_revenue=round(base_revenue * pess, 2),
            ).dict()
        )

    return success_response(
        {
            "base": {
                "total_enrolled": total_enrolled,
                "average_student_ltv": AVERAGE_STUDENT_LTV,
                "baseline_retention_rate": round(baseline_rate, 4),
                "target_retention_rate": round(target_rate, 4),
            },
            "points": points,
        },
        message="Retention forecast",
    )


@router.get("/cohort-heatmap")
def get_cohort_heatmap(db: Session = Depends(get_db)):
    """
    Cohort heatmap-style risk tier distribution.

    Uses department as cohort key (stable and available in the current dataset).
    """
    students = StudentService.get_all_students(db, 0, 5000)
    by_dept: Dict[str, Dict[str, int]] = {}
    totals: Dict[str, int] = {}

    for s in students:
        dept = s.get("department") or "Unknown"
        score = float(s.get("risk_score") or 0)
        tier = _risk_tier(score)
        if dept not in by_dept:
            by_dept[dept] = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
            totals[dept] = 0
        by_dept[dept][tier] += 1
        totals[dept] += 1

    rows: List[Dict[str, Any]] = []
    for dept, counts in by_dept.items():
        total = max(1, totals.get(dept, 0))
        rows.append(
            CohortHeatmapRow(
                cohort=dept,
                Low=round((counts["Low"] / total) * 100, 1),
                Medium=round((counts["Medium"] / total) * 100, 1),
                High=round((counts["High"] / total) * 100, 1),
                Critical=round((counts["Critical"] / total) * 100, 1),
            ).dict()
        )

    # Sort by High+Critical desc for readability
    rows.sort(key=lambda r: -((r["High"] or 0) + (r["Critical"] or 0)))
    return success_response(rows, message="Cohort heatmap")
