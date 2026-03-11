"""
ML Service v2.0 — Backend Integration
======================================
Bridges the ML prediction pipeline with the FastAPI backend.
Uses ModelRegistry for model loading and FeatureEngineer for
feature computation. Maintains backward-compatible response schema.
"""
import sys
import os
import logging
import numpy as np
from functools import lru_cache
from typing import Dict, Any, List, Optional

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from models.predict_model import predict, predict_batch, RUNTIME_STATS
from models.feature_engineering import load_data_from_db, engineer_features, FeatureEngineer, FEATURE_COLS
from backend.core.logger import sys_logger

logger = sys_logger


class MLService:
    """
    ML Service that delegates to the updated prediction pipeline.
    Maintains backward-compatible API while using the enhanced v2.0 models.
    """

    def __init__(self):
        self._initialised = True
        logger.info("MLService v2.0 initialised (uses ModelRegistry + ensemble pipeline)")

    @lru_cache(maxsize=1024)
    def predict_student_cached(self, student_id: str):
        return self.predict_student(student_id)

    def predict_student(self, student_id: str) -> Dict[str, Any]:
        """
        Predicts dropout risk for a single student.
        Returns detailed risk analysis compatible with existing API routes.
        """
        try:
            # Load data for this student
            full_df = load_data_from_db()
            if full_df.empty:
                return {"error": "No data available"}

            # Find student in dataset
            if "student_id" in full_df.columns and student_id in full_df["student_id"].values:
                student_row = full_df[full_df["student_id"] == student_id].iloc[0]
                raw_record = student_row.to_dict()
            else:
                # Try with the raw_record approach
                raw_record = {
                    "student_id": student_id,
                    "attendance_rate": 50.0,
                    "avg_quiz_score": 50.0,
                    "num_logins": 10,
                }
                # Student not found in processed data — use fallback
                return {"error": "Student not found in processed data"}

            # Use the new prediction pipeline
            prediction = predict(student_id, raw_record)

            # Map response to backward-compatible format
            result = {
                "student_id": student_id,
                "predictions": {},
                "dropout_probability": prediction.get("dropout_probability", 0.5),
                "risk_level": self._map_risk_label(prediction.get("risk_label", "MEDIUM")),
                "top_risk_factors": self._extract_risk_factors(prediction),
                "model_version": prediction.get("model_version", "unknown"),
                "fallback_used": prediction.get("fallback_used", False),
            }

            # Add individual model predictions
            if not prediction.get("fallback_used", False):
                individual = prediction.get("individual_model_probabilities", {})
                for model_name, prob in individual.items():
                    if prob is not None:
                        result["predictions"][model_name] = {
                            "probability": prob,
                            "risk_class": int(prob > 0.5),
                        }

                # Also add ensemble as a prediction entry
                result["predictions"]["ensemble"] = {
                    "probability": prediction.get("dropout_probability", 0.5),
                    "risk_class": int(prediction.get("dropout_probability", 0.5) > 0.5),
                }

                # Features dict for backward compat
                result["features"] = {
                    feat: raw_record.get(feat, 0.0)
                    for feat in FEATURE_COLS[:12]  # First 12 base features
                }
            else:
                result["predictions"]["heuristic_fallback"] = {
                    "probability": prediction.get("dropout_probability", 0.5),
                    "risk_class": int(prediction.get("dropout_probability", 0.5) > 0.5),
                }

            return result

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {"error": str(e)}

    def batch_predict(self, student_ids: list) -> List[Dict[str, Any]]:
        """Batch processing optimized prediction."""
        logger.info(f"Batch predicting for {len(student_ids)} students")
        results = [self.predict_student_cached(sid) for sid in student_ids]
        return results

    @staticmethod
    def _map_risk_label(label: str) -> str:
        """Map prediction risk label to backend risk level format."""
        mapping = {
            "HIGH": "Critical",
            "MEDIUM": "Medium",
            "LOW": "Low",
        }
        return mapping.get(label, "Medium")

    @staticmethod
    def _extract_risk_factors(prediction: Dict) -> List[str]:
        """Extract human-readable risk factors from top contributing features."""
        factors = []
        top_features = prediction.get("top_contributing_features", [])
        for feat in top_features[:5]:
            feature_name = feat.get("feature", "")
            importance = feat.get("importance", 0.0)
            # Convert feature names to human-readable labels
            label_map = {
                "attendance_rate": "Low Attendance",
                "avg_quiz_score": "Low Quiz Performance",
                "num_logins": "Low Login Activity",
                "content_completion_rate": "Low Content Completion",
                "quiz_completion_rate": "Low Quiz Completion",
                "submission_delay_avg": "Late Submissions",
                "engagement_frequency": "Low Engagement Frequency",
                "engagement_decay": "Declining Engagement",
                "performance_trend": "Declining Performance",
                "assignment_avg": "Low Assignment Scores",
                "risk_behavior_index": "High Risk Behavior",
                "engagement_score_composite": "Low Overall Engagement",
                "attendance_trend": "Declining Attendance",
                "gpa_improvement_rate": "Declining Grades",
                "performance_consistency": "Inconsistent Performance",
            }
            label = label_map.get(feature_name, feature_name.replace("_", " ").title())
            if importance > 0.05:
                factors.append(label)

        return factors if factors else ["Insufficient data for factor analysis"]

    def get_runtime_stats(self) -> Dict[str, Any]:
        """Return runtime prediction statistics."""
        return RUNTIME_STATS.copy()


# Module-level singleton
ml_service = MLService()
