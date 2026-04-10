"""
Explainable Risk Formula Module
===============================

This module provides a transparent, auditable risk calculation formula.
The formula is rule-based and designed to be interpretable by stakeholders.

RISK SCORE FORMULA:
    risk_score = sum(weight_i * normalized_signal_i) for all signals

Signal weights for the five advisor-facing dimensions are derived from
``backend.config.FEATURE_WEIGHTS`` (same source as ``RiskScorer``), using
``SIGNAL_TO_FEATURE`` to roll up granular features into explainability labels.

NORMALIZATION:
    - All signals normalized to [0, 1] range
    - 0 = best possible (no risk indicator)
    - 1 = worst possible (highest risk indicator)

IMPORTANT: This formula is for EXPLAINABILITY and AUDITING purposes.
The actual ML model predictions should be used for decision-making.
This formula helps explain WHY a student has a certain risk level.
"""

from typing import Any, Dict, List

from backend.config import FEATURE_WEIGHTS

SIGNAL_TO_FEATURE = {
    "academic": ["content_completion", "quiz_engagement", "assignment"],
    "engagement": ["discussion", "time_investment"],
    "consistency": ["login_consistency"],
    "intent": ["content_completion"],
    "responsiveness": ["quiz_engagement"],
}


def get_signal_weights() -> Dict[str, float]:
    """
    Map explainability signal names to weights, summed from FEATURE_WEIGHTS.

    Returns:
        Dictionary mapping signal names to their aggregate weights.
    """
    return {
        signal: sum(FEATURE_WEIGHTS.get(k, 0.0) for k in keys)
        for signal, keys in SIGNAL_TO_FEATURE.items()
    }


def calculate_weighted_risk(signals: Dict[str, float]) -> float:
    """
    Calculate risk score using weighted sum of signal scores.

    This is the EXPLAINABLE formula - transparent and auditable.

    Args:
        signals: Dictionary with signal scores. Expected keys:
            - academic_signal_score
            - engagement_signal_score
            - consistency_signal_score
            - intent_signal_score
            - responsiveness_signal_score

    Returns:
        Risk score in [0.0, 1.0] range.
    """
    weights = get_signal_weights()

    # Map signal dict keys to weight keys
    signal_mapping = {
        "academic_signal_score": "academic",
        "engagement_signal_score": "engagement",
        "consistency_signal_score": "consistency",
        "intent_signal_score": "intent",
        "responsiveness_signal_score": "responsiveness",
    }

    risk = 0.0
    total_weight = 0.0

    for signal_key, weight_key in signal_mapping.items():
        signal_value = signals.get(signal_key, 0.5)  # Default to neutral

        # Validate signal value
        if signal_value is None or not isinstance(signal_value, (int, float)):
            signal_value = 0.5
        signal_value = max(0.0, min(1.0, float(signal_value)))

        weight = weights.get(weight_key, 0.0)
        risk += weight * signal_value
        total_weight += weight

    # Normalize if weights don't sum to 1.0
    if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
        risk = risk / total_weight

    # Clamp final result
    return max(0.0, min(1.0, risk))


def get_risk_contribution_breakdown(signals: Dict[str, float]) -> List[Dict]:
    """
    Calculate how much each signal contributes to the final risk score.

    This is useful for explaining WHY a student has a certain risk level.

    Args:
        signals: Dictionary with signal scores.

    Returns:
        List of contribution breakdowns, sorted by contribution (descending).
        Each item contains:
            - signal_name: Human-readable signal name
            - weight: The weight assigned to this signal
            - score: The raw signal score [0-1]
            - contribution: weight * score (how much this adds to risk)
            - percentage: What percentage of total risk this represents
    """
    weights = get_signal_weights()

    signal_display_names = {
        "academic": "Academic Performance",
        "engagement": "Platform Engagement",
        "consistency": "Attendance Consistency",
        "intent": "Performance Trajectory",
        "responsiveness": "Responsiveness",
    }

    signal_mapping = {
        "academic_signal_score": "academic",
        "engagement_signal_score": "engagement",
        "consistency_signal_score": "consistency",
        "intent_signal_score": "intent",
        "responsiveness_signal_score": "responsiveness",
    }

    breakdown: List[Dict[str, Any]] = []
    total_contribution = 0.0

    for signal_key, weight_key in signal_mapping.items():
        signal_value = signals.get(signal_key, 0.5)
        if signal_value is None or not isinstance(signal_value, (int, float)):
            signal_value = 0.5
        signal_value = max(0.0, min(1.0, float(signal_value)))

        weight = weights.get(weight_key, 0.0)
        contribution = weight * signal_value
        total_contribution += contribution

        breakdown.append(
            {
                "signal_name": signal_display_names.get(weight_key, weight_key),
                "signal_key": weight_key,
                "weight": round(weight, 3),
                "score": round(signal_value, 3),
                "contribution": round(contribution, 4),
                "percentage": 0,  # Will be calculated below
            }
        )

    # Calculate percentage contribution
    if total_contribution > 0:
        for item in breakdown:
            item["percentage"] = round((item["contribution"] / total_contribution) * 100, 1)

    # Sort by contribution descending
    breakdown.sort(key=lambda x: x["contribution"], reverse=True)

    return breakdown


