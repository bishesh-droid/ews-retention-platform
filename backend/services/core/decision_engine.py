"""
Decision Engine Service
Implements risk threshold logic to determine appropriate interventions.

All risk scores in this module use a 0–100 scale.

Thresholds are configurable via environment variables (see backend/config.py):
- < THRESHOLD_NO_ACTION (default 30): No action
- THRESHOLD_NO_ACTION to THRESHOLD_GENTLE (30–40): Gentle reminder (automated email)
- THRESHOLD_GENTLE to THRESHOLD_MENTOR (40–60): Mentor outreach (faculty + email)
- THRESHOLD_MENTOR to THRESHOLD_URGENT (60–80): Mentor outreach (escalated)
- >= THRESHOLD_URGENT (default 80): Urgent intervention (sales + WhatsApp + incentive)
"""

import logging
import numpy as np
from typing import Dict, Any, Optional
from backend.config import (
    INTERVENTION_THRESHOLDS,
    INTERVENTION_COOLDOWN_DAYS,
    RISK_SPIKE_THRESHOLD
)

# Configure logger
logger = logging.getLogger(__name__)

# Extract thresholds from config
THRESHOLD_NO_ACTION = INTERVENTION_THRESHOLDS['no_action']
THRESHOLD_GENTLE = INTERVENTION_THRESHOLDS['gentle_reminder']
THRESHOLD_MENTOR = INTERVENTION_THRESHOLDS['mentor_outreach']
THRESHOLD_URGENT = INTERVENTION_THRESHOLDS['urgent']


def _validate_risk_score(risk_score: float) -> float:
    """Validate and normalize risk score.

    Enforces 0-100 scale (not 0-1). Rejects Inf values; uses 50.0 default for NaN.
    """
    # Check type
    if not isinstance(risk_score, (int, float)):
        raise AssertionError(f"risk_score must be numeric, got {type(risk_score)}")

    # Check NaN — use neutral default rather than raising
    if risk_score != risk_score:  # NaN check (NaN != NaN is always True)
        logger.error("Invalid risk_score in decision engine: nan. Using neutral default 50.0")
        return 50.0

    # Check Inf — reject with AssertionError
    if np.isinf(risk_score):
        raise AssertionError("risk_score cannot be Inf")

    # Reject 0-1 normalized scores (any value strictly between 0 and 1 is suspicious)
    if 0.0 < risk_score < 1.0:
        raise AssertionError(
            f"risk_score {risk_score} appears to be on a 0-1 scale. "
            f"Expected 0-100 scale."
        )

    # Check 0-100 range
    if not (0.0 <= risk_score <= 100.0):
        raise AssertionError(
            f"risk_score must be 0-100 scale, got {risk_score}. "
            f"Normalized (0-1) scores not accepted."
        )

    return float(risk_score)


