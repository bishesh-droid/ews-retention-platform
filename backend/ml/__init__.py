"""
ML Package
---------
Machine learning pipeline for student retention prediction.

This package contains:
- features/: Feature engineering and extraction
- models/: Model registry and interfaces
- inference/: Prediction and inference logic
- training/: Model training and evaluation
"""

from backend.ml.features import create_features
from backend.ml.models import ModelRegistry

__all__ = [
    "create_features",
    "ModelRegistry",
]
