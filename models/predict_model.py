"""
Prediction Module v2.0 — Production Grade
==========================================
Loads ensemble model via ModelRegistry singleton, applies the same
preprocessing pipeline used during training, runs inference, computes
feature importance, and returns a structured prediction response.

Response schema
---------------
{
  "student_id":              str,
  "dropout_probability":     float,   # ensemble probability
  "risk_label":              str,     # HIGH / MEDIUM / LOW
  "top_contributing_features": list,  # [{feature, importance}, ...]
  "model_version":           str,
  "prediction_timestamp":    str,
  "fallback_used":           bool,    # True if ML failed and rule-based was used
}
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

MODELS_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = MODELS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from models.feature_engineering import FeatureEngineer, FeatureValidationError, FEATURE_COLS
from models.model_loader import ModelRegistry, ModelVersionMismatch

# Preprocessing import — optional for backward compatibility
try:
    from models.preprocessing import PreprocessingPipeline
    PREPROCESSING_AVAILABLE = True
except ImportError:
    PREPROCESSING_AVAILABLE = False

# SHAP import is optional — fall back gracefully
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not installed. Top features will use feature importances instead.")

# Probability thresholds for risk labels
RISK_THRESHOLDS = {
    "HIGH":   0.65,
    "MEDIUM": 0.40,
    "LOW":    0.0,
}


def _get_risk_label(probability: float) -> str:
    if probability >= RISK_THRESHOLDS["HIGH"]:
        return "HIGH"
    elif probability >= RISK_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def _compute_top_features(
    model,
    X: pd.DataFrame,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    Compute top contributing features using SHAP or feature importances.
    """
    # Try SHAP first
    if SHAP_AVAILABLE:
        try:
            # Check if model supports TreeExplainer
            base_model = model
            if hasattr(model, 'get_model'):
                # For ensemble, get the primary model
                names = model.get_model_names() if hasattr(model, 'get_model_names') else []
                for name in ['xgboost', 'lightgbm', 'random_forest', 'catboost', 'gradient_boosting']:
                    if name in names:
                        base_model = model.get_model(name)
                        break

            explainer = shap.TreeExplainer(base_model)
            shap_values = explainer.shap_values(X)

            if isinstance(shap_values, list):
                sv = shap_values[1][0]
            else:
                sv = shap_values[0]

            feature_shap = [
                {"feature": feat, "importance": float(abs(val)), "shap_value": float(val)}
                for feat, val in zip(FEATURE_COLS, sv)
            ]
            feature_shap.sort(key=lambda x: x["importance"], reverse=True)
            return feature_shap[:top_n]

        except Exception as exc:
            logger.debug(f"SHAP computation failed: {exc} — falling back to feature importances")

    # Fallback: use model feature importances
    imp_source = model
    if hasattr(model, 'feature_importances_') and model.feature_importances_ is not None:
        importances = model.feature_importances_
    elif hasattr(model, '_models'):
        # Try ensemble's aggregated importances
        for m in (model._models.values() if hasattr(model, '_models') else []):
            if hasattr(m, 'feature_importances_'):
                importances = m.feature_importances_
                break
        else:
            return []
    else:
        return []

    feature_imp = [
        {"feature": feat, "importance": float(imp)}
        for feat, imp in zip(FEATURE_COLS, importances)
    ]
    feature_imp.sort(key=lambda x: x["importance"], reverse=True)
    return feature_imp[:top_n]


# ---------------------------------------------------------------------------
# Registry initialisation & caching
# ---------------------------------------------------------------------------

REGISTRY: Optional[ModelRegistry] = None
PREPROCESSING: Optional[Any] = None

# Lightweight runtime stats for monitoring endpoint
RUNTIME_STATS: Dict[str, Any] = {
    "total_predictions": 0,
    "ml_predictions": 0,
    "fallback_predictions": 0,
    "last_prediction_at": None,
}