def _handle_ghost_outreach(features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle ghost student activation outreach if needed."""
    if not features or not features.get("requires_activation_outreach"):
        return None
    ghost_type = features.get("ghost_info", {}).get("ghost_type", "unknown")
    action_items = (
        [
            "Call student directly — do not send automated message",
            "Verify student received welcome email and login credentials",
            "Check if student has a platform access or technical issue",
            "If no response within 48 hours, escalate to admissions team",
            "Log outcome in intervention tracker",
        ]
        if ghost_type == "never_logged_in"
        else [
            "Student has logged in but never accessed course content",
            "Send personalised onboarding walkthrough link",
            "Schedule a 15-minute orientation call with student support team",
            "Check if student is aware of how to navigate the LMS",
        ]
    )
    return {
        "type": "activation_outreach",
        "priority": "critical",
        "ghost_type": ghost_type,
        "channels": ["direct_call", "email", "admissions_escalation"],
        "action_items": action_items,
        "suppress_automated_messages": True,
    }


def _handle_academic_flags(features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle academic flags like dropout intent, UFM, health referrals."""
    if not features:
        return None

    if features.get("suppress_intervention"):
        return {"type": "none", "reason": "Student formally deferred — enrolled in next trimester"}

    flags = features.get("academic_flags", {})

    if flags.get("dropout_intent"):
        return {
            "type": "retention_emergency",
            "priority": "critical",
            "channels": ["direct_call", "retention_team", "admissions_escalation"],
            "action_items": [
                "Immediate call from retention team — do not use automated messaging",
                "Understand the reason for refund request",
                "Offer financial support options, fee deferral, or leave of absence",
                "Escalate to academic director within 24 hours if no response",
            ],
        }

    if flags.get("ufm_flagged"):
        return {
            "type": "academic_integrity",
            "priority": "high",
            "channels": ["email", "dean_notification"],
            "action_items": [
                "Notify academic integrity officer",
                "Schedule a formal meeting with student and academic advisor",
                "Document the incident in the student record",
            ],
        }

    if features.get("health_referral_needed"):
        return {
            "type": "welfare_referral",
            "priority": "medium",
            "channels": ["email", "welfare_team"],
            "action_items": [
                "Refer to student welfare team (not academic team)",
                "Check on student wellbeing — avoid academic pressure messaging",
                "Offer assignment extension or medical leave if appropriate",
            ],
        }
    return None


def _get_pattern_intervention(
    engagement_pattern: str, risk_score: float
) -> Optional[Dict[str, Any]]:
    """Get intervention based on engagement pattern."""
    if engagement_pattern == "struggling":
        return {
            "type": "academic_support",
            "priority": "high" if risk_score >= 60 else "medium",
            "channels": ["ta_session", "instructor_flag", "remedial_content"],
            "action_items": [
                "Schedule a TA support session within 3 days",
                "Share course-specific remedial content links",
                "Notify course instructor — student is attending but struggling",
                "Follow up after next graded component submission",
            ],
            "message_tone": "supportive",
            "suppress_sales_contact": True,
        }

    if engagement_pattern == "disengaged":
        return {
            "type": "re_engagement",
            "priority": "high" if risk_score >= 50 else "medium",
            "channels": ["whatsapp", "email"],
            "action_items": [
                "Verify platform access — student may have login issues",
                "Send personalised re-engagement message",
                "Check if student received onboarding materials",
                "Escalate to admissions if no response in 5 days",
            ],
            "message_tone": "warm",
            "suppress_sales_contact": False,
        }
    return None


def _get_threshold_intervention(risk_score: float) -> Dict[str, Any]:
    """Get intervention based on risk score thresholds."""
    if risk_score < THRESHOLD_NO_ACTION:
        return {
            "type": "no_action",
            "action_type": "no_action",
            "threshold_category": "low_risk",
            "channels": [],
            "assigned_team": "none",
            "message_template": None,
            "urgency": "none",
            "priority": None,
            "description": (
                "Student is on track, no intervention needed. "
                "Continue to monitor engagement and risk score."
            ),
            "threshold_used": THRESHOLD_NO_ACTION,
        }

    if risk_score < THRESHOLD_GENTLE:
        return {
            "type": "gentle_reminder",
            "action_type": "gentle_reminder",
            "threshold_category": "gentle_reminder",
            "channels": ["email"],
            "assigned_team": "automated",
            "message_template": "gentle_reminder_email",
            "urgency": "low",
            "priority": "low",
            "description": "Send automated email reminder to check in with student",
            "threshold_used": THRESHOLD_GENTLE,
        }

    if risk_score < THRESHOLD_MENTOR:
        return {
            "type": "mentor_outreach",
            "action_type": "mentor_outreach",
            "threshold_category": "mentor_outreach",
            "channels": ["email", "mentor_call"],
            "assigned_team": "faculty",
            "message_template": "mentor_outreach_email",
            "urgency": "medium",
            "priority": "medium",
            "description": "Assign faculty mentor for personalized outreach and support",
            "threshold_used": THRESHOLD_MENTOR,
        }

    if risk_score < THRESHOLD_URGENT:
        return {
            "type": "mentor_outreach",
            "action_type": "mentor_outreach",
            "threshold_category": "mentor_outreach_escalated",
            "channels": ["email", "mentor_call"],
            "assigned_team": "faculty",
            "message_template": "mentor_outreach_email",
            "urgency": "high",
            "priority": "high",
            "description": (
                "Escalated faculty mentor outreach — heightened engagement risk; "
                "prioritize personalized support and follow-up"
            ),
            "threshold_used": THRESHOLD_URGENT,
        }

    return {
        "type": "urgent_intervention",
        "action_type": "urgent_intervention",
        "threshold_category": "urgent_intervention",
        "channels": ["sales_call", "whatsapp", "incentive_offer"],
        "assigned_team": "sales",
        "message_template": "urgent_intervention_package",
        "urgency": "high",
        "priority": "critical",
        "description": "Immediate escalation to sales team with multi-channel outreach and incentive offer",
        "threshold_used": THRESHOLD_URGENT,
    }


def get_intervention_recommendation(
    risk_score: float,
    engagement_pattern: str = None,
    features: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Apply decision thresholds and return recommended intervention.

    Args:
        risk_score: Risk score on the 0–100 scale (same scale as config thresholds).
        engagement_pattern: Optional engagement pattern classification ("disengaged",
            "struggling", "at_risk_normal", "on_track") to enable tailored interventions.
        features: Optional features dictionary for ghost detection and other
            feature-based routing decisions.

    Returns:
        Dictionary with intervention details
    """
    risk_score = _validate_risk_score(risk_score)
    features = features or {}

    # Check interventions in priority order
    if result := _handle_ghost_outreach(features):
        return result

    if result := _handle_academic_flags(features):
        return result

    if result := _get_pattern_intervention(engagement_pattern, risk_score):
        return result

    return _get_threshold_intervention(risk_score)


def should_trigger_intervention(
    current_risk_score: float,
    previous_risk_score: float = None,
    days_since_last_intervention: int = None
) -> bool:
    """
    Determine if an intervention should be triggered based on risk score and history.

    Uses 0-100 scale. Spike threshold is 10 points (not 0.1).

    Args:
        current_risk_score: Current risk score (0–100)
        previous_risk_score: Previous risk score, if available
        days_since_last_intervention: Days since last intervention

    Returns:
        Boolean indicating whether to trigger intervention
    """
    # Validate current score is on 0-100 scale
    if not (0 <= current_risk_score <= 100):
        raise AssertionError(
            f"current_risk_score must be 0-100, got {current_risk_score}"
        )

    # Validate previous score if provided
    if previous_risk_score is not None and not (0 <= previous_risk_score <= 100):
        raise AssertionError(
            f"previous_risk_score must be 0-100, got {previous_risk_score}"
        )

    # No previous score — respect cooldown, then trigger only if above action threshold
    if previous_risk_score is None:
        if days_since_last_intervention is not None and days_since_last_intervention < INTERVENTION_COOLDOWN_DAYS:
            return False  # In cooldown, no delta to justify bypass
        return current_risk_score >= THRESHOLD_NO_ACTION

    # Calculate delta on 0-100 scale
    delta = current_risk_score - previous_risk_score

    # Large spike (>= RISK_SPIKE_THRESHOLD) overrides cooldown
    if delta >= RISK_SPIKE_THRESHOLD:
        return True

    # Respects cooldown for smaller changes
    if days_since_last_intervention is None or days_since_last_intervention >= INTERVENTION_COOLDOWN_DAYS:
        return delta >= 1  # Any increase OK after cooldown expires

    return False


def get_message_template(template_name: str, student_name: str = "Student") -> str:
    """
    Get message template for intervention

    Args:
        template_name: Name of the template
        student_name: Student's name for personalization

    Returns:
        Message content
    """
    templates = {
        "gentle_reminder_email": f"""
Dear {student_name},

We noticed that you haven't been as active on the platform recently. We're here to support you in your learning journey!

If you're facing any challenges or have questions, please don't hesitate to
reach out to your instructors or our support team.

Keep up the great work!

Best regards,
Your Learning Support Team
        """.strip(),

        "mentor_outreach_email": f"""
Dear {student_name},

We've noticed some changes in your engagement and would like to offer you additional support.

A dedicated mentor from our faculty team will be reaching out to you shortly
to discuss how we can help you succeed in your courses.

Please check your email and phone for a call from your assigned mentor.

We're committed to your success!

Best regards,
Academic Support Team
        """.strip(),

        "urgent_intervention_package": f"""
Dear {student_name},

We value your enrollment and want to ensure you're getting the most out of your learning experience.

Our team has prepared a personalized support package for you, including:
- One-on-one consultation with our academic advisor
- Special resources and study materials
- Exclusive learning incentives

A member of our student success team will contact you via phone and WhatsApp within 24 hours.

We're here to help you succeed!

Student Success Team
        """.strip()
    }

    return templates.get(template_name, "")


def calculate_intervention_priority(
    risk_score: float,
    engagement_trend: float = None,
    days_inactive: int = None
) -> str:
    """
    Calculate priority level for intervention queue

    Args:
        risk_score: Current risk score (0–100)
        engagement_trend: Trend in engagement (negative = declining); reserved for future use
        days_inactive: Number of consecutive days inactive; reserved for future use

    Returns:
        Priority level: "critical", "high", "medium", "low"
    """
    normalized = risk_score / 100.0
    if normalized >= 0.85:
        return "critical"
    elif normalized >= 0.70:
        return "high"
    elif normalized >= 0.45:
        return "medium"
    else:
        return "low"
