"""
Model Registry
-------------
Centralized model loading and management with support for multiple model types.
"""

import joblib
from pathlib import Path
from typing import Optional, Any
from backend.ml.config import MODELS_DIR, DEFAULT_MODEL_NAME, XGBOOST_MODEL_NAME
from backend.config import DEFAULT_MODEL_TYPE


class ModelRegistry:
    """
    Manages ML model loading, caching, and swapping.
    Supports multiple model types (XGBoost, Random Forest, etc.)
    """
    
    _models = {}  # Cache for loaded models
    
    @classmethod
    def load_model(cls, model_type: Optional[str] = None) -> Any:
        """
        Load a model by type with caching.
        
        Args:
            model_type: Type of model to load ('xgboost', 'random_forest', etc.)
                       If None, uses DEFAULT_MODEL_TYPE from config
        
        Returns:
            Loaded model object
            
        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        model_type = model_type or DEFAULT_MODEL_TYPE
        
        # Return from cache if already loaded
        if model_type in cls._models:
            return cls._models[model_type]
        
        # Determine model path based on type
        if model_type == "xgboost":
            model_path = MODELS_DIR / XGBOOST_MODEL_NAME
        else:
            model_path = MODELS_DIR / DEFAULT_MODEL_NAME
        
        # Fallback to default if specific model doesn't exist
        if not model_path.exists():
            model_path = MODELS_DIR / DEFAULT_MODEL_NAME
            
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}. "
                "Please train a model first using backend/ml/training/train.py"
            )
        
        # Load and cache the model
        model = joblib.load(model_path)
        cls._models[model_type] = model
        
        return model
    
    @classmethod
    def clear_cache(cls):
        """Clear the model cache to force reload."""
        cls._models = {}
    
    @classmethod
    def get_available_models(cls):
        """List all available model files."""
        if not MODELS_DIR.exists():
            return []
        return [f.name for f in MODELS_DIR.glob("*.joblib")]
