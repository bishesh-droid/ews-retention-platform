import sys
import os
import argparse
import logging
import json
import joblib
import pandas as pd

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.feature_engineering import load_data_from_db, engineer_features

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS_DIR = os.path.join(os.path.dirname(__file__), 'saved_models')

def load_models():
    rf_path = os.path.join(MODELS_DIR, "random_forest.pkl")
    xgb_path = os.path.join(MODELS_DIR, "xgboost_model.pkl")
    
    models = {}
    if os.path.exists(rf_path):
        models['rf'] = joblib.load(rf_path)
    if os.path.exists(xgb_path):
        models['xgb'] = joblib.load(xgb_path)
    return models

def predict(student_id):
    models = load_models()
    if not models:
        logger.error("No models found!")
        return

    # Load All Data (inefficient but simple for script)
    logger.info("Loading data...")
    raw_df = load_data_from_db()
    if raw_df.empty:
        logger.error("No data found.")
        return

    features_df = engineer_features(raw_df)
    
    if student_id not in features_df['student_id'].values:
        logger.error(f"Student {student_id} not found in data.")
        return

    student_row = features_df[features_df['student_id'] == student_id]
    
    feature_cols = [
        'content_completed', 'content_required', 'quiz_completed', 
        'total_quiz_attempts', 'num_logins', 'total_time_spent_seconds',
        'discussion_posts_created', 'discussion_posts_read', 'courses_enrolled',
        'content_completion_rate', 'quiz_completion_rate', 'avg_time_per_course'
    ]
    
    X_input = student_row[feature_cols]
    
    results = {
        "student_id": student_id,
        "predictions": {}
    }

    if 'rf' in models:
        rf_prob = models['rf'].predict_proba(X_input)[:, 1][0]
        results["predictions"]["random_forest"] = float(rf_prob)

    if 'xgb' in models:
        xgb_prob = models['xgb'].predict_proba(X_input)[:, 1][0]
        results["predictions"]["xgboost"] = float(xgb_prob)

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict dropout risk for a student")
    parser.add_argument("student_id", help="Student ID to predict for")
    args = parser.parse_args()
    
    predict(args.student_id)
