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

import backend.config as settings
from backend.config import trimester_week_number
from backend.services.feature_engineering import FeatureEngineer
from backend.services.calendar_scorer import get_current_week
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
    is_new_student: bool = False,
    week_number: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calculate risk score for a single student from DB-derived LMS features.

    Parameters
    ----------
    enrollments        : list of enrollment dicts (from StudentService)
    graded_components  : list of graded quiz/assignment dicts
    exam_records       : list of exam record dicts
    include_decisions  : if True, include intervention recommendation
    is_new_student     : if True, early-term score tolerance (weeks 1–3) in features
    week_number        : trimester week (1-based); default from config trimester start

    Returns
    -------
    dict with risk_score (0-100), engagement_score, retention_likelihood,
    dominant_risk_factor, risk_breakdown, and optional intervention fields.
    """
    try:
        wn = week_number if week_number is not None else trimester_week_number()
        current_week = get_current_week(settings.TRIMESTER_START_DATE)
        features = FeatureEngineer.calculate_all_features(
            enrollments,
            graded_components=graded_components or [],
            exam_records=exam_records or [],
            is_new_student=is_new_student,
            week_number=wn,
        )
        risk_score = RiskScorer.calculate_risk_score(
            features,
            graded_components=graded_components or [],
            program=None,
            current_week=current_week,
        )
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
            "model_type": "rule_based",
            "model_description": "Weighted engagement formula — not a trained ML model",
            "prediction_error": False,
        }

        if include_decisions:
            try:
                engagement_pattern = features.get("engagement_pattern")
                intervention = get_intervention_recommendation(
                    risk_score,
                    engagement_pattern=engagement_pattern,
                    features=features,
                )
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
        is_new = bool(s.get("is_new_student", False))
        if s.get("old_new_student") is not None:
            is_new = (str(s.get("old_new_student")).lower() == "new")
        wn = s.get("week_number")
        pred = calculate_student_risk(
            enrollments=s.get("enrollments", []),
            graded_components=s.get("graded_components", []),
            exam_records=s.get("exam_records", []),
            include_decisions=include_decisions,
            is_new_student=is_new,
            week_number=wn,
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
        "academic": lambda s: (
            (float(s["graded_quiz_score"]) / 100.0)
            if s.get("graded_quiz_score") is not None
            else None
        ),
        "engagement": lambda s: float(s.get("content_completion_score", 0) or 0) / 100.0,
        "consistency": lambda s: (
            (float(s["exam_attendance_rate"]) / 100.0)
            if s.get("exam_attendance_rate") is not None
            else None
        ),
        "intent": lambda s: (
            (float(s["graded_assignment_score"]) / 100.0)
            if s.get("graded_assignment_score") is not None
            else None
        ),
        "responsiveness": lambda s: (
            (float(s["exam_score"]) / 100.0)
            if s.get("exam_score") is not None
            else None
        ),
    }

    if signal_category not in signal_map:
        raise ValueError(
            "Invalid signal category. Must be one of: "
            f"{list(signal_map.keys())}"
        )

    signal_values = [signal_map[signal_category](s) for s in students]
    values = [v for v in signal_values if v is not None]
    if not students:
        return {
            "signal_category": signal_category,
            "total_students": 0,
            "mean": None,
            "median": None,
            "distribution": {"low": 0, "medium": 0, "high": 0},
        }

    n_students = len(students)
    mean_val = sum(values) / len(values) if values else None
    values.sort()
    median_val = values[len(values) // 2] if values else None
    low = sum(1 for v in values if v < 0.3)
    medium = sum(1 for v in values if 0.3 <= v < 0.7)
    high = sum(1 for v in values if v >= 0.7)

    return {
        "signal_category": signal_category,
        "total_students": n_students,
        "mean": None if mean_val is None else round(mean_val, 3),
        "median": None if median_val is None else round(median_val, 3),
        "distribution": {"low": low, "medium": medium, "high": high},
    }
