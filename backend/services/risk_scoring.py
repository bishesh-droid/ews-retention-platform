"""
Rule-based risk scoring for the EWS platform.

This scorer is intentionally model-free so the system remains operational
without training data. It only consumes present-time engagement features
from `FeatureEngineer.calculate_all_features()`.
"""

from math import isfinite
from typing import Dict, Optional, Tuple

from backend.config import (
    CALENDAR_RISK_BLEND_WEIGHT,
    FEATURE_WEIGHTS,
    RISK_THRESHOLD_HIGH,
    RISK_THRESHOLD_MEDIUM,
)
from backend.services.calendar_scorer import calculate_calendar_adjusted_risk

# Logical config keys -> keys returned by FeatureEngineer.calculate_all_features()
_LOGICAL_TO_FEATURE_KEY: Dict[str, str] = {
    "content_completion": "content_completion_score",
    "login_consistency": "login_consistency_score",
    "quiz_engagement": "quiz_engagement_score",
    "assignment": "assignment_score",
    "time_investment": "time_investment_score",
    "discussion": "discussion_engagement_score",
    "self_directed_learning": "self_directed_learning_score",
}


def _feature_score_key(logical: str) -> str:
    return _LOGICAL_TO_FEATURE_KEY.get(logical, f"{logical}_score")


