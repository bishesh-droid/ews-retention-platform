"""
Model Training Pipeline v2.0 — Production Grade
=================================================
Structured pipeline with 10 stages:
  1. Data ingestion
  2. Feature engineering (28 features)
  3. Time-aware train/test split
  4. Preprocessing (impute → clamp → scale)
  5. Class balancing (SMOTE-Tomek)
  6. Hyperparameter tuning (Optuna)
  7. Multi-model training (6 models)
  8. Comprehensive evaluation
  9. Ensemble creation (weighted voting)
  10. Model export & metadata

Usage
-----
    python models/train_model.py
    python models/train_model.py --skip-tuning   # use defaults, faster
    python models/train_model.py --trials 20      # fewer Optuna trials
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# ── Path setup ───────────────────────────────────────────────────────────
MODELS_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = MODELS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.feature_engineering import (
    FeatureEngineer,
    FEATURE_COLS,
    load_master_dataset,
)
from models.preprocessing import PreprocessingPipeline
from models.model_zoo import ModelZoo
from models.ensemble import WeightedVotingEnsemble
from models.evaluation import ModelEvaluator

# Optional imports — degrade gracefully
try:
    from models.hyperparameter_tuning import HyperparameterTuner
    TUNER_AVAILABLE = True
except ImportError:
    TUNER_AVAILABLE = False

try:
    from imblearn.combine import SMOTETomek
    from imblearn.over_sampling import SMOTE
    IMBALANCE_AVAILABLE = True
except ImportError:
    IMBALANCE_AVAILABLE = False


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

SAVED_MODELS_DIR = MODELS_DIR / "saved_models"
SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
MODEL_VERSION = "v2.0"


# ══════════════════════════════════════════════════════════════════════════
# Stage 1: Data Ingestion
# ══════════════════════════════════════════════════════════════════════════

def stage_data_ingestion() -> pd.DataFrame:
    """Load the clean master dataset."""
    logger.info("━" * 60)
    logger.info("STAGE 1: Data Ingestion")
    logger.info("━" * 60)

    master_df = load_master_dataset()
    if master_df.empty:
        raise RuntimeError(
            "No master dataset found. Run data_ingestion.master_builder first: "
            "  python -m data_ingestion.master_builder"
        )

    logger.info(f"  Loaded: {master_df.shape[0]} rows × {master_df.shape[1]} columns")
    if "trimester" in master_df.columns:
        logger.info(f"  Trimesters: {master_df['trimester'].value_counts().to_dict()}")
    return master_df


# ══════════════════════════════════════════════════════════════════════════
# Stage 2: Feature Engineering
# ══════════════════════════════════════════════════════════════════════════

def stage_feature_engineering(
    master_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, FeatureEngineer]:
    """
    Compute features and split into train/test using time-aware split.
    T1 → training, T2 → testing.
    """
    logger.info("━" * 60)
    logger.info("STAGE 2: Feature Engineering & Train/Test Split")
    logger.info("━" * 60)

    # Fit on T1 (training)
    train_fe = FeatureEngineer(fit=True)
    X_train, y_train = train_fe.fit_transform(master_df, trimester_filter="T1")
    train_fe.save_imputation_stats()

    # Transform T2 (test) using T1 imputation medians — prevents leakage
    t2_df = master_df[master_df.get("trimester") == "T2"].copy()
    test_fe = FeatureEngineer(fit=False)
    test_fe._imputation_medians = dict(train_fe._imputation_medians)
    X_test = test_fe.transform(t2_df)
    y_test = train_fe._build_target(t2_df)

    if X_train.empty:
        raise RuntimeError("Training set empty (T1). Check clean_master_dataset.csv has T1 rows.")

    if X_test.empty:
        logger.warning("Test set empty (T2). Falling back to 20% random split from T1.")
        X_train, X_test, y_train, y_test = train_test_split(
            X_train, y_train, test_size=0.2,
            random_state=RANDOM_STATE,
            stratify=y_train if y_train.nunique() > 1 else None,
        )

    logger.info(f"  Train: {X_train.shape}, y={y_train.value_counts().to_dict()}")
    logger.info(f"  Test:  {X_test.shape}, y={y_test.value_counts().to_dict()}")
    logger.info(f"  Features ({len(FEATURE_COLS)}): {FEATURE_COLS[:5]}... (see feature_list.json)")

    return X_train, y_train, X_test, y_test, train_fe


# ══════════════════════════════════════════════════════════════════════════
# Stage 3: Preprocessing
# ══════════════════════════════════════════════════════════════════════════

def stage_preprocessing(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, PreprocessingPipeline]:
    """Apply sklearn preprocessing pipeline (impute → clamp outliers → scale)."""
    logger.info("━" * 60)
    logger.info("STAGE 3: Preprocessing (Impute → Clamp → Scale)")
    logger.info("━" * 60)

    pp = PreprocessingPipeline(outlier_factor=1.5)
    X_train_pp = pp.fit_transform(X_train)
    X_test_pp = pp.transform(X_test)
    pp.save()

    stats = pp.get_stats()
    logger.info(f"  Duplicates removed: {stats.get('n_duplicates_removed', 0)}")
    logger.info(f"  Outlier clamping: IQR × 1.5")
    logger.info(f"  Scaling: StandardScaler (z-score)")

    return X_train_pp, X_test_pp, pp


# ══════════════════════════════════════════════════════════════════════════
# Stage 4: Class Balancing
# ══════════════════════════════════════════════════════════════════════════

def stage_class_balancing(
    X_train: pd.DataFrame,
    y_train: pd.Series,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Apply SMOTE-Tomek to address class imbalance."""
    logger.info("━" * 60)
    logger.info("STAGE 4: Class Balancing (SMOTE-Tomek)")
    logger.info("━" * 60)

    if not IMBALANCE_AVAILABLE:
        logger.warning("  imbalanced-learn not installed — skipping resampling")
        return X_train, y_train

    if y_train.nunique() < 2:
        logger.warning("  Only one class — skipping SMOTE")
        return X_train, y_train

    minority_count = y_train.value_counts().min()
    k_neighbors = min(5, minority_count - 1)
    if k_neighbors < 1:
        logger.warning(f"  Minority class has only {minority_count} samples — skipping SMOTE")
        return X_train, y_train

    try:
        resampler = SMOTETomek(
            smote=SMOTE(random_state=RANDOM_STATE, k_neighbors=k_neighbors),
            random_state=RANDOM_STATE,
        )
        X_res, y_res = resampler.fit_resample(X_train, y_train)
        logger.info(f"  Before: {len(X_train)} samples → After: {len(X_res)} samples")
        logger.info(f"  Class distribution after: {pd.Series(y_res).value_counts().to_dict()}")
        return pd.DataFrame(X_res, columns=FEATURE_COLS), pd.Series(y_res, name="is_dropout")
    except Exception as exc:
        logger.warning(f"  SMOTE-Tomek failed ({exc}) — using original data")
        return X_train, y_train


