"""
EWS Engine — core risk computation facade.

The old implementation called backend/ml/inference/predictor.py which used
a 32-feature absrate/mpa schema incompatible with this platform's LMS data.
That module has been removed.

This implementation delegates to the services layer which uses DB-backed
LMS features (content, quiz, login, time, grades) — the only data we
actually have from the ingested XLSX files.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.services.feature_engineering import FeatureEngineer
from backend.services.risk_scoring import RiskScorer
from backend.services.core.decision_engine import (
    get_intervention_recommendation,
    should_trigger_intervention,
    calculate_intervention_priority,
)

logger = logging.getLogger(__name__)


def calculate_student_risk(
    enrollments: List[Dict],
    graded_components: Optional[List[Dict]] = None,
    exam_records: Optional[List[Dict]] = None,
    include_decisions: bool = False,
) -> Dict[str, Any]:
    """
    Calculate risk score for a single student from DB-derived LMS features.

    Parameters
    ----------
    enrollments        : list of enrollment dicts (from StudentService)
    graded_components  : list of graded quiz/assignment dicts
    exam_records       : list of exam record dicts
    include_decisions  : if True, include intervention recommendation

    Returns
    -------
    dict with risk_score (0-100), engagement_score, retention_likelihood,
    dominant_risk_factor, risk_breakdown, and optional intervention fields.
    """
    try:
        features = FeatureEngineer.calculate_all_features(
            enrollments,
            graded_components=graded_components or [],
            exam_records=exam_records or [],
        )
        risk_score = RiskScorer.calculate_risk_score(features)
        risk_category = RiskScorer.get_risk_category(risk_score)
        retention = RiskScorer.get_retention_likelihood(risk_score)
        dominant = RiskScorer.get_dominant_risk_factor(features)
        breakdown = RiskScorer.get_risk_breakdown(features)

        # Engagement score: inverse of risk as a normalised 0-100 value
        engagement_score = round(100.0 - risk_score, 2)

        response: Dict[str, Any] = {
            "risk_score": round(risk_score, 2),
            "engagement_score": engagement_score,
            "retention_likelihood": retention,
            "risk_category": risk_category,
            "dominant_risk_factor": dominant,
            "risk_breakdown": breakdown,
            "model_version": "rule-based-v1",
            "prediction_error": False,
        }

        if include_decisions:
            try:
                intervention = get_intervention_recommendation(risk_score)
                priority = calculate_intervention_priority(risk_score)
                response["intervention_recommendation"] = {
                    "threshold_category": intervention["threshold_category"],
                    "action_type": intervention["action_type"],
                    "channels": intervention["channels"],
                    "assigned_team": intervention["assigned_team"],
                    "priority": priority,
                    "urgency": intervention["urgency"],
                    "description": intervention["description"],
                }
            except Exception as exc:
                logger.error(f"Intervention recommendation failed: {exc}")
                response["intervention_recommendation"] = None

        return response

    except Exception as exc:
        logger.error(f"Error calculating risk: {exc}", exc_info=True)
        return {
            "risk_score": 50.0,
            "engagement_score": 50.0,
            "retention_likelihood": "Unknown",
            "risk_category": "medium",
            "dominant_risk_factor": "Unknown",
            "risk_breakdown": {},
            "model_version": "error-fallback",
            "prediction_error": True,
        }


def batch_predict(
    students: List[Dict[str, Any]],
    include_decisions: bool = False,
) -> List[Dict[str, Any]]:
    """
    Compute predictions for a list of students.

    Each entry in `students` must have keys:
        student_id, enrollments, graded_components, exam_records
    """
    results = []
    for s in students:
        pred = calculate_student_risk(
            enrollments=s.get("enrollments", []),
            graded_components=s.get("graded_components", []),
            exam_records=s.get("exam_records", []),
            include_decisions=include_decisions,
        )
        pred["student_id"] = s.get("student_id", "unknown")
        results.append(pred)
    return results


def get_signal_summary(
    students: List[Dict[str, Any]],
    signal_category: str,
) -> Dict[str, Any]:
    """
    Backward-compatible summary helper expected by core package imports.
    """
    signal_map = {
        "academic": lambda s: float(s.get("graded_quiz_score", 0) or 0) / 100.0,
        "engagement": lambda s: float(s.get("content_completion_score", 0) or 0) / 100.0,
        "consistency": lambda s: float(s.get("exam_attendance_rate", 0) or 0) / 100.0,
        "intent": lambda s: float(s.get("graded_assignment_score", 0) or 0) / 100.0,
        "responsiveness": lambda s: float(s.get("exam_score", 0) or 0) / 100.0,
    }

    if signal_category not in signal_map:
        raise ValueError(
            "Invalid signal category. Must be one of: "
            f"{list(signal_map.keys())}"
        )

    values = [signal_map[signal_category](s) for s in students]
    if not values:
        return {
            "signal_category": signal_category,
            "total_students": 0,
            "mean": 0.0,
            "median": 0.0,
            "distribution": {"low": 0, "medium": 0, "high": 0},
        }

    values.sort()
    n = len(values)
    mean_val = sum(values) / n
    median_val = values[n // 2]
    low = sum(1 for v in values if v < 0.3)
    medium = sum(1 for v in values if 0.3 <= v < 0.7)
    high = sum(1 for v in values if v >= 0.7)

    return {
        "signal_category": signal_category,
        "total_students": n,
        "mean": round(mean_val, 3),
        "median": round(median_val, 3),
        "distribution": {"low": low, "medium": medium, "high": high},
    }
