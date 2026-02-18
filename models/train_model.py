import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from imblearn.over_sampling import SMOTE
import os
import sys
import logging
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.feature_engineering import load_data_from_db, engineer_features, FEATURE_COLS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), 'saved_models')
os.makedirs(MODELS_DIR, exist_ok=True)

def train_models():
    logger.info("Starting model training pipeline...")
    
    # 1. Load Data
    raw_df = load_data_from_db()
    if raw_df.empty:
        logger.error("No data loaded. Exiting.")
        return

    # 2. Split by Trimester (Train on T1, Test on T2)
    logger.info("Creating features for Trimester 1 (Train)...")
    train_df = engineer_features(raw_df, semester='Trimester 1')
    
    logger.info("Creating features for Trimester 2 (Test)...")
    test_df = engineer_features(raw_df, semester='Trimester 2')
    
    if train_df.empty or test_df.empty:
        logger.error("Train or Test set is empty. Check semester Filtering.")
        # Fallback to random split if trimesters not found (e.g. if data is not labeled properly)
        logger.warning("Falling back to random split on full dataset...")
        full_df = engineer_features(raw_df)
        from sklearn.model_selection import train_test_split
        train_df, test_df = train_test_split(full_df, test_size=0.3, random_state=42)

    # 3. Prepare X and y
    target_col = 'is_dropout'

    X_train = train_df[FEATURE_COLS]
    y_train = train_df[target_col]
    
    # Align columns in test set
    X_test = test_df[FEATURE_COLS]
    y_test = test_df[target_col]

    logger.info(f"Training shapes: X_train={X_train.shape}, y_train={y_train.shape}")
    logger.info(f"Testing shapes: X_test={X_test.shape}, y_test={y_test.shape}")
    logger.info(f"Class imbalance (Train): {y_train.value_counts().to_dict()}")

    # 4. Handle Imbalance (SMOTE)
    logger.info("Applying SMOTE to training data...")
    # Handle case where class 1 might be very small
    k_neighbors = 5
    if y_train.value_counts().min() <= 5:
        k_neighbors = 1
    
    smote = SMOTE(random_state=42, k_neighbors=k_neighbors)
    try:
        X_train_res, y_train_res = smote.fit_resample(X_train, y_train)
    except ValueError as e:
        logger.warning(f"SMOTE failed: {e}. using original data.")
        X_train_res, y_train_res = X_train, y_train

    # 5. Train Random Forest
    logger.info("Training Random Forest...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_train_res, y_train_res)
    
    rf_pred = rf.predict(X_test)
    rf_prob = rf.predict_proba(X_test)[:, 1]
    
    logger.info("Random Forest Evaluation:")
    print(classification_report(y_test, rf_pred))
    rf_auc = roc_auc_score(y_test, rf_prob) if len(y_test.unique()) > 1 else 0
    logger.info(f"Random Forest AUC: {rf_auc}")

    # 6. Train XGBoost
    logger.info("Training XGBoost...")
    xgb = XGBClassifier(eval_metric='logloss', n_estimators=100, max_depth=6, learning_rate=0.1)
    xgb.fit(X_train_res, y_train_res)
    
    xgb_pred = xgb.predict(X_test)
    xgb_prob = xgb.predict_proba(X_test)[:, 1]
    
    logger.info("XGBoost Evaluation:")
    print(classification_report(y_test, xgb_pred))
    xgb_auc = roc_auc_score(y_test, xgb_prob) if len(y_test.unique()) > 1 else 0
    logger.info(f"XGBoost AUC: {xgb_auc}")

    # 7. Save Models
    logger.info("Saving models...")
    joblib.dump(rf, os.path.join(MODELS_DIR, "random_forest.pkl"))
    joblib.dump(xgb, os.path.join(MODELS_DIR, "xgboost_model.pkl"))
    
    # Save Feature Importance
    feature_importance = {
        "feature_names": FEATURE_COLS,
        "importances": list(xgb.feature_importances_.astype(float)) # Convert to float for JSON serialization
    }
    with open(os.path.join(MODELS_DIR, "feature_importance.json"), "w") as f:
        json.dump(feature_importance, f)

    logger.info(f"Models saved to {MODELS_DIR}")

if __name__ == "__main__":
    train_models()
