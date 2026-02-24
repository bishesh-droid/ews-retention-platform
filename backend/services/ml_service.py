import sys
import os
import logging
import joblib
import pandas as pd
import numpy as np
from functools import lru_cache

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from models.feature_engineering import load_data_from_db, engineer_features
from backend.core.logger import sys_logger
from backend.database import SessionLocal, Prediction

logger = sys_logger

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../models/saved_models'))

class MLService:
    def __init__(self):
        self.rf_model = None
        self.xgb_model = None
        self.load_models()

    def load_models(self):
        try:
            rf_path = os.path.join(MODELS_DIR, "random_forest.pkl")
            xgb_path = os.path.join(MODELS_DIR, "xgboost_model.pkl")
            
            if os.path.exists(rf_path):
                self.rf_model = joblib.load(rf_path)
                logger.info(f"Loaded Random Forest model from {rf_path}")
            else:
                logger.warning(f"Random Forest model not found at {rf_path}. Will use fallback heuristic if ML fails.")

            if os.path.exists(xgb_path):
                self.xgb_model = joblib.load(xgb_path)
                logger.info(f"Loaded XGBoost model from {xgb_path}")
            else:
                logger.warning(f"XGBoost model not found at {xgb_path}. Will use fallback heuristic if ML fails.")

        except Exception as e:
            logger.error(f"Error loading models: {e}")

    def _fallback_heuristic(self, student_row):
        """Standardized fallback if ML models fail or are absent."""
        risk = 0.5
        factors = []
        if student_row['content_completion_rate'].values[0] < 0.3:
            risk += 0.2
            factors.append("Critically Low Content Completion")
        if student_row['num_logins'].values[0] < 3:
            risk += 0.15
            factors.append("Critically Low Login Activity")
        if student_row['quiz_completion_rate'].values[0] < 0.5:
             risk += 0.15
             factors.append("Critically Low Quiz Performance")
        
        return {
            "probability": min(risk, 0.99),
            "risk_class": int(risk > 0.5),
            "factors": factors
        }

    @lru_cache(maxsize=1024)
    def predict_student_cached(self, student_id: str):
         return self.predict_student(student_id)

    def predict_student(self, student_id: str):
        """
        Predicts dropout risk for a single student.
        Returns detailed risk analysis.
        """
        if not self.rf_model and not self.xgb_model:
            logger.warning("Models not loaded. Using fallback heuristic.")
            # We don't return error; we use graceful fallback later

        # Load data for this student (inefficient to load all, but for now reuse existing logic)
        # TODO: Optimize to load single student data
        try:
            full_df = load_data_from_db()
            if full_df.empty:
                 return {"error": "No data available"}
            
            features_df = engineer_features(full_df)
            
            if student_id not in features_df['student_id'].values:
                return {"error": "Student not found in processed data"}

            student_row = features_df[features_df['student_id'] == student_id]
            
            # features used for training
            feature_cols = [
                'content_completed', 'content_required', 'quiz_completed', 
                'total_quiz_attempts', 'num_logins', 'total_time_spent_seconds',
                'discussion_posts_created', 'discussion_posts_read', 'courses_enrolled',
                'content_completion_rate', 'quiz_completion_rate', 'avg_time_per_course'
            ]
            
            X_input = student_row[feature_cols]
            
            result = {
                "student_id": student_id,
                "predictions": {}
            }

            if self.rf_model:
                rf_prob = self.rf_model.predict_proba(X_input)[:, 1][0]
                result["predictions"]["random_forest"] = {
                    "probability": float(rf_prob),
                    "risk_class": int(rf_prob > 0.5)
                }

            if self.xgb_model:
                xgb_prob = self.xgb_model.predict_proba(X_input)[:, 1][0]
                result["predictions"]["xgboost"] = {
                    "probability": float(xgb_prob),
                    "risk_class": int(xgb_prob > 0.5)
                }
                
                # Feature Importance / explanation (simple)
                # Since SHAP is heavy, we just return feature values for now
                result["features"] = X_input.to_dict(orient='records')[0]
                
                # Heuristic "Top Factors"
                # If risk is high, what constitutes it?
                factors = []
                if student_row['content_completion_rate'].values[0] < 0.2:
                    factors.append("Low Content Completion")
                if student_row['num_logins'].values[0] < 5:
                    factors.append("Low Login Activity")
                if student_row['quiz_completion_rate'].values[0] < 0.5:
                     factors.append("Low Quiz Performance")
                
                result["top_risk_factors"] = factors

            if not self.rf_model and not self.xgb_model:
                 logger.warning("No ML models loaded for student %s; using heuristic fallback prediction.", student_row.index[0] if not student_row.empty else "unknown")
                 fallback = self._fallback_heuristic(student_row)
                 result["predictions"]["heuristic_fallback"] = {"probability": fallback["probability"], "risk_class": fallback["risk_class"]}
                 result["top_risk_factors"] = fallback["factors"]
            
            # Overall Score (Avg if both exist)
            probs = []
            if "random_forest" in result["predictions"]:
                probs.append(result["predictions"]["random_forest"]["probability"])
            if "xgboost" in result["predictions"]:
                probs.append(result["predictions"]["xgboost"]["probability"])
            if "heuristic_fallback" in result["predictions"]:
                probs.append(result["predictions"]["heuristic_fallback"]["probability"])
            
            if probs:
                result["dropout_probability"] = sum(probs) / len(probs)
                result["risk_level"] = "Critical" if result["dropout_probability"] > 0.75 else \
                                       "High" if result["dropout_probability"] > 0.5 else \
                                       "Medium" if result["dropout_probability"] > 0.3 else "Low"

            return result

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {"error": str(e)}

    def batch_predict(self, student_ids: list):
        """Batch processing optimized prediction."""
        logger.info(f"Batch predicting for {len(student_ids)} students")
        results = [self.predict_student_cached(sid) for sid in student_ids]
        return results

ml_service = MLService()
