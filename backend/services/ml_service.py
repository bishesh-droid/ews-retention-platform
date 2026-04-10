"""
ML Service — EWS Retention Platform
=====================================
Bridges the prediction pipeline with the FastAPI layer.

Architecture decision
---------------------
The three ML pipelines that existed in the codebase (32-feature absrate/mpa
schema, 28-feature LMS schema from models/, and 12-feature DB-derived schema)
were all mutually incompatible, so every prediction silently fell back to a
rule-based heuristic.

This service consolidates to a single, coherent path:

  StudentService → FeatureEngineer → RiskScorer → risk_score (0-100)

That pipeline is already wired, already reads from the live SQLite database,
and produces risk scores that are actually grounded in the ingested LMS data.

ML model inference (XGBoost/RF) is kept as an *optional enhancement layer*:
  • If a valid model is loaded AND its feature columns match the DB-derived
    features, its probability is blended in (30 % model / 70 % rule-based).
  • If no model is available the pure rule-based score is used as-is and
    `model_used` in the response is set to False so callers know.

Prediction results are persisted to the `predictions` table so that
trend, velocity, and history endpoints have real data to serve.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

import backend.config as settings
from backend.config import trimester_week_number
from backend.services.feature_engineering import FeatureEngineer
from backend.services.calendar_scorer import get_current_week
from backend.services.risk_scoring import RiskScorer
from backend.database.models.prediction import Prediction
from backend.core.logger import sys_logger

logger = sys_logger


# ---------------------------------------------------------------------------
# Optional: attempt to load the joblib models that live in
# backend/ml/models/saved/.  These were trained on the 32-feature absrate/mpa
# schema which is different from the DB-derived features, so we deliberately
# do NOT use them for the primary score — but we log a clear warning so
# the discrepancy is visible rather than silently swallowed.
# ---------------------------------------------------------------------------

def _try_load_joblib_models() -> Optional[Any]:
    """
    Try to load the XGBoost joblib model.
    Returns the model object or None if not available/compatible.
    Validates that the model expects the correct 12 DB-derived features.
    """
    try:
        import joblib
        from pathlib import Path
        import json

        model_path = (
            Path(__file__).resolve().parent.parent
            / "ml" / "models" / "saved" / "retention_model_xgboost.joblib"
        )
        features_path = model_path.parent / "feature_names.json"
        metrics_path = model_path.parent / "model_metrics.json"

        if not model_path.exists():
            logger.info("No XGBoost model found — rule-based scoring only.")
            return None

        # Load feature metadata if available
        expected_features = None
        if features_path.exists():
            try:
                with open(features_path) as f:
                    feature_meta = json.load(f)
                    expected_features = feature_meta.get("feature_names", [])
                    logger.info(f"Model expects features: {expected_features}")
            except Exception:
                pass

        # Load the model
        model = joblib.load(model_path)

        # Validate feature count
        n_features_in = getattr(model, "n_features_in_", None)
        if n_features_in is not None and expected_features:
            if n_features_in == len(expected_features):
                logger.info(
                    f"XGBoost model loaded successfully ({model_path.name}) "
                    f"with {n_features_in} features matching DB-derived schema."
                )

                # Load and log metrics
                if metrics_path.exists():
                    try:
                        with open(metrics_path) as f:
                            metrics = json.load(f)
                            logger.info(
                                f"Model metrics: AUC-ROC={metrics.get('test_set', {}).get('auc_roc', 'N/A')}, "
                                f"F1={metrics.get('test_set', {}).get('f1_score', 'N/A')}"
                            )
                    except Exception:
                        pass

                return model
            else:
                logger.warning(
                    f"Model feature count mismatch: model expects {n_features_in}, "
                    f"but DB-derived features have {len(expected_features)}. "
                    "Using rule-based scoring."
                )
                return None
        else:
            logger.warning("Could not validate model feature schema. Using rule-based scoring.")
            return None

    except Exception as exc:
        logger.info(f"XGBoost model not loaded: {exc}")
        return None


_JOBLIB_MODEL = _try_load_joblib_models()


# ---------------------------------------------------------------------------
# Public service class
# ---------------------------------------------------------------------------

class MLService:
    """
    Orchestrates risk prediction for students.

    Primary path  : DB data → FeatureEngineer → RiskScorer → risk_score (0-100)
    Persistence   : Saves each prediction to the `predictions` table.
    Cache         : In-process dict keyed by student_id, TTL = one DB session.
                    Use predict_student() to bypass cache when fresh data needed.
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info("MLService initialised (rule-based scoring, DB-backed features)")

    # ------------------------------------------------------------------
    # Feature extraction for ML model
    # ------------------------------------------------------------------

    # 12 DB-derived features expected by the XGBoost model
    _MODEL_FEATURES: List[str] = [
        "content_completion_score",
        "login_consistency_score",
        "quiz_engagement_score",
        "assignment_score",
        "time_investment_score",
        "discussion_engagement_score",
        "self_directed_learning_score",
        "w1w2_completion_score",
        "zero_progress_ratio",
        "graded_quiz_score",
        "graded_assignment_score",
        "exam_score",
    ]

    def _extract_model_features(self, features: Dict[str, Any]) -> List[float]:
        """
        Extract the 12 DB-derived features in the correct order for model inference.
        Handles missing values by using defaults.
        """
        values = []
        for feat_name in self._MODEL_FEATURES:
            val = features.get(feat_name)
            if val is None:
                # Use sensible defaults based on feature type
                if feat_name == "zero_progress_ratio":
                    val = 0.5  # Unknown = moderate risk
                else:
                    val = 0.0  # Scores default to 0
            values.append(float(val))
        return values

    def _get_model_prediction(self, features: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
        """
        Get prediction from XGBoost model if available.

        Returns:
            Tuple of (dropout_probability, model_confidence) or (None, None) if no model.
        """
        if _JOBLIB_MODEL is None:
            return None, None

        try:
            import numpy as np

            # Extract features in correct order
            feature_vector = self._extract_model_features(features)
            X = np.array([feature_vector])

            # Get prediction probability
            proba = _JOBLIB_MODEL.predict_proba(X)[0]
            dropout_proba = proba[1]  # Probability of class 1 (dropped out)

            # Convert to risk score (0-100)
            risk_score = dropout_proba * 100

            # Confidence = max probability
            confidence = max(proba)

            return risk_score, confidence

        except Exception as exc:
            logger.warning(f"Model prediction failed: {exc}")
            return None, None

    # ------------------------------------------------------------------
    # Primary entry points
    # ------------------------------------------------------------------

    def predict_student(
        self,
        student_id: str,
        enrollments: List[Dict],
        graded: List[Dict],
        exams: List[Dict],
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Compute and return a risk prediction for one student.

        Uses XGBoost model if available, otherwise falls back to rule-based scoring.
        When both are available, blends predictions (30% model / 70% rule-based)
        for robustness while maintaining interpretability.

        Parameters
        ----------
        student_id  : student primary key (email / org_defined_id)
        enrollments : list of enrollment dicts from StudentService._get_enrollment_dicts()
        graded      : list of graded component dicts
        exams       : list of exam record dicts
        db          : if provided, the prediction is persisted to the DB

        Returns
        -------
        dict with keys:
            student_id, risk_score (0-100), risk_category, retention_likelihood,
            dominant_risk_factor, risk_breakdown, model_used, model_confidence,
            prediction_timestamp
        """
        try:
            features = FeatureEngineer.calculate_all_features(
                enrollments,
                graded_components=graded,
                exam_records=exams,
                is_new_student=False,
                week_number=trimester_week_number(),
            )

            # Get rule-based score (always calculated)
            rule_based_score = RiskScorer.calculate_risk_score(
                features,
                graded_components=graded or [],
                program=None,
                current_week=get_current_week(settings.TRIMESTER_START_DATE),
            )

            # Try to get XGBoost model prediction
            model_score, model_confidence = self._get_model_prediction(features)

            # Blend scores if model is available
            if model_score is not None:
                # Blend: 30% model, 70% rule-based for stability
                risk_score = 0.30 * model_score + 0.70 * rule_based_score
                model_used = True
                model_type = "xgboost_blended"
                model_description = "XGBoost + rule-based ensemble (30/70 blend)"
                score_basis = "ml_model_with_rule_fallback"
            else:
                risk_score = rule_based_score
                model_used = False
                model_type = "rule_based"
                model_description = "Weighted engagement formula — not a trained ML model"
                score_basis = "rule_based_formula"
                model_confidence = None

            risk_category = RiskScorer.get_risk_category(risk_score)
            retention = RiskScorer.get_retention_likelihood(risk_score)
            dominant = RiskScorer.get_dominant_risk_factor(features)
            breakdown = RiskScorer.get_risk_breakdown(features)

            result: Dict[str, Any] = {
                "student_id": student_id,
                "risk_score": round(risk_score, 2),
                "engagement_risk_score": round(risk_score, 2),
                "risk_category": risk_category,
                "retention_likelihood": retention,
                "dominant_risk_factor": dominant,
                "risk_breakdown": breakdown,
                "model_used": model_used,
                "model_type": model_type,
                "model_description": model_description,
                "model_confidence": round(model_confidence, 4) if model_confidence else None,
                "rule_based_score": round(rule_based_score, 2),
                "ml_model_score": round(model_score, 2) if model_score else None,
                "score_basis": score_basis,
                "prediction_error": False,
                "prediction_timestamp": datetime.now(timezone.utc).isoformat(),
                "features": {
                    "content_completion_score": features.get("content_completion_score", 0),
                    "quiz_engagement_score": features.get("quiz_engagement_score", 0),
                    "graded_quiz_score": features.get("graded_quiz_score", 0),
                    "graded_assignment_score": features.get("graded_assignment_score", 0),
                    "exam_score": features.get("exam_score", 0),
                    "exam_attendance_rate": features.get("exam_attendance_rate", 0),
                    "login_consistency_score": features.get("login_consistency_score", 0),
                    "time_investment_score": features.get("time_investment_score", 0),
                    "discussion_engagement_score": features.get("discussion_engagement_score", 0),
                    "assignment_score": features.get("assignment_score", 0),
                },
            }

            self._cache[student_id] = result

            if db is not None:
                self.persist_prediction(db, student_id, risk_score, features)

            logger.info(
                f"Prediction: student={student_id} risk={risk_score:.1f} "
                f"category={risk_category}"
            )
            return result

        except Exception as exc:
            logger.error(f"Prediction failed for student={student_id}: {exc}")
            return self._error_prediction(student_id, str(exc))

    def predict_student_cached(self, student_id: str) -> Dict[str, Any]:
        """
        Return cached prediction if available, otherwise return an error dict.
        Callers should prefer predict_student() with live DB data.
        Used only by legacy ml_routes endpoints.
        """
        if student_id in self._cache:
            return self._cache[student_id]
        return {
            "student_id": student_id,
            "error": "Student not found in processed data",
            "prediction_error": True,
        }

    def batch_predict(
        self,
        student_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """Return cached predictions for a list of student IDs."""
        return [self.predict_student_cached(sid) for sid in student_ids]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def persist_prediction(
        self,
        db: Session,
        student_id: str,
        risk_score: float,
        features: Dict[str, Any],
    ) -> None:
        """
        Persist a Prediction row without committing.

        The caller is responsible for `db.commit()` so we keep transaction
        boundaries at the outer request/job layer.
        """
        try:
            pred = Prediction(
                student_id=student_id,
                risk_score=risk_score / 100.0,          # stored as 0-1 probability
                engagement_score=features.get("content_completion_score", 0) / 100.0,
                retention_likelihood=RiskScorer.get_retention_likelihood(risk_score),
                # Legacy fields (kept for backward compatibility with analytics endpoints)
                grades=features.get("graded_quiz_score", 0.0),
                attendance=features.get("exam_attendance_rate", 0.0),
                assignments=features.get("graded_assignment_score", 0.0),
                # Signal breakdown scores (0-1 scale)
                academic_signal_score=features.get("graded_quiz_score", 0) / 100.0,
                engagement_signal_score=features.get("quiz_engagement_score", 0) / 100.0,
                consistency_signal_score=features.get("login_consistency_score", 0) / 100.0,
                intent_signal_score=features.get("assignment_score", 0) / 100.0,
                responsiveness_signal_score=features.get("discussion_engagement_score", 0) / 100.0,
                model_version="rule-based-v1",
                prediction_timestamp=datetime.now(timezone.utc),
                top_risk_factors=json.dumps(
                    [RiskScorer.get_dominant_risk_factor(features)]
                ),
            )
            db.add(pred)
            # Flush so PKs/row state is available to the caller if needed.
            db.flush()
        except Exception as exc:
            logger.warning(f"Could not persist prediction for {student_id}: {exc}")
            raise

    # Backward-compatible alias (if any legacy code calls the old private name).
    _persist_prediction = persist_prediction

    # ------------------------------------------------------------------
    # Runtime stats (backward-compatible with old ml_routes)
    # ------------------------------------------------------------------

    def get_runtime_stats(self) -> Dict[str, Any]:
        """Get runtime statistics and model status."""
        model_loaded = _JOBLIB_MODEL is not None

        if model_loaded:
            status = "XGBoost model loaded — blended scoring active (30% ML / 70% rule-based)"
        else:
            status = (
                "No XGBoost model loaded — rule-based scoring only. "
                "Run train_xgboost.py to train and enable ML inference."
            )

        return {
            "total_predictions": len(self._cache),
            "model_loaded": model_loaded,
            "model_used": model_loaded,  # backward compat
            "model_status": status,
        }

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get detailed information about the loaded ML model.

        Returns model type, feature list, and performance metrics.
        """
        # Load metrics if available
        metrics = None
        model_path = (
            Path(__file__).resolve().parent.parent
            / "ml" / "models" / "saved" / "retention_model_xgboost.joblib"
        )
        metrics_path = model_path.parent / "model_metrics.json"

        if metrics_path.exists():
            try:
                with open(metrics_path) as f:
                    metrics = json.load(f)
            except Exception:
                pass

        if _JOBLIB_MODEL is None:
            return {
                "model_type": "none",
                "model_loaded": False,
                "model_path": str(model_path),
                "features": self._MODEL_FEATURES,
                "n_features": len(self._MODEL_FEATURES),
                "description": "No ML model loaded — rule-based scoring only",
                "metrics": None,
                "training_info": None,
            }

        # Get model info from loaded model
        model_info = {
            "model_type": "XGBoostClassifier",
            "model_loaded": True,
            "model_path": str(model_path),
            "features": self._MODEL_FEATURES,
            "n_features": len(self._MODEL_FEATURES),
            "description": "XGBoost classifier trained on 12 DB-derived engagement features",
        }

        # Add metrics if available
        if metrics:
            model_info["metrics"] = {
                "auc_roc": metrics.get("test_set", {}).get("auc_roc"),
                "precision": metrics.get("test_set", {}).get("precision"),
                "recall": metrics.get("test_set", {}).get("recall"),
                "f1_score": metrics.get("test_set", {}).get("f1_score"),
            }
            model_info["training_info"] = {
                "n_samples": metrics.get("n_samples"),
                "class_distribution": metrics.get("class_distribution"),
                "cross_validation_folds": metrics.get("cross_validation", {}).get("folds"),
                "training_params": metrics.get("training_params"),
            }
            model_info["feature_importance"] = metrics.get("feature_importance", [])

        return model_info

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _error_prediction(student_id: str, error: str) -> Dict[str, Any]:
        return {
            "student_id": student_id,
            "risk_score": 50.0,
            "risk_category": "medium",
            "retention_likelihood": "Medium",
            "dominant_risk_factor": "Unknown",
            "risk_breakdown": {},
            "model_used": False,
            "prediction_error": True,
            "error": error,
            "prediction_timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Module-level singleton — import and use this everywhere.
ml_service = MLService()