def _init_registry() -> None:
    """
    Load all models once at process startup and cache in memory.
    """
    global REGISTRY, PREPROCESSING
    try:
        REGISTRY = ModelRegistry.get_instance()
    except ModelVersionMismatch as exc:
        logger.error(f"Model registry feature mismatch: {exc}")
        REGISTRY = None
    except Exception as exc:
        logger.error(f"Failed to initialise ModelRegistry: {exc}")
        REGISTRY = None

    # Load preprocessing pipeline
    if PREPROCESSING_AVAILABLE:
        try:
            PREPROCESSING = PreprocessingPipeline.load()
        except FileNotFoundError:
            logger.warning("No preprocessing pipeline found — predictions will use raw features")
            PREPROCESSING = None
        except Exception as exc:
            logger.warning(f"Failed to load preprocessing pipeline: {exc}")
            PREPROCESSING = None


# Initialise on import (e.g. at server startup)
_init_registry()


def predict(
    student_id: str,
    raw_record: Dict[str, Any],
    top_n_features: int = 5,
) -> Dict[str, Any]:
    """
    Generate a structured dropout risk prediction for one student.

    Parameters
    ----------
    student_id : str
    raw_record : dict
        Raw or canonical-named feature values for this student.
    top_n_features : int
        Number of top contributing features to include in response.

    Returns
    -------
    dict with schema described in module docstring.
    """
    timestamp = datetime.now().isoformat()
    fallback_used = False

    RUNTIME_STATS["total_predictions"] = int(RUNTIME_STATS.get("total_predictions", 0)) + 1
    RUNTIME_STATS["last_prediction_at"] = timestamp

    # ── Step 1: Load models from cached registry ────────────────────────────
    registry = REGISTRY
    if registry is None or not registry.is_loaded():
        logger.warning(
            f"No ML models available in registry for student={student_id} — "
            "using rule-based fallback"
        )
        result = _rule_based_fallback(student_id, raw_record, timestamp)
        RUNTIME_STATS["fallback_predictions"] = int(RUNTIME_STATS.get("fallback_predictions", 0)) + 1
        return result

    # ── Step 2: Feature engineering ────────────────────────────────────────
    try:
        fe = FeatureEngineer(fit=False)
        fe.load_imputation_stats()
        feature_vec = fe.compute(raw_record)
        fe.validate_feature_vector(feature_vec)
        X = fe.to_dataframe([feature_vec])
    except FeatureValidationError as exc:
        logger.error(f"Feature validation failed for student={student_id}: {exc}")
        result = _rule_based_fallback(student_id, raw_record, timestamp, error=str(exc))
        RUNTIME_STATS["fallback_predictions"] = int(RUNTIME_STATS.get("fallback_predictions", 0)) + 1
        return result
    except Exception as exc:
        logger.error(f"Feature engineering failed for student={student_id}: {exc}")
        result = _rule_based_fallback(student_id, raw_record, timestamp, error=str(exc))
        RUNTIME_STATS["fallback_predictions"] = int(RUNTIME_STATS.get("fallback_predictions", 0)) + 1
        return result

    # ── Step 3: Apply preprocessing pipeline ─────────────────────────────
    if PREPROCESSING is not None and PREPROCESSING.is_fitted:
        try:
            X = PREPROCESSING.transform(X)
        except Exception as exc:
            logger.warning(f"Preprocessing transform failed: {exc} — using raw features")

    # ── Step 4: Ensemble probability ───────────────────────────────────────
    probabilities: List[float] = []
    primary_model = None

    # Try ensemble first
    ensemble = registry.get("ensemble")
    if ensemble is not None:
        try:
            prob = float(ensemble.predict_proba(X)[:, 1][0])
            probabilities.append(prob)
            primary_model = ensemble
        except Exception as exc:
            logger.warning(f"Ensemble predict_proba failed: {exc}")

    # Fall back to individual models
    if not probabilities:
        for model_key in ["xgboost", "lightgbm", "catboost", "random_forest", "gradient_boosting"]:
            model = registry.get(model_key)
            if model is None:
                continue
            try:
                prob = float(model.predict_proba(X)[:, 1][0])
                probabilities.append(prob)
                if primary_model is None:
                    primary_model = model
            except Exception as exc:
                logger.warning(f"Model '{model_key}' predict_proba failed: {exc}")

    if not probabilities:
        logger.error(f"All models failed for student={student_id} — using rule-based fallback")
        result = _rule_based_fallback(student_id, raw_record, timestamp)
        RUNTIME_STATS["fallback_predictions"] = int(RUNTIME_STATS.get("fallback_predictions", 0)) + 1
        return result

    ensemble_probability = float(np.mean(probabilities))
    risk_label = _get_risk_label(ensemble_probability)

    # ── Step 5: Feature importance ─────────────────────────────────────────
    top_features: List[Dict] = []
    if primary_model is not None:
        top_features = _compute_top_features(primary_model, X, top_n=top_n_features)

    # ── Step 6: Build response ────────────────────────────────────────────
    response = {
        "student_id":                  student_id,
        "dropout_probability":         round(ensemble_probability, 4),
        "risk_label":                  risk_label,
        "top_contributing_features":   top_features,
        "model_version":               registry.get_model_version(),
        "prediction_timestamp":        timestamp,
        "fallback_used":               fallback_used,
        "individual_model_probabilities": {
            "ensemble": round(probabilities[0], 4) if len(probabilities) > 0 else None,
        },
    }

    logger.info(
        f"Prediction: student={student_id} | p={ensemble_probability:.3f} | risk={risk_label} "
        f"| v={registry.get_model_version()}"
    )
    RUNTIME_STATS["ml_predictions"] = int(RUNTIME_STATS.get("ml_predictions", 0)) + 1
    return response