# ══════════════════════════════════════════════════════════════════════════
# Stage 5: Hyperparameter Tuning
# ══════════════════════════════════════════════════════════════════════════

def stage_hyperparameter_tuning(
    model_names: List[str],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    scale_pos_weight: float,
    n_trials: int = 50,
    skip_tuning: bool = False,
) -> Dict[str, Dict]:
    """Run Optuna-based hyperparameter tuning for each model."""
    logger.info("━" * 60)
    logger.info("STAGE 5: Hyperparameter Tuning (Optuna)")
    logger.info("━" * 60)

    if skip_tuning:
        logger.info("  Skipping tuning (--skip-tuning). Using default hyperparameters.")
        return {name: {} for name in model_names}

    if not TUNER_AVAILABLE:
        logger.warning("  Optuna not available — using default hyperparameters")
        return {name: {} for name in model_names}

    tuner = HyperparameterTuner(
        n_trials=n_trials,
        cv_folds=5,
        scoring="roc_auc",
        random_state=RANDOM_STATE,
    )

    all_params = tuner.tune_all(model_names, X_train.values, y_train.values, scale_pos_weight)

    for name, params in all_params.items():
        logger.info(f"  {name}: {params or 'defaults'}")

    return all_params


# ══════════════════════════════════════════════════════════════════════════
# Stage 6: Multi-Model Training
# ══════════════════════════════════════════════════════════════════════════

