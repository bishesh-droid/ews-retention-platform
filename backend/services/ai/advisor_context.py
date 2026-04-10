"""
Advisor Context Builder Module

Aggregates all relevant EWS data into a structured context
that can be passed to LLM prompts for AI Academic Advisor features.

This module ensures the AI advisor has access to:
- Student profile and demographics
- Current risk assessment and signals
- Historical intervention data
- Academic performance trends
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


def build_advisor_context(
    student_data: Dict[str, Any],
    prediction_data: Optional[Dict[str, Any]] = None,
    intervention_history: Optional[List[Dict]] = None,
    include_sensitive: bool = False
) -> Dict[str, Any]:
    """
    Build comprehensive context for AI advisor prompts.

    Args:
        student_data: Raw student record from database
        prediction_data: Current prediction/risk assessment
        intervention_history: List of past interventions
        include_sensitive: Whether to include sensitive predictions (for internal use)

    Returns:
        Structured context dictionary for LLM prompts
    """
    if not student_data:
        logger.warning("Empty student_data provided to advisor context builder")
        return get_empty_context()

    student_id = student_data.get('id', 'unknown')

    # Build student profile
    profile = build_student_profile(student_data)

    # Build risk assessment context (sanitized for advisor use)
    risk_context = build_risk_context(prediction_data, include_sensitive)

    # Build academic history summary
    academic_summary = build_academic_summary(student_data)

    # Build intervention history summary
    intervention_summary = build_intervention_summary(intervention_history)

    # Combine into final context
    context = {
        "student_id": student_id,
        "context_generated_at": datetime.now().isoformat(),
        "student_profile": profile,
        "risk_assessment": risk_context,
        "academic_history": academic_summary,
        "intervention_history": intervention_summary,
        "advisor_hints": generate_advisor_hints(profile, risk_context, academic_summary)
    }

    return context


def build_student_profile(student_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and structure student profile information."""
    return {
        "id": student_data.get('id'),
        "years_in_program": 7,  # All students have 7 years of data
        "current_status": "active",
        "engagement_level": categorize_engagement(student_data)
    }


def build_risk_context(
    prediction_data: Optional[Dict[str, Any]],
    include_sensitive: bool
) -> Dict[str, Any]:
    """
    Build risk context for advisor.

    Note: For student-facing advisors, we use softer language
    and don't expose raw risk scores.
    """
    if not prediction_data:
        return {
            "status": "unknown",
            "description": "Unable to assess current status",
            "areas_of_focus": []
        }

    risk_score = prediction_data.get('risk_score', 0.5)
    signals = prediction_data.get('signal_breakdown', {})

    # Categorize risk with student-friendly language
    if risk_score < 0.3:
        status = "on_track"
        description = "You're doing well! Keep up the good work."
    elif risk_score < 0.6:
        status = "some_attention_needed"
        description = "There are a few areas where you could improve."
    elif risk_score < 0.8:
        status = "support_recommended"
        description = "We'd like to help you succeed. Let's work together."
    else:
        status = "priority_support"
        description = "We're here to support you through this challenging time."

    # Identify areas needing focus (from signals)
    areas_of_focus = []
    if signals.get('academic_signal_score', 0) > 0.6:
        areas_of_focus.append("academic_performance")
    if signals.get('engagement_signal_score', 0) > 0.6:
        areas_of_focus.append("course_engagement")
    if signals.get('consistency_signal_score', 0) > 0.6:
        areas_of_focus.append("attendance")
    if signals.get('intent_signal_score', 0) > 0.6:
        areas_of_focus.append("performance_trend")

    result = {
        "status": status,
        "description": description,
        "areas_of_focus": areas_of_focus,
        "signal_summary": {
            "academic": categorize_signal(signals.get('academic_signal_score', 0.5)),
            "engagement": categorize_signal(signals.get('engagement_signal_score', 0.5)),
            "consistency": categorize_signal(signals.get('consistency_signal_score', 0.5)),
            "trend": categorize_signal(signals.get('intent_signal_score', 0.5))
        }
    }

    # Include raw scores only for internal/faculty use
    if include_sensitive:
        result["raw_risk_score"] = risk_score
        result["raw_signals"] = signals

    return result