def explain_risk_score(risk_score: float, signals: Dict[str, float]) -> Dict:
    """
    Generate a human-readable explanation of a risk score.

    Args:
        risk_score: The calculated risk score (0-1)
        signals: The signal scores used

    Returns:
        Dictionary with:
            - risk_score: The score
            - risk_category: 'low', 'moderate', 'high', 'critical'
            - breakdown: Contribution breakdown
            - top_factors: Top 2 contributing factors
            - explanation: Human-readable explanation
    """
    # Categorize risk
    if risk_score < 0.30:
        category = "low"
        category_description = "on track"
    elif risk_score < 0.60:
        category = "moderate"
        category_description = "showing some warning signs"
    elif risk_score < 0.80:
        category = "high"
        category_description = "at significant risk"
    else:
        category = "critical"
        category_description = "requiring immediate attention"

    breakdown = get_risk_contribution_breakdown(signals)
    top_factors = breakdown[:2] if len(breakdown) >= 2 else breakdown

    # Generate explanation
    if len(top_factors) >= 2:
        explanation = (
            f"This student is {category_description} with a risk score of "
            f"{risk_score*100:.0f}%. The primary contributing factors are "
            f"{top_factors[0]['signal_name']} ({top_factors[0]['percentage']:.0f}% of risk) "
            f"and {top_factors[1]['signal_name']} ({top_factors[1]['percentage']:.0f}% of risk)."
        )
    elif len(top_factors) == 1:
        explanation = (
            f"This student is {category_description} with a risk score of "
            f"{risk_score*100:.0f}%. The primary contributing factor is "
            f"{top_factors[0]['signal_name']} ({top_factors[0]['percentage']:.0f}% of risk)."
        )
    else:
        explanation = f"This student is {category_description} with a risk score of {risk_score*100:.0f}%."

    return {
        "risk_score": round(risk_score, 3),
        "risk_percentage": round(risk_score * 100, 1),
        "risk_category": category,
        "category_description": category_description,
        "breakdown": breakdown,
        "top_factors": top_factors,
        "explanation": explanation,
        "weights_used": get_signal_weights(),
    }


def simulate_what_if(
    current_signals: Dict[str, float],
    adjustments: Dict[str, float],
) -> Dict:
    """
    Simulate risk score if certain signals change.

    Args:
        current_signals: Current signal scores
        adjustments: Changes to apply (e.g., {'academic_signal_score': 0.3})

    Returns:
        Dictionary with current risk, simulated risk, and difference.
    """
    # Calculate current risk
    current_risk = calculate_weighted_risk(current_signals)

    # Apply adjustments
    simulated_signals = current_signals.copy()
    for key, value in adjustments.items():
        if key in simulated_signals:
            simulated_signals[key] = max(0.0, min(1.0, value))

    # Calculate simulated risk
    simulated_risk = calculate_weighted_risk(simulated_signals)

    # Get explanations
    current_explanation = explain_risk_score(current_risk, current_signals)
    simulated_explanation = explain_risk_score(simulated_risk, simulated_signals)

    return {
        "current_risk": round(current_risk, 3),
        "simulated_risk": round(simulated_risk, 3),
        "risk_change": round(simulated_risk - current_risk, 3),
        "risk_change_percentage": round((simulated_risk - current_risk) * 100, 1),
        "current_category": current_explanation["risk_category"],
        "simulated_category": simulated_explanation["risk_category"],
        "category_changed": current_explanation["risk_category"]
        != simulated_explanation["risk_category"],
        "adjustments_applied": adjustments,
        "current_breakdown": current_explanation["breakdown"],
        "simulated_breakdown": simulated_explanation["breakdown"],
    }