def stage_training(
    model_names: List[str],
    tuned_params: Dict[str, Dict],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    scale_pos_weight: float,
) -> Dict[str, object]:
    """Train all models with tuned (or default) hyperparameters."""
    logger.info("━" * 60)
    logger.info("STAGE 6: Multi-Model Training")
    logger.info("━" * 60)

    zoo = ModelZoo(random_state=RANDOM_STATE)
    trained_models = {}

    for name in model_names:
        params = tuned_params.get(name, {})
        try:
            if name == "random_forest":
                model = zoo.get_random_forest(**params)
            elif name == "xgboost":
                model = zoo.get_xgboost(scale_pos_weight=scale_pos_weight, **params)
            elif name == "lightgbm":
                model = zoo.get_lightgbm(scale_pos_weight=scale_pos_weight, **params)
            elif name == "catboost":
                model = zoo.get_catboost(**params)
            elif name == "gradient_boosting":
                model = zoo.get_gradient_boosting(**params)
            elif name == "mlp":
                model = zoo.get_mlp(**params)
            else:
                logger.warning(f"  Unknown model: {name} — skipping")
                continue

            t0 = time.time()
            model.fit(X_train, y_train)
            elapsed = time.time() - t0
            trained_models[name] = model
            logger.info(f"  ✓ {name} trained in {elapsed:.1f}s")

        except ImportError as exc:
            logger.warning(f"  ✗ {name} unavailable: {exc}")
        except Exception as exc:
            logger.error(f"  ✗ {name} training failed: {exc}")

    logger.info(f"  Successfully trained: {list(trained_models.keys())}")
    return trained_models


# ══════════════════════════════════════════════════════════════════════════
# Stage 7: Evaluation
# ══════════════════════════════════════════════════════════════════════════

def stage_evaluation(
    trained_models: Dict[str, object],
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
) -> Tuple[Dict[str, Dict], Dict[str, Dict]]:
    """Evaluate all trained models with full metrics and plots."""
    logger.info("━" * 60)
    logger.info("STAGE 7: Comprehensive Evaluation")
    logger.info("━" * 60)

    evaluator = ModelEvaluator(random_state=RANDOM_STATE)
    test_reports = {}
    cv_reports = {}

    for name, model in trained_models.items():
        logger.info(f"  Evaluating {name}...")
        report = evaluator.evaluate(model, X_test, y_test, name, feature_names=FEATURE_COLS)
        test_reports[name] = report

        cv = evaluator.cross_validate(model, X_train, y_train, name)
        cv_reports[name] = cv

    # Model comparison table
    comparison = evaluator.compare_models(test_reports)
    logger.info("\n  Model Comparison:")
    logger.info(f"\n{comparison.to_string(index=False)}")

    return test_reports, cv_reports


# ══════════════════════════════════════════════════════════════════════════
# Stage 8: Ensemble Creation
# ══════════════════════════════════════════════════════════════════════════

def stage_ensemble(
    trained_models: Dict[str, object],
    X_test: pd.DataFrame,
    y_test: pd.Series,
    top_n: int = 3,
) -> Tuple[WeightedVotingEnsemble, Dict]:
    """Create weighted voting ensemble from top-N models."""
    logger.info("━" * 60)
    logger.info(f"STAGE 8: Ensemble Creation (Top-{top_n} Models)")
    logger.info("━" * 60)

    ensemble = WeightedVotingEnsemble(power=2.0, threshold=0.5)
    ensemble.fit(trained_models, X_test, y_test, top_n=top_n)

    # Evaluate ensemble
    evaluator = ModelEvaluator(random_state=RANDOM_STATE)
    ensemble_report = evaluator.evaluate(
        ensemble, X_test, y_test, "ensemble", feature_names=FEATURE_COLS
    )

    meta = ensemble.get_metadata()
    meta["test_metrics"] = ensemble_report["metrics"]

    logger.info(f"  Ensemble AUC: {ensemble_report['metrics'].get('roc_auc')}")
    logger.info(f"  Ensemble F1:  {ensemble_report['metrics'].get('f1_score'):.3f}")

    return ensemble, meta