def predict_batch(
    records: List[Dict[str, Any]],
    top_n_features: int = 3,
) -> List[Dict[str, Any]]:
    """
    Predict for multiple students in one call.
    Returns a list of prediction dicts in the same order as input.
    """
    results = []
    for record in records:
        sid = record.get("student_id", "unknown")
        result = predict(sid, record, top_n_features=top_n_features)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Rule-based fallback
# ---------------------------------------------------------------------------

def _rule_based_fallback(
    student_id: str,
    raw_record: Dict[str, Any],
    timestamp: str,
    error: str = "",
) -> Dict[str, Any]:
    """
    Simple rule-based risk estimate when ML models are unavailable.
    """
    att   = _safe_float(raw_record.get("attendance_rate", None), default=50.0)
    quiz  = _safe_float(raw_record.get("avg_quiz_score", None), default=50.0)
    logins = _safe_float(raw_record.get("num_logins", None), default=10.0)

    risk_score = 0.0
    if att < 50:    risk_score += 0.40
    elif att < 70:  risk_score += 0.20
    if quiz < 40:   risk_score += 0.35
    elif quiz < 60: risk_score += 0.15
    if logins < 5:  risk_score += 0.25

    risk_score = min(1.0, risk_score)
    risk_label = _get_risk_label(risk_score)

    logger.warning(
        f"Rule-based fallback for student={student_id}, score={risk_score:.2f}" +
        (f", reason={error}" if error else "")
    )

    return {
        "student_id":                  student_id,
        "dropout_probability":         round(risk_score, 4),
        "risk_label":                  risk_label,
        "top_contributing_features":   [],
        "model_version":               "rule-based-fallback",
        "prediction_timestamp":        timestamp,
        "fallback_used":               True,
        "fallback_reason":             error or "ML models not loaded",
    }


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        v = float(value)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# CLI usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(description="Predict dropout risk for a student")
    parser.add_argument("student_id", help="Student email/ID")
    parser.add_argument("--attendance",   type=float, default=75.0)
    parser.add_argument("--quiz_score",   type=float, default=60.0)
    parser.add_argument("--logins",       type=float, default=20.0)
    args = parser.parse_args()

    raw = {
        "attendance_rate": args.attendance,
        "avg_quiz_score":  args.quiz_score,
        "num_logins":      args.logins,
    }
    result = predict(args.student_id, raw)
    print(json.dumps(result, indent=2))