def build_academic_summary(student_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build summary of academic history."""
    # Extract GPA data (q4mpa = Q4 grade point average)
    gpa_history = []
    for year in range(1, 8):
        gpa_key = f'q4mpa{year}'
        if gpa_key in student_data and student_data[gpa_key] is not None:
            gpa_history.append({
                "year": year,
                "gpa": round(student_data[gpa_key], 2)
            })

    # Extract attendance data
    attendance_history = []
    for year in range(1, 8):
        abs_key = f'absrate{year}'
        if abs_key in student_data and student_data[abs_key] is not None:
            attendance_rate = 1 - min(student_data[abs_key], 1.0)  # Convert absence to attendance
            attendance_history.append({
                "year": year,
                "attendance_rate": round(attendance_rate * 100, 1)
            })

    # Calculate trends
    gpa_trend = calculate_trend([g['gpa'] for g in gpa_history[-3:]] if len(gpa_history) >= 3 else [])
    attendance_trend = calculate_trend([a['attendance_rate']
                                       for a in attendance_history[-3:]] if len(attendance_history) >= 3 else [])

    # Get current values
    current_gpa = gpa_history[-1]['gpa'] if gpa_history else None
    current_attendance = attendance_history[-1]['attendance_rate'] if attendance_history else None

    return {
        "current_gpa": current_gpa,
        "gpa_trend": gpa_trend,
        "gpa_trend_description": describe_trend(gpa_trend, "GPA"),
        "current_attendance_rate": current_attendance,
        "attendance_trend": attendance_trend,
        "attendance_trend_description": describe_trend(attendance_trend, "attendance"),
        "years_of_data": len(gpa_history),
        "strengths": identify_strengths(gpa_history, attendance_history),
        "areas_for_improvement": identify_improvements(gpa_history, attendance_history)
    }


def build_intervention_summary(
    intervention_history: Optional[List[Dict]]
) -> Dict[str, Any]:
    """Build summary of past interventions."""
    if not intervention_history:
        return {
            "total_interventions": 0,
            "recent_interventions": [],
            "response_pattern": "no_history"
        }

    total = len(intervention_history)
    recent = intervention_history[:5] if len(intervention_history) > 5 else intervention_history

    # Analyze response pattern
    positive_responses = sum(1 for i in intervention_history if i.get('effectiveness_score', 0) > 0.5)
    response_rate = positive_responses / total if total > 0 else 0

    if response_rate > 0.7:
        response_pattern = "highly_responsive"
    elif response_rate > 0.4:
        response_pattern = "moderately_responsive"
    else:
        response_pattern = "needs_different_approach"

    return {
        "total_interventions": total,
        "recent_interventions": [
            {
                "type": i.get('action', 'unknown'),
                "date": i.get('date'),
                "outcome": "positive" if i.get('effectiveness_score', 0) > 0.5 else "needs_followup"
            }
            for i in recent
        ],
        "response_pattern": response_pattern,
        "successful_approaches": identify_successful_approaches(intervention_history)
    }


def generate_advisor_hints(
    profile: Dict,
    risk_context: Dict,
    academic_summary: Dict
) -> List[str]:
    """Generate hints for the AI advisor based on context."""
    hints = []

    # Hint based on risk status
    status = risk_context.get('status', 'unknown')
    if status == 'on_track':
        hints.append("Focus on maintaining momentum and setting stretch goals")
    elif status == 'some_attention_needed':
        hints.append("Offer gentle encouragement and specific improvement suggestions")
    elif status in ['support_recommended', 'priority_support']:
        hints.append("Be supportive and non-judgmental; focus on small, achievable steps")

    # Hint based on trends
    gpa_trend = academic_summary.get('gpa_trend', 0)
    if gpa_trend < -0.1:
        hints.append("Acknowledge the challenges; help identify root causes")
    elif gpa_trend > 0.1:
        hints.append("Celebrate improvement and reinforce positive behaviors")

    # Hint based on areas of focus
    areas = risk_context.get('areas_of_focus', [])
    if 'attendance' in areas:
        hints.append("Explore barriers to attendance without being accusatory")
    if 'academic_performance' in areas:
        hints.append("Suggest specific study strategies and resources")

    return hints


def get_empty_context() -> Dict[str, Any]:
    """Return empty context structure."""
    return {
        "student_id": None,
        "context_generated_at": datetime.now().isoformat(),
        "student_profile": {},
        "risk_assessment": {"status": "unknown"},
        "academic_history": {},
        "intervention_history": {"total_interventions": 0},
        "advisor_hints": []
    }


def categorize_engagement(student_data: Dict) -> str:
    """Categorize student engagement level."""
    absrate = student_data.get('absrate7', 0.5)
    gpa = student_data.get('q4mpa7', 2.5)

    if absrate < 0.1 and gpa > 3.5:
        return "highly_engaged"
    elif absrate < 0.2 and gpa > 2.5:
        return "engaged"
    elif absrate < 0.3:
        return "moderately_engaged"
    else:
        return "needs_support"


def categorize_signal(score: float) -> str:
    """Convert signal score to category."""
    if score < 0.3:
        return "strong"
    elif score < 0.6:
        return "moderate"
    else:
        return "needs_attention"


def calculate_trend(values: List[float]) -> float:
    """Calculate simple trend from values."""
    if len(values) < 2:
        return 0.0
    return (values[-1] - values[0]) / len(values)


def describe_trend(trend: float, metric: str) -> str:
    """Convert trend value to description."""
    if trend > 0.1:
        return f"{metric} is improving"
    elif trend < -0.1:
        return f"{metric} is declining"
    else:
        return f"{metric} is stable"


def identify_strengths(gpa_history: List, attendance_history: List) -> List[str]:
    """Identify student strengths from history."""
    strengths = []
    if gpa_history and gpa_history[-1]['gpa'] > 3.5:
        strengths.append("Strong academic performance")
    if attendance_history and attendance_history[-1]['attendance_rate'] > 90:
        strengths.append("Excellent attendance")
    if gpa_history and len(gpa_history) >= 3:
        trend = calculate_trend([g['gpa'] for g in gpa_history[-3:]])
        if trend > 0.1:
            strengths.append("Showing improvement over time")
    return strengths


def identify_improvements(gpa_history: List, attendance_history: List) -> List[str]:
    """Identify areas for improvement."""
    improvements = []
    if gpa_history and gpa_history[-1]['gpa'] < 2.5:
        improvements.append("Academic performance could be stronger")
    if attendance_history and attendance_history[-1]['attendance_rate'] < 80:
        improvements.append("Attendance could be improved")
    return improvements


def identify_successful_approaches(interventions: List[Dict]) -> List[str]:
    """Identify which intervention approaches worked."""
    if not interventions:
        return []

    successful = [
        i.get('action', 'unknown')
        for i in interventions
        if i.get('effectiveness_score', 0) > 0.6
    ]

    # Return unique successful approaches
    return list(set(successful))[:3]
