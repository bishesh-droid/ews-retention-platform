"""
Risk Consistency Checker — Section 6
Ensures coherence between rule-based risk scores and ML predictions.

TODO: This module is currently inactive for ML comparisons — no trained model exists yet.
The discrepancy detection logic is reserved for future use when a real ML model is available.
See backend/ml/training/calibrate.py for the path to real ML.

Responsibilities (when ML is available)
---------------------------------------
1. Shared feature base for both rule-based and ML scoring.
2. Detect contradictions (rule says LOW, ML says HIGH, or vice-versa).
3. Log discrepancies to logs/risk_discrepancy.log.
4. Return a unified risk object:
   - If ML works: use ML probability as primary, rule-based as secondary.
   - If ML fails: fall back to rule-based, flag the fallback.
5. Never crash the API.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

DISCREPANCY_LOG = LOG_DIR / "risk_discrepancy.log"

logger = logging.getLogger(__name__)
_discrepancy_logger = logging.getLogger("ews.risk_discrepancy")
if not _discrepancy_logger.handlers:
    _discrepancy_logger.setLevel(logging.WARNING)
    fh = logging.FileHandler(DISCREPANCY_LOG, encoding="utf-8")
    fh.setFormatter(
        logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    )
    _discrepancy_logger.addHandler(fh)


# Contradiction detection thresholds
CONTRADICTION_THRESHOLD = 0.30  # If |ml_prob - rule_score| > this, flag discrepancy


def _rule_based_score(features: Dict[str, Any]) -> float:  # noqa: C901
    """
    Compute a 0-1 rule-based risk score from canonical features.
    Uses the SAME feature keys as the ML model to ensure consistency.
    """
    att = _safe_float(features.get("attendance_rate"), 50.0)
    quiz = _safe_float(features.get("avg_quiz_score"), 50.0)
    assign = _safe_float(features.get("assignment_avg"), 50.0)
    logins = _safe_float(features.get("num_logins"), 10.0)
    freq = _safe_float(features.get("engagement_frequency"), 0.5)
    decay = _safe_float(features.get("engagement_decay"), 1.0)

    score = 0.0

    # Attendance signals (weight: 35%)
    if att < 40:
        score += 0.35
    elif att < 60:
        score += 0.20
    elif att < 75:
        score += 0.10

    # Academic performance signals (weight: 35%)
    quiz_assign_avg = (quiz + assign) / 2
    if quiz_assign_avg < 35:
        score += 0.35
    elif quiz_assign_avg < 50:
        score += 0.20
    elif quiz_assign_avg < 65:
        score += 0.10

    # Engagement signals (weight: 20%)
    if logins < 5:
        score += 0.20
    elif logins < 15:
        score += 0.10

    # Trend signals (weight: 10%)
    if freq < 0.3:
        score += 0.07
    if decay < 0.5:
        score += 0.03

    return round(min(1.0, score), 4)


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        import numpy as np

        v = float(val)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def get_unified_risk(
    student_id: str,
    features: Dict[str, Any],
    ml_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compute a unified risk object combining ML and rule-based signals.

    Parameters
    ----------
    student_id : str
    features : dict
        Canonical feature dict (same keys as FEATURE_COLS).
    ml_result : dict, optional
        Result from predict_model.predict(). If None, ML is skipped.

    Returns
    -------
    dict with unified risk assessment.
    """
    timestamp = datetime.now().isoformat()
    rule_score = _rule_based_score(features)
    rule_label = _score_to_label(rule_score)

    # Case 1: ML result available and not a fallback
    if ml_result and not ml_result.get("fallback_used", False):
        ml_prob = float(ml_result.get("dropout_probability", rule_score))
        ml_label = ml_result.get("risk_label", rule_label)

        # Check for contradiction
        discrepancy = abs(ml_prob - rule_score)
        if discrepancy >= CONTRADICTION_THRESHOLD:
            _log_discrepancy(
                student_id=student_id,
                ml_prob=ml_prob,
                ml_label=ml_label,
                rule_score=rule_score,
                rule_label=rule_label,
                discrepancy=discrepancy,
            )

        return {
            "student_id": student_id,
            "final_risk_label": ml_label,  # ML is primary
            "final_risk_score": ml_prob,
            "ml_probability": ml_prob,
            "rule_based_score": rule_score,
            "rule_based_label": rule_label,
            "ml_available": True,
            "discrepancy": round(discrepancy, 4),
            "discrepancy_flagged": discrepancy >= CONTRADICTION_THRESHOLD,
            "model_version": ml_result.get("model_version", "unknown"),
            "top_contributing_features": ml_result.get("top_contributing_features", []),
            "prediction_timestamp": ml_result.get("prediction_timestamp", timestamp),
        }

    # Case 2: ML unavailable / fallback → use rule-based
    logger.warning(
        f"ML unavailable for student={student_id} — returning rule-based risk only"
    )
    return {
        "student_id": student_id,
        "final_risk_label": rule_label,
        "final_risk_score": rule_score,
        "ml_probability": None,
        "rule_based_score": rule_score,
        "rule_based_label": rule_label,
        "ml_available": False,
        "discrepancy": None,
        "discrepancy_flagged": False,
        "model_version": "rule-based-only",
        "top_contributing_features": [],
        "prediction_timestamp": timestamp,
        "fallback_reason": (
            ml_result.get("fallback_reason", "ML not available")
            if ml_result
            else "ML not called"
        ),
    }


def _score_to_label(score: float) -> str:
    if score >= 0.65:
        return "HIGH"
    elif score >= 0.40:
        return "MEDIUM"
    return "LOW"


def _log_discrepancy(
    student_id: str,
    ml_prob: float,
    ml_label: str,
    rule_score: float,
    rule_label: str,
    discrepancy: float,
):
    """Write a structured discrepancy record to the discrepancy log."""
    record = {
        "student_id": student_id,
        "ml_prob": round(ml_prob, 4),
        "ml_label": ml_label,
        "rule_score": round(rule_score, 4),
        "rule_label": rule_label,
        "discrepancy": round(discrepancy, 4),
        "severity": "HIGH" if discrepancy >= 0.50 else "MEDIUM",
    }
    _discrepancy_logger.warning(json.dumps(record))
    logger.warning(
        f"RISK DISCREPANCY: student={student_id} | ML={ml_label}({ml_prob:.2f}) "
        f"vs Rule={rule_label}({rule_score:.2f}) | delta={discrepancy:.2f}"
    )