class RiskScorer:
    """Calculate dropout risk from current engagement/activity signals."""

    # Feature schema aligned with backend/services/feature_engineering.py.
    # We intentionally exclude graded/exam features from the fallback score
    # to avoid chronology leakage and keep scoring usable early in term.
    # Weights are loaded from backend.config.FEATURE_WEIGHTS (env-overridable).

    FEATURE_LABELS: Dict[str, str] = {
        "content_completion_score": "Content Completion",
        "login_consistency_score": "Login Consistency",
        "quiz_engagement_score": "Quiz Engagement",
        "assignment_score": "Assignment Submissions",
        "time_investment_score": "Time Investment",
        "discussion_engagement_score": "Discussion Engagement",
        "self_directed_learning_score": "Self-Directed Learning",
    }

    # Legacy K-12 weights for backward compatibility with old tests
    # These map to the feature keys expected by test_risk_scoring.py
    WEIGHTS: Dict[str, float] = {
        "attendance": 0.30,
        "academic": 0.40,
        "behavioral": 0.15,
        "stability": 0.15,
    }

    # Legacy feature key mapping for tests using attendance_score, academic_score, etc.
    _LEGACY_FEATURE_KEYS: Dict[str, str] = {
        "attendance": "attendance_score",
        "academic": "academic_score",
        "behavioral": "behavioral_score",
        "stability": "stability_score",
    }

    NEUTRAL_RISK_SCORE = 50.0

    @staticmethod
    def normalize_risk_to_0_100(raw_value: object) -> Optional[float]:
        """Pure helper: normalize risk values from either [0,1] or [0,100]."""
        if raw_value is None:
            return None
        try:
            v = float(raw_value)  # type: ignore[arg-type]
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
            score = float(raw_value)  # type: ignore[arg-type]
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

        For self_directed_learning: high score = low risk, so we invert.
        """
        weighted_sum = 0.0
        observed_weight = 0.0

        for logical_key, weight in FEATURE_WEIGHTS.items():
            score = RiskScorer._to_valid_score(features.get(_feature_score_key(logical_key)))
            if score is None:
                continue
            # Self-directed learning is a risk REDUCER - invert the score
            # High SDL score (100) -> 0 risk contribution, Low SDL (0) -> 100 risk contribution
            if logical_key == "self_directed_learning":
                score = 100.0 - score
            weighted_sum += weight * score
            observed_weight += weight

        if observed_weight == 0.0:
            return 0.0, 0.0

        return weighted_sum / observed_weight, observed_weight

    @staticmethod
    def _is_legacy_k12_features(features: Dict) -> bool:
        """Detect if features dict contains legacy K-12 style keys."""
        legacy_keys = ['attendance_score', 'academic_score', 'behavioral_score', 'stability_score']
        return any(k in features for k in legacy_keys)

    @staticmethod
    def _compute_weighted_engagement_legacy(features: Dict) -> Tuple[float, float]:
        """
        Compute weighted engagement using legacy K-12 weights.
        For backward compatibility with old tests.
        """
        weighted_sum = 0.0
        observed_weight = 0.0

        for logical_key, weight in RiskScorer.WEIGHTS.items():
            score_key = RiskScorer._LEGACY_FEATURE_KEYS.get(logical_key, f"{logical_key}_score")
            score = RiskScorer._to_valid_score(features.get(score_key))
            if score is None:
                continue
            weighted_sum += weight * score
            observed_weight += weight

        if observed_weight == 0.0:
            return 0.0, 0.0

        return weighted_sum / observed_weight, observed_weight

    @staticmethod
    def calculate_risk_score(
        features: Dict,
        *,
        graded_components: Optional[list] = None,
        program: Optional[str] = None,
        current_week: int | None = None,
    ) -> float:
        """
        Calculate overall risk score from available engagement features.

        Behavior:
        - Missing data does not imply worst risk.
        - Sparse observations are shrunk toward neutral (50).
        - Includes a bounded zero-progress penalty.
        - Detects and handles legacy K-12 feature format for backward compatibility.
        """
        # ML-3: Sanitize input features - handle NaN/null values
        import math
        import logging
        logger = logging.getLogger(__name__)

        required_keys = set(FEATURE_WEIGHTS.keys())
        missing_keys = []

        for key in list(features.keys()):
            val = features[key]
            # Handle None or NaN values
            if val is None or (isinstance(val, float) and math.isnan(val)):
                features[key] = 0.0
                if key in required_keys:
                    missing_keys.append(key)
            else:
                # Clamp to valid range [0.0, 100.0]
                try:
                    features[key] = max(0.0, min(100.0, float(val)))
                except (TypeError, ValueError):
                    features[key] = 0.0
                    if key in required_keys:
                        missing_keys.append(key)

        # Log warning for missing required features
        if missing_keys:
            logger.warning(
                f"ML-3: Missing or invalid required features for risk scoring: {missing_keys}. "
                f"Substituting 0.0 for missing values."
            )

        # Check for legacy K-12 features and use appropriate computation
        if RiskScorer._is_legacy_k12_features(features):
            weighted_engagement, observed_weight = RiskScorer._compute_weighted_engagement_legacy(features)
            total_weight = sum(RiskScorer.WEIGHTS.values())
        else:
            weighted_engagement, observed_weight = RiskScorer._compute_weighted_engagement(features)
            total_weight = sum(FEATURE_WEIGHTS.values())

        if observed_weight == 0.0 or total_weight <= 0.0:
            existing_score = RiskScorer.NEUTRAL_RISK_SCORE
        else:
            base_risk = 100.0 - weighted_engagement

            # Confidence from feature coverage; avoids overconfident extremes when sparse.
            coverage = max(0.0, min(1.0, observed_weight / total_weight))
            existing_score = (base_risk * coverage) + (RiskScorer.NEUTRAL_RISK_SCORE * (1.0 - coverage))

            # Zero-progress adds bounded risk directly with nonlinear sensitivity.
            # This increases penalty only when zero-progress dominates course load.
            zero_ratio = RiskScorer._to_valid_score((features.get("zero_progress_ratio", 0.0) or 0.0) * 100.0)
            if zero_ratio is not None:
                z = zero_ratio / 100.0
                existing_score += min(15.0, (z**1.5) * 15.0)

        if not isfinite(existing_score):
            existing_score = RiskScorer.NEUTRAL_RISK_SCORE

        risk_score = existing_score

        if current_week is not None:
            cal = calculate_calendar_adjusted_risk(
                student_features=features,
                graded_components=graded_components or [],
                program=program,
                current_week=int(current_week),
            )
            calendar_risk_score = float(cal.get("calendar_risk_score") or 0.0)
            risk_score = (1.0 - CALENDAR_RISK_BLEND_WEIGHT) * existing_score + CALENDAR_RISK_BLEND_WEIGHT * calendar_risk_score

            # Mutate features so callers can include these signals in responses.
            features["calendar_risk_score"] = round(calendar_risk_score, 2)
            features["overdue_components"] = cal.get("overdue_components", [])
            features["calendar_expected_pct"] = cal.get("expected_pct", 0.0)
            features["calendar_actual_pct"] = cal.get("actual_pct", 0.0)

        if not isfinite(risk_score):
            return RiskScorer.NEUTRAL_RISK_SCORE

        # Ghost student override: Force high risk for students with zero engagement
        # This happens AFTER all other calculations so it cannot be diluted
        ghost_info = features.get("ghost_info", {})
        if ghost_info.get("is_ghost"):
            risk_score = 95.0
            features["risk_override_reason"] = f"ghost_student:{ghost_info.get('ghost_type')}"
            features["requires_activation_outreach"] = True

        # Academic flags overrides (exam-based high-signal indicators)
        flags = features.get("academic_flags", {})

        if flags.get("dropout_intent"):
            # Strongest signal: student requested refund / indicated intent to leave
            risk_score = 100.0
            features["risk_score"] = risk_score
            features["risk_override_reason"] = "dropout_intent_detected"

        elif flags.get("ufm_flagged"):
            # Academic misconduct: elevated risk
            risk_score = min(100.0, risk_score + 20.0)
            features["risk_score"] = risk_score
            features["risk_override_reason"] = "ufm_flagged"

        elif flags.get("unknown_defaulter"):
            # No reason given for absence: elevated risk
            risk_score = min(100.0, risk_score + 15.0)
            features["risk_score"] = risk_score
            features["risk_override_reason"] = "exam_defaulter_no_reason"

        elif flags.get("deferred"):
            # Deferred students are NOT at risk — officially continuing next term
            risk_score = 0.0
            features["risk_score"] = risk_score
            features["risk_override_reason"] = "formally_deferred"
            features["suppress_intervention"] = True

        elif flags.get("health_support_needed"):
            # Do not change risk score — but route to welfare team
            features["health_referral_needed"] = True

        final_score = round(max(0.0, min(100.0, risk_score)), 1)  # D6-2: Standardised to 1 decimal
        
        # ML-4: Log prediction to audit trail if student_id is available in features
        student_id = features.get("student_id")
        if student_id:
            RiskScorer._log_prediction(
                student_id=student_id,
                model_version=features.get("model_version", "unknown"),
                input_features=features,
                output_score=final_score,
                output_category=RiskScorer.get_risk_category(final_score),
            )
        
        return final_score

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

        # Handle legacy K-12 features
        if RiskScorer._is_legacy_k12_features(features):
            for logical_key, weight in RiskScorer.WEIGHTS.items():
                score_key = RiskScorer._LEGACY_FEATURE_KEYS.get(logical_key, f"{logical_key}_score")
                score = RiskScorer._to_valid_score(features.get(score_key))
                if score is None:
                    continue
                risk_contributions[logical_key] = (100.0 - score) * weight
        else:
            for logical_key, weight in FEATURE_WEIGHTS.items():
                score_key = _feature_score_key(logical_key)
                score = RiskScorer._to_valid_score(features.get(score_key))
                if score is None:
                    continue
                label = RiskScorer.FEATURE_LABELS[score_key]
                risk_contributions[label] = (100.0 - score) * weight

        if not risk_contributions:
            return "Insufficient Data"
        return max(risk_contributions, key=lambda k: risk_contributions[k])

    @staticmethod
    def get_risk_breakdown(features: Dict) -> Dict:
        """Return risk-by-component breakdown for observed features."""
        breakdown: Dict[str, object] = {}

        for logical_key in FEATURE_WEIGHTS:
            score_key = _feature_score_key(logical_key)
            score = RiskScorer._to_valid_score(features.get(score_key))
            suffix = score_key.replace("_score", "")
            if score is None:
                breakdown[f"{suffix}_risk"] = None
            else:
                breakdown[f"{suffix}_risk"] = round(100.0 - score, 2)

        breakdown["weights"] = {
            _feature_score_key(k): v for k, v in FEATURE_WEIGHTS.items()
        }
        breakdown["coverage"] = round(
            (
                sum(
                    weight
                    for logical_key, weight in FEATURE_WEIGHTS.items()
                    if RiskScorer._to_valid_score(features.get(_feature_score_key(logical_key)))
                    is not None
                )
                / sum(FEATURE_WEIGHTS.values())
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
    def _log_prediction(
        student_id: str,
        model_version: str,
        input_features: Dict,
        output_score: float,
        output_category: str,
        source: str = "api",
    ) -> None:
        """
        ML-4: Log prediction to audit trail (PredictionLog table).
        
        This is a best-effort logging — failures are logged but don't
        block the prediction response.
        """
        try:
            from datetime import datetime, timezone
            from backend.database.connection import SessionLocal
            from backend.database.models.prediction_log import PredictionLog
            
            db = SessionLocal()
            try:
                log_entry = PredictionLog(
                    student_id=student_id,
                    model_version=model_version,
                    input_features=dict(input_features),  # Copy to avoid mutations
                    output_score=output_score,
                    output_category=output_category,
                    source=source,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(log_entry)
                db.commit()
            except Exception as e:
                db.rollback()
                logging.getLogger(__name__).warning(f"ML-4: Failed to log prediction: {e}")
            finally:
                db.close()
        except Exception as e:
            # Best-effort: log failure but don't block
            logging.getLogger(__name__).warning(f"ML-4: Prediction logging failed: {e}")

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
        # D6-2: Standardize to 1 decimal place
        return {
            "old_risk_score": round(old_risk, 1),
            "new_risk_score": round(new_risk, 1),
            "delta_new_minus_old": round(new_risk - old_risk, 1),
        }