# ══════════════════════════════════════════════════════════════════════════
# Stage 9: Model Export
# ══════════════════════════════════════════════════════════════════════════

def stage_export(
    trained_models: Dict[str, object],
    ensemble: WeightedVotingEnsemble,
    ensemble_meta: Dict,
    test_reports: Dict[str, Dict],
    cv_reports: Dict[str, Dict],
    preprocessing_pipeline: PreprocessingPipeline,
    n_train: int,
    n_test: int,
) -> None:
    """Save all trained models, ensemble, and metadata."""
    logger.info("━" * 60)
    logger.info("STAGE 9: Model Export")
    logger.info("━" * 60)

    # Save individual models
    model_paths = {}
    for name, model in trained_models.items():
        filename = f"{name}_{MODEL_VERSION}.pkl"
        path = SAVED_MODELS_DIR / filename
        joblib.dump(model, path)
        model_paths[name] = str(path)
        logger.info(f"  ✓ {name} → {filename}")

    # Save ensemble
    ensemble_path = SAVED_MODELS_DIR / f"ensemble_{MODEL_VERSION}.pkl"
    joblib.dump(ensemble, ensemble_path)
    logger.info(f"  ✓ ensemble → {ensemble_path.name}")

    # Build comprehensive metadata
    metadata = {
        "model_version": MODEL_VERSION,
        "training_date": datetime.now().isoformat(),
        "training_trimester": "T1",
        "test_trimester": "T2",
        "feature_list": FEATURE_COLS,
        "n_features": len(FEATURE_COLS),
        "n_train_samples": n_train,
        "n_test_samples": n_test,
        "random_state": RANDOM_STATE,
        "smote_applied": IMBALANCE_AVAILABLE,
        "preprocessing": preprocessing_pipeline.get_stats(),
        "ensemble": ensemble_meta,
        "models": {},
    }

    for name in trained_models:
        metadata["models"][name] = {
            "path": model_paths.get(name, ""),
            "test_metrics": test_reports.get(name, {}).get("metrics", {}),
            "cv_metrics": cv_reports.get(name, {}),
        }

    # Save metadata
    metadata_path = SAVED_MODELS_DIR / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    logger.info(f"  ✓ metadata → {metadata_path.name}")

    # Save evaluation report
    evaluator = ModelEvaluator(random_state=RANDOM_STATE)
    evaluator.save_report(test_reports, cv_reports, ensemble_meta)

    # Save backward-compatible individual model files (no version suffix)
    # so existing model_loader.py can find them
    for name, model in trained_models.items():
        compat_name = f"{name}.pkl"
        compat_path = SAVED_MODELS_DIR / compat_name
        joblib.dump(model, compat_path)

    # Also save xgboost as xgboost_model.pkl for legacy compat
    if "xgboost" in trained_models:
        joblib.dump(trained_models["xgboost"], SAVED_MODELS_DIR / "xgboost_model.pkl")

    logger.info("  All models and metadata exported successfully.")


# ══════════════════════════════════════════════════════════════════════════
# Main Orchestrator
# ══════════════════════════════════════════════════════════════════════════

