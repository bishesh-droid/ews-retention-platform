"""
Model Training Pipeline — Production Grade
Time-aware split (T1 → Train, T2 → Test), SMOTE, cross-validation,
versioned model serialisation with full metadata.

Usage
-----
    python models/train_model.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold, cross_validate
from xgboost import XGBClassifier

try:
    from imblearn.over_sampling import SMOTE
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False
    logging.warning("imbalanced-learn not installed. SMOTE will be skipped.")

# ── Path setup ───────────────────────────────────────────────────────────
MODELS_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = MODELS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.feature_engineering import (
    FeatureEngineer,
    FEATURE_COLS,
    load_master_dataset,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SAVED_MODELS_DIR = MODELS_DIR / "saved_models"
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
MODEL_VERSION = "v1.0"  # Bump this when retraining


# ── SMOTE helper ──────────────────────────────────────────────────────────────

def _apply_smote(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> tuple[pd.DataFrame, pd.Series]:
    if not SMOTE_AVAILABLE:
        return X_train, y_train
    if y_train.nunique() < 2:
        logger.warning("SMOTE skipped: only one class in training data.")
        return X_train, y_train

    minority_count = y_train.value_counts().min()
    k_neighbors = min(5, minority_count - 1)
    if k_neighbors < 1:
        logger.warning(
            f"SMOTE skipped: minority class has only {minority_count} samples — need ≥2."
        )
        return X_train, y_train

    try:
        smote = SMOTE(random_state=RANDOM_STATE, k_neighbors=k_neighbors)
        X_res, y_res = smote.fit_resample(X_train, y_train)
        logger.info(
            f"SMOTE: {len(X_train)} → {len(X_res)} samples "
            f"(minority: {minority_count} → {y_res.sum()})"
        )
        return pd.DataFrame(X_res, columns=FEATURE_COLS), pd.Series(y_res, name="is_dropout")
    except Exception as exc:
        logger.warning(f"SMOTE failed ({exc}) — using original training data.")
        return X_train, y_train


# ── Evaluation helper ────────────────────────────────────────────────────────────

def _evaluate(model, X_test: pd.DataFrame, y_test: pd.Series, model_name: str) -> dict:
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    metrics = {}
    if y_test.nunique() > 1:
        metrics["auc_roc"]   = float(roc_auc_score(y_test, y_prob))
    else:
        metrics["auc_roc"]   = None
        logger.warning(f"{model_name}: only one class in test set, AUC-ROC is undefined.")

    metrics["f1_score"]   = float(f1_score(y_test, y_pred, zero_division=0))
    metrics["precision"]  = float(precision_score(y_test, y_pred, zero_division=0))
    metrics["recall"]     = float(recall_score(y_test, y_pred, zero_division=0))
    metrics["cm"]         = confusion_matrix(y_test, y_pred).tolist()

    logger.info(f"{model_name} — AUC={metrics['auc_roc']}, F1={metrics['f1_score']:.3f}")
    print(f"\n{model_name} Classification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))
    return metrics


# ── Cross-validation helper ───────────────────────────────────────────────────────

def _cross_validate(model, X: pd.DataFrame, y: pd.Series, model_name: str) -> dict:
    if y.nunique() < 2 or len(X) < 10:
        logger.warning(f"{model_name}: skipping CV (insufficient data: {len(X)} rows)")
        return {}

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_validate(
        model, X, y, cv=cv,
        scoring=["roc_auc", "f1", "precision", "recall"],
        return_train_score=False,
    )
    summary = {
        "cv_auc_mean":       float(np.mean(scores["test_roc_auc"])),
        "cv_auc_std":        float(np.std(scores["test_roc_auc"])),
        "cv_f1_mean":        float(np.mean(scores["test_f1"])),
        "cv_precision_mean": float(np.mean(scores["test_precision"])),
        "cv_recall_mean":    float(np.mean(scores["test_recall"])),
    }
    logger.info(
        f"{model_name} 5-Fold CV — AUC={summary['cv_auc_mean']:.3f}±{summary['cv_auc_std']:.3f}, "
        f"F1={summary['cv_f1_mean']:.3f}"
    )
    return summary


# ── Model saver ──────────────────────────────────────────────────────────────────

def _save_model(model, model_key: str, metrics: dict, cv_metrics: dict) -> Path:
    filename = f"{model_key}_{MODEL_VERSION}.pkl"
    path = SAVED_MODELS_DIR / filename
    joblib.dump(model, path)
    logger.info(f"Model saved → {path}")

    # Save per-model metrics alongside pkl
    metrics_path = SAVED_MODELS_DIR / f"{model_key}_{MODEL_VERSION}_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump({"test_metrics": metrics, "cv_metrics": cv_metrics}, f, indent=2)

    return path


# ── Main training entry point ─────────────────────────────────────────────────────

def train_models():
    logger.info("=" * 70)
    logger.info("EWS Model Training Pipeline")
    logger.info(f"  version  : {MODEL_VERSION}")
    logger.info(f"  date     : {datetime.now().isoformat()}")
    logger.info(f"  features : {len(FEATURE_COLS)}")
    logger.info("=" * 70)

    # 1. Load master dataset ─────────────────────────────────────────────
    master_df = load_master_dataset()
    if master_df.empty:
        logger.error(
            "No master dataset found. Run data_ingestion.master_builder first: "
            "  python -m data_ingestion.master_builder"
        )
        return

    logger.info(f"Master dataset loaded: {master_df.shape}")
    if "trimester" in master_df.columns:
        logger.info(f"Trimester distribution:\n{master_df['trimester'].value_counts().to_dict()}")

    # 2. Feature engineering (time-aware split) ─────────────────────
    #    - T1: training set (used to learn imputations + target)
    #    - T2: validation set (uses T1 imputations ONLY to prevent leakage)
    train_fe = FeatureEngineer(fit=True)
    X_train, y_train = train_fe.fit_transform(master_df, trimester_filter="T1")

    # Save imputation stats from training set (T1 medians only)
    train_fe.save_imputation_stats()

    # Build T2 test set using the SAME imputation medians learned from T1.
    # We MUST NOT refit imputation medians on T2, otherwise we leak future info.
    t2_df = master_df[master_df.get("trimester") == "T2"].copy()

    test_fe = FeatureEngineer(fit=False)
    test_fe._imputation_medians = dict(train_fe._imputation_medians)  # anti-leakage: T1 medians
    X_test = test_fe.transform(t2_df)
    y_test = train_fe._build_target(t2_df)

    if X_train.empty:
        logger.error("Training set empty (T1). Check that clean_master_dataset.csv has T1 rows.")
        return

    if X_test.empty:
        logger.warning(
            "Test set empty (T2). Falling back to 20% random split from T1 for evaluation only."
        )
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X_train, y_train, test_size=0.2, random_state=RANDOM_STATE, stratify=y_train if y_train.nunique() > 1 else None
        )

    logger.info(f"Train: X={X_train.shape}, y distribution={y_train.value_counts().to_dict()}")
    logger.info(f"Test:  X={X_test.shape},  y distribution={y_test.value_counts().to_dict()}")

    # 3. SMOTE on training data only (NEVER on test) ──────────────────
    X_train_res, y_train_res = _apply_smote(X_train, y_train)

    # 4. Train RandomForest ─────────────────────────────────────────────
    logger.info("Training RandomForest...")
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=3,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    rf.fit(X_train_res, y_train_res)
    rf_cv   = _cross_validate(rf, X_train, y_train, "RandomForest")
    rf_test = _evaluate(rf, X_test, y_test, "RandomForest")
    rf_path = _save_model(rf, "random_forest", rf_test, rf_cv)

    # 5. Train XGBoost ───────────────────────────────────────────────
    logger.info("Training XGBoost...")
    xgb = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        scale_pos_weight=(
            len(y_train_res[y_train_res == 0]) / max(len(y_train_res[y_train_res == 1]), 1)
        ),
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    xgb.fit(X_train_res, y_train_res)
    xgb_cv   = _cross_validate(xgb, X_train, y_train, "XGBoost")
    xgb_test = _evaluate(xgb, X_test, y_test, "XGBoost")
    xgb_path = _save_model(xgb, "xgboost", xgb_test, xgb_cv)

    # 6. Save shared model metadata ───────────────────────────────────
    metadata = {
        "model_version":      MODEL_VERSION,
        "training_date":      datetime.now().isoformat(),
        "training_trimester": "T1",
        "test_trimester":     "T2",
        "feature_list":       FEATURE_COLS,
        "n_features":         len(FEATURE_COLS),
        "n_train_samples":    len(X_train_res),
        "n_test_samples":     len(X_test),
        "random_state":       RANDOM_STATE,
        "smote_applied":      SMOTE_AVAILABLE,
        "models": {
            "random_forest": {
                "path":       str(rf_path),
                "test_metrics": rf_test,
                "cv_metrics":   rf_cv,
            },
            "xgboost": {
                "path":       str(xgb_path),
                "test_metrics": xgb_test,
                "cv_metrics":   xgb_cv,
            },
        },
    }

    metadata_path = SAVED_MODELS_DIR / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    logger.info(f"Metadata saved → {metadata_path}")
    logger.info("Training pipeline complete.")
    logger.info(f"  RF  AUC: {rf_test.get('auc_roc')}")
    logger.info(f"  XGB AUC: {xgb_test.get('auc_roc')}")


if __name__ == "__main__":
    train_models()
