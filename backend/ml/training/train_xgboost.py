"""
XGBoost Training Script for EWS Student Retention Platform
===========================================================

Generates synthetic student data matching the 12 DB-derived features,
trains an XGBoost classifier with class imbalance handling,
evaluates with cross-validation, and saves the model.

Usage:
    cd /home/duffer/Gemini/Project_1(complete)/ews-retention-platform
    python -m backend.ml.training.train_xgboost

Outputs:
    - backend/ml/models/saved/retention_model_xgboost.joblib
    - backend/ml/models/saved/model_metrics.json
    - backend/ml/models/saved/feature_names.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# XGBoost and sklearn imports
try:
    import xgboost as xgb
except ImportError:
    print("Installing xgboost...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost"])
    import xgboost as xgb

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix, roc_curve
)
import joblib


# ============================================================================
# 12 DB-DERIVED FEATURES (must match feature_engineering.py output)
# ============================================================================

FEATURE_NAMES: List[str] = [
    "content_completion_score",      # 0-100: content completion rate
    "login_consistency_score",       # 0-100: login frequency
    "quiz_engagement_score",         # 0-100: quiz completion/attempts
    "assignment_score",              # 0-100: assignment submissions
    "time_investment_score",         # 0-100: time spent in content
    "discussion_engagement_score",   # 0-100: discussion participation
    "self_directed_learning_score",  # 0-100: optional course engagement
    "w1w2_completion_score",         # 0-100: weeks 1 & 2 content completion
    "zero_progress_ratio",           # 0-1: fraction of courses with zero progress
    "graded_quiz_score",             # 0-100: average graded quiz score
    "graded_assignment_score",       # 0-100: average graded assignment score
    "exam_score",                    # 0-100: exam performance score
]

# Training configuration
RANDOM_STATE = 42
N_SAMPLES = 5000
TEST_SIZE = 0.2
CV_FOLDS = 5

# Model paths
MODELS_DIR = Path(__file__).parent.parent / "models" / "saved"
MODEL_PATH = MODELS_DIR / "retention_model_xgboost.joblib"
METRICS_PATH = MODELS_DIR / "model_metrics.json"
FEATURES_PATH = MODELS_DIR / "feature_names.json"


def generate_synthetic_student_data(n_samples: int = N_SAMPLES) -> pd.DataFrame:
    """
    Generate synthetic student data matching the 12 DB-derived features.
    
    Creates realistic correlations between features and dropout risk:
    - Low engagement features -> higher dropout probability
    - High self-directed learning -> lower dropout probability
    - Zero progress ratio -> strongly predictive of dropout
    
    Returns:
        DataFrame with features and target (dropped_out: 0/1)
    """
    np.random.seed(RANDOM_STATE)
    
    # Generate base engagement features with realistic distributions
    # Using beta distribution to get 0-100 bounded values
    
    # Content completion - most students have moderate completion
    content_completion = np.random.beta(2, 1.5, n_samples) * 100
    
    # Login consistency - correlated with content completion
    login_consistency = (
        0.6 * content_completion + 
        0.4 * np.random.beta(2, 2, n_samples) * 100
    )
    
    # Quiz engagement - correlated with content completion
    quiz_engagement = (
        0.5 * content_completion + 
        0.5 * np.random.beta(2, 2, n_samples) * 100
    )
    
    # Assignment score - correlated with quiz engagement
    assignment_score = (
        0.6 * quiz_engagement + 
        0.4 * np.random.beta(2, 2, n_samples) * 100
    )
    
    # Time investment - correlated with login consistency
    time_investment = (
        0.5 * login_consistency + 
        0.5 * np.random.beta(1.5, 2, n_samples) * 100
    )
    
    # Discussion engagement - independent, lower values generally
    discussion_engagement = np.random.beta(1, 3, n_samples) * 100
    
    # Self-directed learning - independent, rarer but good signal
    self_directed_learning = np.random.beta(1, 4, n_samples) * 100
    
    # W1W2 completion - strongly correlated with overall content completion
    w1w2_completion = (
        0.7 * content_completion + 
        0.3 * np.random.beta(2, 1.5, n_samples) * 100
    )
    
    # Zero progress ratio - inverse to content completion
    zero_progress_ratio = np.clip(
        1.0 - (content_completion / 100) + np.random.normal(0, 0.1, n_samples),
        0, 1
    )
    
    # Graded quiz score - correlated with quiz engagement
    graded_quiz_score = (
        0.6 * quiz_engagement + 
        0.4 * np.random.beta(2.5, 1.5, n_samples) * 100
    )
    
    # Graded assignment score - correlated with assignment score
    graded_assignment_score = (
        0.7 * assignment_score + 
        0.3 * np.random.beta(2, 2, n_samples) * 100
    )
    
    # Exam score - correlated with graded quiz and assignment scores
    exam_score = (
        0.4 * graded_quiz_score + 
        0.4 * graded_assignment_score + 
        0.2 * np.random.beta(2, 2, n_samples) * 100
    )
    
    # Create DataFrame
    df = pd.DataFrame({
        "content_completion_score": np.clip(content_completion, 0, 100),
        "login_consistency_score": np.clip(login_consistency, 0, 100),
        "quiz_engagement_score": np.clip(quiz_engagement, 0, 100),
        "assignment_score": np.clip(assignment_score, 0, 100),
        "time_investment_score": np.clip(time_investment, 0, 100),
        "discussion_engagement_score": np.clip(discussion_engagement, 0, 100),
        "self_directed_learning_score": np.clip(self_directed_learning, 0, 100),
        "w1w2_completion_score": np.clip(w1w2_completion, 0, 100),
        "zero_progress_ratio": np.clip(zero_progress_ratio, 0, 1),
        "graded_quiz_score": np.clip(graded_quiz_score, 0, 100),
        "graded_assignment_score": np.clip(graded_assignment_score, 0, 100),
        "exam_score": np.clip(exam_score, 0, 100),
    })
    
    # Generate dropout labels based on feature combinations
    # Lower scores = higher dropout risk
    dropout_risk_score = (
        -0.3 * df["content_completion_score"] +
        -0.2 * df["login_consistency_score"] +
        -0.2 * df["quiz_engagement_score"] +
        -0.15 * df["assignment_score"] +
        -0.1 * df["time_investment_score"] +
        -0.05 * df["discussion_engagement_score"] +
        +0.3 * df["zero_progress_ratio"] * 100 +  # Strong positive predictor
        -0.1 * df["graded_quiz_score"] +
        -0.1 * df["graded_assignment_score"] +
        -0.1 * df["exam_score"] +
        -0.15 * df["self_directed_learning_score"]  # Protective factor
    )
    
    # Normalize and add noise
    dropout_risk_score = (dropout_risk_score - dropout_risk_score.mean()) / dropout_risk_score.std()
    dropout_risk_score += np.random.normal(0, 0.5, n_samples)
    
    # Convert to probability using sigmoid
    dropout_prob = 1 / (1 + np.exp(-dropout_risk_score))
    
    # Sample binary outcome
    df["dropped_out"] = (np.random.random(n_samples) < dropout_prob).astype(int)
    
    return df


def calculate_class_weights(y: np.ndarray) -> float:
    """
    Calculate scale_pos_weight for XGBoost to handle class imbalance.
    
    scale_pos_weight = sum(negative) / sum(positive)
    """
    n_negative = np.sum(y == 0)
    n_positive = np.sum(y == 1)
    
    if n_positive == 0:
        return 1.0
    
    return n_negative / n_positive


def train_xgboost_model(df: pd.DataFrame) -> Tuple[xgb.XGBClassifier, Dict[str, Any]]:
    """
    Train XGBoost classifier with cross-validation.
    
    Args:
        df: DataFrame with features and target
        
    Returns:
        Trained model and metrics dictionary
    """
    # Prepare features and target
    X = df[FEATURE_NAMES].values
    y = df["dropped_out"].values
    
    print(f"\nDataset: {len(df)} samples")
    print(f"  - Retained (0): {np.sum(y == 0)} ({np.sum(y == 0)/len(y)*100:.1f}%)")
    print(f"  - Dropped out (1): {np.sum(y == 1)} ({np.sum(y == 1)/len(y)*100:.1f}%)")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    
    # Calculate scale_pos_weight for class imbalance
    scale_pos_weight = calculate_class_weights(y_train)
    print(f"\nClass imbalance handling:")
    print(f"  - scale_pos_weight: {scale_pos_weight:.2f}")
    
    # Initialize XGBoost classifier
    model = xgb.XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        scale_pos_weight=scale_pos_weight,
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    
    # Cross-validation
    print(f"\nRunning {CV_FOLDS}-fold cross-validation...")
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    
    cv_auc_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="roc_auc")
    cv_precision = cross_val_score(model, X_train, y_train, cv=cv, scoring="precision")
    cv_recall = cross_val_score(model, X_train, y_train, cv=cv, scoring="recall")
    cv_f1 = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1")
    
    print(f"\nCross-validation results:")
    print(f"  - AUC-ROC:  {cv_auc_scores.mean():.4f} (+/- {cv_auc_scores.std()*2:.4f})")
    print(f"  - Precision: {cv_precision.mean():.4f} (+/- {cv_precision.std()*2:.4f})")
    print(f"  - Recall:    {cv_recall.mean():.4f} (+/- {cv_recall.std()*2:.4f})")
    print(f"  - F1:        {cv_f1.mean():.4f} (+/- {cv_f1.std()*2:.4f})")
    
    # Train final model on full training set
    print("\nTraining final model...")
    model.fit(X_train, y_train)
    
    # Evaluate on test set
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    test_auc = roc_auc_score(y_test, y_pred_proba)
    test_precision = precision_score(y_test, y_pred, zero_division=0)
    test_recall = recall_score(y_test, y_pred, zero_division=0)
    test_f1 = f1_score(y_test, y_pred, zero_division=0)
    
    print(f"\nTest set results:")
    print(f"  - AUC-ROC:   {test_auc:.4f}")
    print(f"  - Precision: {test_precision:.4f}")
    print(f"  - Recall:    {test_recall:.4f}")
    print(f"  - F1 Score:  {test_f1:.4f}")
    
    print(f"\nClassification report:")
    print(classification_report(y_test, y_pred, target_names=["Retained", "Dropped Out"]))
    
    # Feature importance
    importance = model.feature_importances_
    feature_importance = list(zip(FEATURE_NAMES, importance))
    feature_importance.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\nTop 5 feature importances:")
    for name, imp in feature_importance[:5]:
        print(f"  - {name}: {imp:.4f}")
    
    # Compile metrics
    metrics = {
        "model_type": "XGBoostClassifier",
        "n_features": len(FEATURE_NAMES),
        "n_samples": len(df),
        "class_distribution": {
            "retained": int(np.sum(y == 0)),
            "dropped_out": int(np.sum(y == 1)),
        },
        "cross_validation": {
            "folds": CV_FOLDS,
            "auc_mean": round(float(cv_auc_scores.mean()), 4),
            "auc_std": round(float(cv_auc_scores.std()), 4),
            "precision_mean": round(float(cv_precision.mean()), 4),
            "recall_mean": round(float(cv_recall.mean()), 4),
            "f1_mean": round(float(cv_f1.mean()), 4),
        },
        "test_set": {
            "auc_roc": round(float(test_auc), 4),
            "precision": round(float(test_precision), 4),
            "recall": round(float(test_recall), 4),
            "f1_score": round(float(test_f1), 4),
        },
        "training_params": {
            "scale_pos_weight": round(float(scale_pos_weight), 4),
            "n_estimators": 200,
            "max_depth": 6,
            "learning_rate": 0.1,
        },
        "feature_importance": [
            {"feature": name, "importance": round(float(imp), 4)}
            for name, imp in feature_importance
        ],
    }
    
    return model, metrics


def save_model(model: xgb.XGBClassifier, metrics: Dict[str, Any]) -> None:
    """
    Save the trained model and associated metadata.
    """
    # Create directory if needed
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save model
    joblib.dump(model, MODEL_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")
    
    # Save metrics
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved to: {METRICS_PATH}")
    
    # Save feature names for inference
    feature_metadata = {
        "feature_names": FEATURE_NAMES,
        "n_features": len(FEATURE_NAMES),
        "description": "12 DB-derived features from FeatureEngineer.calculate_all_features()",
    }
    with open(FEATURES_PATH, "w") as f:
        json.dump(feature_metadata, f, indent=2)
    print(f"Feature names saved to: {FEATURES_PATH}")


def main():
    """Main training pipeline."""
    print("=" * 70)
    print("EWS Retention Platform - XGBoost Model Training")
    print("=" * 70)
    
    # Generate synthetic data
    print("\n[1/4] Generating synthetic student data...")
    df = generate_synthetic_student_data(N_SAMPLES)
    print(f"Generated {len(df)} synthetic student records")
    
    # Train model
    print("\n[2/4] Training XGBoost classifier...")
    model, metrics = train_xgboost_model(df)
    
    # Save model and metrics
    print("\n[3/4] Saving model and artifacts...")
    save_model(model, metrics)
    
    # Summary
    print("\n[4/4] Training complete!")
    print("=" * 70)
    print(f"Model: XGBoostClassifier ({metrics['n_features']} features)")
    print(f"Test AUC-ROC: {metrics['test_set']['auc_roc']:.4f}")
    print(f"Test F1: {metrics['test_set']['f1_score']:.4f}")
    print(f"Model path: {MODEL_PATH}")
    print("=" * 70)
    
    return model, metrics


if __name__ == "__main__":
    main()