def train_models(skip_tuning: bool = False, n_trials: int = 50):
    """
    Run the complete training pipeline.

    Parameters
    ----------
    skip_tuning : bool
        If True, skip Optuna hyperparameter tuning and use defaults.
    n_trials : int
        Number of Optuna trials per model.
    """
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("EWS Model Training Pipeline v2.0")
    logger.info(f"  Version    : {MODEL_VERSION}")
    logger.info(f"  Date       : {datetime.now().isoformat()}")
    logger.info(f"  Features   : {len(FEATURE_COLS)}")
    logger.info(f"  Tuning     : {'Optuna' if not skip_tuning else 'Disabled'}")
    logger.info("=" * 60)

    # Stage 1: Data Ingestion
    master_df = stage_data_ingestion()

    # Stage 2: Feature Engineering
    X_train, y_train, X_test, y_test, train_fe = stage_feature_engineering(master_df)

    # Stage 3: Preprocessing
    X_train_pp, X_test_pp, pp = stage_preprocessing(X_train, X_test)

    # Stage 4: Class Balancing
    X_train_bal, y_train_bal = stage_class_balancing(X_train_pp, y_train)

    # Compute scale_pos_weight for algorithms that support it
    n_neg = (y_train_bal == 0).sum()
    n_pos = max((y_train_bal == 1).sum(), 1)
    scale_pos_weight = float(n_neg / n_pos)

    # Determine available models
    model_names = ["random_forest", "xgboost", "gradient_boosting", "mlp"]
    from models.model_zoo import LGBM_AVAILABLE, CATBOOST_AVAILABLE
    if LGBM_AVAILABLE:
        model_names.append("lightgbm")
    if CATBOOST_AVAILABLE:
        model_names.append("catboost")

    # Stage 5: Hyperparameter Tuning
    tuned_params = stage_hyperparameter_tuning(
        model_names, X_train_bal, y_train_bal,
        scale_pos_weight, n_trials=n_trials, skip_tuning=skip_tuning,
    )

    # Stage 6: Training
    trained_models = stage_training(
        model_names, tuned_params, X_train_bal, y_train_bal, scale_pos_weight,
    )

    if not trained_models:
        logger.error("No models trained successfully. Aborting.")
        return

    # Stage 7: Evaluation
    test_reports, cv_reports = stage_evaluation(
        trained_models, X_train_pp, y_train, X_test_pp, y_test,
    )

    # Stage 8: Ensemble
    ensemble, ensemble_meta = stage_ensemble(
        trained_models, X_test_pp, y_test, top_n=min(3, len(trained_models)),
    )

    # Stage 9: Export
    stage_export(
        trained_models, ensemble, ensemble_meta,
        test_reports, cv_reports, pp,
        n_train=len(X_train_bal), n_test=len(X_test_pp),
    )

    elapsed = time.time() - start_time
    logger.info("=" * 60)
    logger.info("TRAINING PIPELINE COMPLETE")
    logger.info(f"  Total time     : {elapsed:.1f}s")
    logger.info(f"  Models trained : {len(trained_models)}")
    logger.info(f"  Ensemble       : {ensemble.get_model_names()}")
    logger.info(f"  Model version  : {MODEL_VERSION}")
    logger.info("=" * 60)

    # Print final results
    print("\n" + "=" * 60)
    print("FINAL MODEL PERFORMANCE")
    print("=" * 60)
    for name, report in test_reports.items():
        m = report.get("metrics", {})
        print(f"  {name:20s}  AUC={m.get('roc_auc', 'N/A'):>7}  F1={m.get('f1_score', 0):.3f}  Recall={m.get('recall', 0):.3f}")

    ens_m = ensemble_meta.get("test_metrics", {})
    print(f"  {'ENSEMBLE':20s}  AUC={ens_m.get('roc_auc', 'N/A'):>7}  F1={ens_m.get('f1_score', 0):.3f}  Recall={ens_m.get('recall', 0):.3f}")
    print("=" * 60)


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EWS Model Training Pipeline v2.0")
    parser.add_argument(
        "--skip-tuning", action="store_true",
        help="Skip Optuna hyperparameter tuning (use defaults for faster training)",
    )
    parser.add_argument(
        "--trials", type=int, default=50,
        help="Number of Optuna trials per model (default: 50)",
    )
    args = parser.parse_args()

    train_models(skip_tuning=args.skip_tuning, n_trials=args.trials)
