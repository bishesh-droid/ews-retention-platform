"""
LLM API Endpoints
-----------------
REST API endpoints for all LLM capabilities with role-based access control.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.services.ai.llm_orchestrator import LLMOrchestrator
from backend.app.services.analytics.pattern_discovery import PatternDiscoveryEngine, CohortAnalyzer
from backend.app.services.analytics.intervention_intel import InterventionIntelligence
from ..deps import require_role

router = APIRouter()


# ========== Request/Response Models ==========

class RiskExplanationRequest(BaseModel):
    student_id: str
    time_period: str = "recent"


class StudentAdviceRequest(BaseModel):
    student_id: str
    question: str


class FacultySummaryRequest(BaseModel):
    student_id: str
    for_role: str = "faculty"


class InterventionRequest(BaseModel):
    student_id: str


class WhatIfRequest(BaseModel):
    student_id: str
    scenario: Dict[str, Any]


class ReportNarrativeRequest(BaseModel):
    report_type: str
    data: Dict[str, Any]


# ========== Student-Facing Endpoints ==========

@router.post("/explain-risk-change")
def explain_risk_change(
    request: RiskExplanationRequest,
    db: Session = Depends(get_db)
):
    """
    Explain why a student's risk score changed.
    Student-facing endpoint.
    """
    orchestrator = LLMOrchestrator(db)
    result = orchestrator.explain_risk_change(request.student_id, request.time_period)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.post("/student-advice")
def get_student_advice(
    request: StudentAdviceRequest,
    db: Session = Depends(get_db)
):
    """
    Generate personalized advice for a student.
    Student-facing endpoint.
    """
    orchestrator = LLMOrchestrator(db)
    result = orchestrator.generate_student_advice(request.student_id, request.question)
    
    return result


@router.post("/what-if-simulation")
def run_what_if_simulation(
    request: WhatIfRequest,
    db: Session = Depends(get_db)
):
    """
    Simulate what-if scenarios for a student.
    Student-facing endpoint.
    """
    orchestrator = LLMOrchestrator(db)
    result = orchestrator.simulate_what_if(request.student_id, request.scenario)
    
    return result


@router.get("/weekly-brief/{student_id}")
def get_weekly_brief(
    student_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate a weekly academic progress brief for a student.
    Student-facing endpoint.
    """
    orchestrator = LLMOrchestrator(db)
    
    # Use student advice with a standard weekly question
    result = orchestrator.generate_student_advice(
        student_id,
        "Provide a brief weekly summary of my academic progress and suggest 2-3 goals for next week."
    )
    
    return {
        "student_id": student_id,
        "brief": result.get("content", ""),
        "confidence": result.get("confidence", "medium"),
        "sources": result.get("sources", [])
    }


# ========== Faculty/Counselor Endpoints ==========

@router.post("/faculty-summary")
def get_faculty_summary(
    request: FacultySummaryRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a student profile summary for faculty/counselors.
    Faculty-facing endpoint.
    """
    orchestrator = LLMOrchestrator(db)
    result = orchestrator.summarize_student_profile(request.student_id, request.for_role)
    
    return result


@router.post("/intervention-suggestions")
def get_intervention_suggestions(
    request: InterventionRequest,
    db: Session = Depends(get_db)
):
    """
    Get evidence-based intervention suggestions for a student.
    Faculty-facing endpoint.
    """
    intelligence = InterventionIntelligence(db)
    recommendations = intelligence.recommend_interventions(request.student_id)
    
    # Also get LLM narrative
    orchestrator = LLMOrchestrator(db)
    llm_suggestions = orchestrator.suggest_interventions(request.student_id)
    
    return {
        "student_id": request.student_id,
        "structured_recommendations": recommendations,
        "llm_narrative": llm_suggestions.get("content", ""),
        "confidence": llm_suggestions.get("confidence", "medium"),
        "sources": llm_suggestions.get("sources", [])
    }


@router.get("/prioritize-students")
def get_priority_queue(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get a priority queue of students needing intervention.
    Faculty-facing endpoint.
    """
    intelligence = InterventionIntelligence(db)
    priority_queue = intelligence.calculate_intervention_priority_queue(limit)
    
    return {
        "priority_queue": priority_queue,
        "total_students": len(priority_queue),
        "generated_at": "now"
    }


@router.get("/similar-students/{student_id}")
def find_similar_students(
    student_id: str,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Find students with similar risk profiles.
    Faculty-facing endpoint.
    """
    intelligence = InterventionIntelligence(db)
    similar = intelligence.find_similar_students(student_id, limit)
    
    return {
        "student_id": student_id,
        "similar_students": similar,
        "count": len(similar)
    }


# ========== Sales/Retention Endpoints ==========

@router.post("/cohort-analysis")
def analyze_cohort(
    cohort_filters: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """
    Analyze cohort patterns for sales/retention teams.
    Sales-facing endpoint.
    """
    orchestrator = LLMOrchestrator(db)
    result = orchestrator.analyze_cohort_patterns(cohort_filters)
    
    return result


@router.get("/revenue-risk-translation")
def get_revenue_risk(
    db: Session = Depends(get_db)
):
    """
    Translate academic risk to revenue impact.
    Sales-facing endpoint.
    """
    analyzer = CohortAnalyzer(db)
    result = analyzer.analyze_churn_risk()
    
    return result


@router.get("/dropout-pattern-explanation")
def explain_dropout_patterns(
    db: Session = Depends(get_db)
):
    """
    Explain dropout patterns in cohorts.
    Sales-facing endpoint.
    """
    orchestrator = LLMOrchestrator(db)
    
    # Get cohort data and explain patterns
    result = orchestrator.analyze_cohort_patterns()
    
    return result


# ========== Admin/Institutional Endpoints ==========

@router.get("/institutional-insights", dependencies=[Depends(require_role("admin"))])
def get_institutional_insights(
    db: Session = Depends(get_db)
):
    """
    Get system-wide institutional insights.
    Admin-facing endpoint.
    """
    engine = PatternDiscoveryEngine(db)
    
    systemic_issues = engine.discover_systemic_issues()
    blind_spots = engine.detect_blind_spots()
    
    return {
        "systemic_issues": systemic_issues,
        "blind_spots": blind_spots,
        "total_insights": len(systemic_issues) + len(blind_spots)
    }


@router.get("/pattern-discovery")
def discover_patterns(
    db: Session = Depends(get_db)
):
    """
    Run pattern discovery algorithms.
    Admin-facing endpoint.
    """
    engine = PatternDiscoveryEngine(db)
    patterns = engine.discover_systemic_issues()
    
    return {
        "patterns": patterns,
        "count": len(patterns)
    }


@router.post("/generate-report-narrative", dependencies=[Depends(require_role("faculty"))])
def generate_report_narrative(
    request: ReportNarrativeRequest,
    db: Session = Depends(get_db)
):
    """
    Generate auto-narrative for reports.
    Admin/Faculty-facing endpoint.
    """
    orchestrator = LLMOrchestrator(db)
    result = orchestrator.generate_report_narrative(request.report_type, request.data)
    
    return result


@router.get("/intervention-effectiveness")
def get_intervention_effectiveness(
    db: Session = Depends(get_db)
):
    """
    Analyze intervention effectiveness metrics.
    Admin-facing endpoint.
    """
    intelligence = InterventionIntelligence(db)
    effectiveness = intelligence.analyze_intervention_effectiveness()
    
    return effectiveness
