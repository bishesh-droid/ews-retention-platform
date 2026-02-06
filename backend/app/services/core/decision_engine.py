"""
Decision Engine Service
Implements risk threshold logic to determine appropriate interventions.

Thresholds are configurable via environment variables (see backend/config.py):
- < THRESHOLD_NO_ACTION (default 30%): No action
- THRESHOLD_NO_ACTION to THRESHOLD_GENTLE (30-60%): Gentle reminder (automated email)
- THRESHOLD_GENTLE to THRESHOLD_MENTOR (60-80%): Mentor outreach (faculty + email)
- >= THRESHOLD_URGENT (default 80%): Urgent intervention (sales + WhatsApp + incentive)

NOTE: All risk_score inputs must be probabilities in [0.0, 1.0] range.
"""

import logging
import numpy as np
from typing import Dict, Any, List
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


def get_intervention_recommendation(risk_score: float) -> Dict[str, Any]:
    """
    Apply decision thresholds and return recommended intervention.
    
    Args:
        risk_score: Risk score from 0.0 to 1.0 (probability, NOT percentage)
        
    Returns:
        Dictionary with intervention details
    
    Note:
        This function expects probabilities (0.0-1.0), not percentages (0-100).
        Thresholds are: <0.30, 0.30-0.60, 0.60-0.80, >=0.80
    """
    # Validate risk_score is in valid range
    if risk_score is None or np.isnan(risk_score) or np.isinf(risk_score):
        logger.error(f"Invalid risk_score in decision engine: {risk_score}. Using neutral default 0.5")
        risk_score = 0.5
    
    if risk_score < 0.0 or risk_score > 1.0:
        logger.error(f"Risk score out of range [0, 1]: {risk_score}. Clamping to valid range.")
        risk_score = max(0.0, min(1.0, risk_score))

    if risk_score < THRESHOLD_NO_ACTION:
        return {
            "action_type": "no_action",
            "threshold_category": "low_risk",
            "channels": [],
            "assigned_team": "none",
            "message_template": None,
            "urgency": "none",
            "description": "Student is on track, no intervention needed",
            "threshold_used": THRESHOLD_NO_ACTION
        }

    elif risk_score < THRESHOLD_GENTLE:
        return {
            "action_type": "gentle_reminder",
            "threshold_category": "gentle_reminder",
            "channels": ["email"],
            "assigned_team": "automated",
            "message_template": "gentle_reminder_email",
            "urgency": "low",
            "description": "Send automated email reminder to check in with student",
            "threshold_used": THRESHOLD_GENTLE
        }

    elif risk_score < THRESHOLD_MENTOR:
        return {
            "action_type": "mentor_outreach",
            "threshold_category": "mentor_outreach",
            "channels": ["email", "mentor_call"],
            "assigned_team": "faculty",
            "message_template": "mentor_outreach_email",
            "urgency": "medium",
            "description": "Assign faculty mentor for personalized outreach and support",
            "threshold_used": THRESHOLD_MENTOR
        }

    else:  # risk_score >= THRESHOLD_URGENT
        return {
            "action_type": "urgent_intervention",
            "threshold_category": "urgent_intervention",
            "channels": ["sales_call", "whatsapp", "incentive_offer"],
            "assigned_team": "sales",
            "message_template": "urgent_intervention_package",
            "urgency": "high",
            "description": "Immediate escalation to sales team with multi-channel outreach and incentive offer",
            "threshold_used": THRESHOLD_URGENT
        }


def should_trigger_intervention(
    current_risk_score: float,
    previous_risk_score: float = None,
    days_since_last_intervention: int = None
) -> bool:
    """
    Determine if an intervention should be triggered based on risk score and history
    
    Args:
        current_risk_score: Current risk score (0-1)
        previous_risk_score: Previous risk score, if available
        days_since_last_intervention: Days since last intervention
        
    Returns:
        Boolean indicating whether to trigger intervention
    """
    # Always trigger if risk is above threshold and no recent intervention
    if current_risk_score >= THRESHOLD_NO_ACTION:
        # Don't spam: wait at least INTERVENTION_COOLDOWN_DAYS between interventions
        if days_since_last_intervention is None or days_since_last_intervention >= INTERVENTION_COOLDOWN_DAYS:
            return True

        # Exception: if risk increased significantly (> RISK_SPIKE_THRESHOLD), trigger even if recent
        if previous_risk_score and (current_risk_score - previous_risk_score) > RISK_SPIKE_THRESHOLD:
            return True

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

If you're facing any challenges or have questions, please don't hesitate to reach out to your instructors or our support team.

Keep up the great work!

Best regards,
Your Learning Support Team
        """.strip(),
        
        "mentor_outreach_email": f"""
Dear {student_name},

We've noticed some changes in your engagement and would like to offer you additional support. 

A dedicated mentor from our faculty team will be reaching out to you shortly to discuss how we can help you succeed in your courses.

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
        risk_score: Current risk score (0-1)
        engagement_trend: Trend in engagement (negative = declining)
        days_inactive: Number of consecutive days inactive
        
    Returns:
        Priority level: "critical", "high", "medium", "low"
    """
    # Critical: Very high risk + declining engagement + inactive
    if risk_score >= 0.85:
        if (engagement_trend and engagement_trend < -0.2) or (days_inactive and days_inactive > 10):
            return "critical"
        return "high"
    
    # High: High risk threshold
    elif risk_score >= 0.70:
        return "high"
    
    # Medium: Moderate risk
    elif risk_score >= 0.45:
        return "medium"
    
    # Low: Just above no-action threshold
    else:
        return "low"
