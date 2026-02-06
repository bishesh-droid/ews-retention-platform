"""
ML Configuration
---------------
Machine learning specific configuration and constants.
"""

import os
from pathlib import Path

# Paths
ML_DIR = Path(__file__).resolve().parent
MODELS_DIR = ML_DIR / "models" / "saved"
FEATURES_DIR = ML_DIR / "features"  
TRAINING_DIR = ML_DIR / "training"

# Model settings
DEFAULT_MODEL_NAME = "retention_model.joblib"
XGBOOST_MODEL_NAME = "retention_model_xgboost.joblib"

# Feature engineering  
REQUIRED_STUDENT_FEATURES = [
    'absrate7', 'q4mpa7', 'nsusp7', 'mobility7'
]

# Training parameters
RANDOM_STATE = 42
TEST_SIZE = 0.2
CROSS_VALIDATION_FOLDS = 5

# Prediction thresholds (imported from main config)
from backend.config import RISK_THRESHOLD_HIGH, RISK_THRESHOLD_MEDIUM, RISK_THRESHOLD_LOW

# Model versioning
MODEL_VERSION = os.getenv("MODEL_VERSION", "v1.0")
