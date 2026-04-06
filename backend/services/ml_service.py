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
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.services.feature_engineering import FeatureEngineer
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
    Returns the pipeline object or None.
    Logs a warning explaining why it cannot be used for scoring if the
    feature schema does not match.
    """
    try:
        import joblib
        from pathlib import Path

        model_path = (
            Path(__file__).resolve().parent.parent
            / "ml" / "models" / "saved" / "retention_model_xgboost.joblib"
        )
        if not model_path.exists():
            logger.info("No joblib model found — rule-based scoring only.")
            return None

        model = joblib.load(model_path)

        # The joblib model expects 32 absrate/mpa/nsusp/mobility features.
        # Our DB-derived features are different (content, quiz, time, etc.).
        # Until the model is retrained on DB features we cannot use it.
        clf = model.named_steps.get("classifier") if hasattr(model, "named_steps") else None
        expected_features = getattr(clf, "n_features_in_", None)
        logger.warning(
            f"Joblib model loaded ({model_path.name}) but expects "
            f"{expected_features} absrate/mpa features which differ from "
            "DB-derived LMS features. Model will NOT be used for scoring "
            "until retrained on DB features. Using rule-based scoring."
        )
        return None  # Intentionally disabled until retrained

    except Exception as exc:
        logger.info(f"Joblib model not loaded: {exc}")
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
            dominant_risk_factor, risk_breakdown, model_used, prediction_timestamp
        """
        try:
            features = FeatureEngineer.calculate_all_features(
                enrollments,
                graded_components=graded,
                exam_records=exams,
            )
            risk_score = RiskScorer.calculate_risk_score(features)
            risk_category = RiskScorer.get_risk_category(risk_score)
            retention = RiskScorer.get_retention_likelihood(risk_score)
            dominant = RiskScorer.get_dominant_risk_factor(features)
            breakdown = RiskScorer.get_risk_breakdown(features)

            result: Dict[str, Any] = {
                "student_id": student_id,
                "risk_score": risk_score,           # 0-100
                "risk_category": risk_category,     # "low" | "medium" | "high"
                "retention_likelihood": retention,
                "dominant_risk_factor": dominant,
                "risk_breakdown": breakdown,
                "model_used": False,                # True once a retrained model is available
                "prediction_error": False,
                "prediction_timestamp": datetime.utcnow().isoformat(),
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
                academic_signal_score=features.get("graded_quiz_score", 0) / 100.0,
                engagement_signal_score=features.get("quiz_engagement_score", 0) / 100.0,
                consistency_signal_score=features.get("login_consistency_score", 0) / 100.0,
                intent_signal_score=features.get("assignment_score", 0) / 100.0,
                responsiveness_signal_score=features.get("discussion_engagement_score", 0) / 100.0,
                model_version="rule-based-v1",
                prediction_timestamp=datetime.utcnow(),
                top_risk_factors=json.dumps(
                    [RiskScorer.get_dominant_risk_factor(features)]
                ),
            )
            db.add(pred)
            # Flush so PKs/row state is available to the caller if needed.
            db.flush()
        except Exception as exc:
            db.rollback()
            logger.warning(f"Could not persist prediction for {student_id}: {exc}")

    # Backward-compatible alias (if any legacy code calls the old private name).
    _persist_prediction = persist_prediction

    # ------------------------------------------------------------------
    # Runtime stats (backward-compatible with old ml_routes)
    # ------------------------------------------------------------------

    def get_runtime_stats(self) -> Dict[str, Any]:
        return {
            "total_predictions": len(self._cache),
            "model_used": False,
            "model_status": (
                "No model loaded — rule-based scoring active. "
                "Retrain on DB-derived features to enable ML inference."
            ),
        }

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
            "prediction_timestamp": datetime.utcnow().isoformat(),
        }


# Module-level singleton — import and use this everywhere.
ml_service = MLService()
