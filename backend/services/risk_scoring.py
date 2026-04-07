"""
Rule-based risk scoring for the EWS platform.

This scorer is intentionally model-free so the system remains operational
without training data. It only consumes present-time engagement features
from `FeatureEngineer.calculate_all_features()`.
"""

from math import isfinite
from typing import Dict, Optional, Tuple

from backend.config import (
    RISK_THRESHOLD_MEDIUM,
    RISK_THRESHOLD_HIGH,
)


class RiskScorer:
    """Calculate dropout risk from current engagement/activity signals."""

    # Feature schema aligned with backend/services/feature_engineering.py.
    # We intentionally exclude graded/exam features from the fallback score
    # to avoid chronology leakage and keep scoring usable early in term.
    FEATURE_WEIGHTS: Dict[str, float] = {
        "content_completion_score": 0.30,
        "login_consistency_score": 0.20,
        "quiz_engagement_score": 0.15,
        "assignment_score": 0.15,
        "time_investment_score": 0.10,
        "discussion_engagement_score": 0.10,
    }

    FEATURE_LABELS: Dict[str, str] = {
        "content_completion_score": "Content Completion",
        "login_consistency_score": "Login Consistency",
        "quiz_engagement_score": "Quiz Engagement",
        "assignment_score": "Assignment Submissions",
        "time_investment_score": "Time Investment",
        "discussion_engagement_score": "Discussion Engagement",
    }

    NEUTRAL_RISK_SCORE = 50.0

    @staticmethod
    def normalize_risk_to_0_100(raw_value: object) -> Optional[float]:
        """Pure helper: normalize risk values from either [0,1] or [0,100]."""
        if raw_value is None:
            return None
        try:
            v = float(raw_value)
        except (TypeError, ValueError):
            return None
        if not isfinite(v):
            return None
        if 0.0 <= v <= 1.0:
            v *= 100.0
        return round(max(0.0, min(100.0, v)), 2)

    @staticmethod
    def _to_valid_score(raw_value: object) -> Optional[float]:
        """Convert a raw feature to bounded [0,100] score or None."""
        if raw_value is None:
            return None
        try:
            score = float(raw_value)
        except (TypeError, ValueError):
            return None
        if not isfinite(score):
            return None
        return max(0.0, min(100.0, score))

    @staticmethod
    def _compute_weighted_engagement(features: Dict) -> Tuple[float, float]:
        """
        Return weighted engagement and observed weight mass.
        Missing values do not default to 0 (which would inflate risk).
        """
        weighted_sum = 0.0
        observed_weight = 0.0

        for feature_key, weight in RiskScorer.FEATURE_WEIGHTS.items():
            score = RiskScorer._to_valid_score(features.get(feature_key))
            if score is None:
                continue
            weighted_sum += weight * score
            observed_weight += weight

        if observed_weight == 0.0:
            return 0.0, 0.0

        return weighted_sum / observed_weight, observed_weight

    @staticmethod
    def calculate_risk_score(features: Dict) -> float:
        """
        Calculate overall risk score from available engagement features.

        Behavior:
        - Missing data does not imply worst risk.
        - Sparse observations are shrunk toward neutral (50).
        - Includes a bounded zero-progress penalty.
        """
        weighted_engagement, observed_weight = RiskScorer._compute_weighted_engagement(features)
        total_weight = sum(RiskScorer.FEATURE_WEIGHTS.values())

        if observed_weight == 0.0 or total_weight <= 0.0:
            return RiskScorer.NEUTRAL_RISK_SCORE

        base_risk = 100.0 - weighted_engagement

        # Confidence from feature coverage; avoids overconfident extremes when sparse.
        coverage = max(0.0, min(1.0, observed_weight / total_weight))
        risk_score = (base_risk * coverage) + (RiskScorer.NEUTRAL_RISK_SCORE * (1.0 - coverage))

        # Zero-progress adds bounded risk directly with nonlinear sensitivity.
        # This increases penalty only when zero-progress dominates course load.
        zero_ratio = RiskScorer._to_valid_score((features.get("zero_progress_ratio", 0.0) or 0.0) * 100.0)
        if zero_ratio is not None:
            z = zero_ratio / 100.0
            risk_score += min(15.0, (z ** 1.5) * 15.0)

        if not isfinite(risk_score):
            return RiskScorer.NEUTRAL_RISK_SCORE

        return round(max(0.0, min(100.0, risk_score)), 2)

    @staticmethod
    def get_risk_category(risk_score: float) -> str:
        """Categorize risk score into low/medium/high."""
        if risk_score < RISK_THRESHOLD_MEDIUM:
            return "low"
        if risk_score < RISK_THRESHOLD_HIGH:
            return "medium"
        return "high"

    @staticmethod
    def get_retention_likelihood(risk_score: float) -> str:
        """Convert risk score to retention likelihood label."""
        if risk_score < 20:
            return "Very High"
        if risk_score < 40:
            return "High"
        if risk_score < 60:
            return "Medium"
        if risk_score < 80:
            return "Low"
        return "Very Low"

    @staticmethod
    def get_dominant_risk_factor(features: Dict) -> str:
        """Identify which observed component contributes most to risk."""
        risk_contributions: Dict[str, float] = {}

        for feature_key, weight in RiskScorer.FEATURE_WEIGHTS.items():
            score = RiskScorer._to_valid_score(features.get(feature_key))
            if score is None:
                continue
            label = RiskScorer.FEATURE_LABELS[feature_key]
            risk_contributions[label] = (100.0 - score) * weight

        if not risk_contributions:
            return "Insufficient Data"
        return max(risk_contributions, key=risk_contributions.get)

    @staticmethod
    def get_risk_breakdown(features: Dict) -> Dict:
        """Return risk-by-component breakdown for observed features."""
        breakdown: Dict[str, object] = {}

        for feature_key in RiskScorer.FEATURE_WEIGHTS:
            score = RiskScorer._to_valid_score(features.get(feature_key))
            if score is None:
                breakdown[f"{feature_key.replace('_score', '')}_risk"] = None
            else:
                breakdown[f"{feature_key.replace('_score', '')}_risk"] = round(100.0 - score, 2)

        breakdown["weights"] = RiskScorer.FEATURE_WEIGHTS
        breakdown["coverage"] = round(
            (
                sum(
                    weight
                    for key, weight in RiskScorer.FEATURE_WEIGHTS.items()
                    if RiskScorer._to_valid_score(features.get(key)) is not None
                )
                / sum(RiskScorer.FEATURE_WEIGHTS.values())
            ),
            3,
        )
        return breakdown

    @staticmethod
    def validate_risk_score(risk_score: float) -> bool:
        """Validate that risk score is finite and within [0, 100]."""
        if not isinstance(risk_score, (int, float)):
            return False
        if not isfinite(float(risk_score)):
            return False
        return 0.0 <= float(risk_score) <= 100.0

    @staticmethod
    def compare_old_vs_new_formula(features: Dict) -> Dict[str, float]:
        """
        Pure helper for tests/docs: compare legacy and current formula outcomes.

        Legacy approximation:
          risk_old = 100 - weighted_engagement
          if zero_progress_ratio >= 0.8: weighted_engagement *= 0.5
        """
        weighted_engagement, observed_weight = RiskScorer._compute_weighted_engagement(features)
        if observed_weight == 0.0:
            old_risk = 100.0
        else:
            old_weighted = weighted_engagement
            if float(features.get("zero_progress_ratio", 0.0) or 0.0) >= 0.8:
                old_weighted *= 0.5
            old_risk = max(0.0, min(100.0, 100.0 - old_weighted))

        new_risk = RiskScorer.calculate_risk_score(features)
        return {
            "old_risk_score": round(old_risk, 2),
            "new_risk_score": round(new_risk, 2),
            "delta_new_minus_old": round(new_risk - old_risk, 2),
        }
