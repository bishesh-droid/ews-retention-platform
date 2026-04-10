"""
Student domain policies.
"""

from typing import Dict


def build_intervention_recommendation(risk_score: float) -> Dict:
    """Derive intervention recommendation from a risk score."""
    if risk_score >= 80:
        category = "urgent"
        action = "Immediate outreach required"
        channels = ["whatsapp", "phone", "email"]
        team = "sales"
    elif risk_score >= 60:
        category = "mentor_outreach"
        action = "Schedule mentor meeting"
        channels = ["email", "mentor_call"]
        team = "faculty"
    elif risk_score >= 40:
        category = "gentle_reminder"
        action = "Send encouragement email"
        channels = ["email"]
        team = "automated"
    else:
        category = "no_action"
        action = "No intervention needed"
        channels = []
        team = "none"

    return {
        "threshold_category": category,
        "action_type": action,
        "channels": channels,
        "assigned_team": team,
        "priority": (
            "critical" if risk_score >= 80
            else "high" if risk_score >= 60
            else "medium" if risk_score >= 40
            else "low"
        ),
        "urgency": category,
        "description": action,
    }
