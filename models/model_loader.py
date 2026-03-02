"""
Model Loader — Singleton Model Registry
Loads RF and XGB models exactly ONCE at startup and validates feature alignment.

Usage
-----
    from models.model_loader import ModelRegistry
    registry = ModelRegistry.get_instance()  # singleton
    rf_model = registry.get("random_forest")
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import joblib

MODELS_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = MODELS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAVED_MODELS_DIR = MODELS_DIR / "saved_models"
METADATA_PATH    = SAVED_MODELS_DIR / "model_metadata.json"


class ModelVersionMismatch(Exception):
    """Raised when loaded model's feature list differs from active feature_list.json."""
    pass


class ModelRegistry:
    """
    Singleton registry that loads all models once at startup.

    Thread-safe for read-only access (no locking needed; models are immutable after load).
    """

    _instance: Optional["ModelRegistry"] = None

    def __init__(self):
        self._models: Dict[str, Any] = {}
        self._metadata: Dict = {}
        self._loaded = False

    @classmethod
    def get_instance(cls) -> "ModelRegistry":
        """Return the singleton registry (load on first call)."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load_all()
        return cls._instance

    @classmethod
    def reset(cls):
        """Force reload on next get_instance() call. Used in tests."""
        cls._instance = None

    # ------------------------------------------------------------------ #
    # Public accessors
    # ------------------------------------------------------------------ #

    def get(self, model_key: str) -> Optional[Any]:
        """Return a loaded model by key ('random_forest' or 'xgboost')."""
        model = self._models.get(model_key)
        if model is None:
            logger.warning(f"Model '{model_key}' not found in registry. Available: {list(self._models)}")
        return model

    def get_metadata(self) -> Dict:
        """Return the full model metadata dict."""
        return self._metadata

    def get_model_version(self) -> str:
        return self._metadata.get("model_version", "unknown")

    def get_feature_list(self) -> list:
        return self._metadata.get("feature_list", [])

    def is_loaded(self) -> bool:
        return self._loaded

    def available_models(self) -> list:
        return list(self._models.keys())

    # ------------------------------------------------------------------ #
    # Internal loading
    # ------------------------------------------------------------------ #

    def _load_all(self):
        """Load all models defined in model_metadata.json."""
        if not METADATA_PATH.exists():
            logger.error(
                f"model_metadata.json not found at {METADATA_PATH}. "
                "Run train_model.py first."
            )
            return

        with open(METADATA_PATH) as f:
            self._metadata = json.load(f)

        logger.info(
            f"Loading models — version={self._metadata.get('model_version', '?')}, "
            f"features={self._metadata.get('n_features', '?')}"
        )

        # Validate feature list against current feature_list.json
        self._validate_feature_alignment()

        # Load each model
        model_defs = self._metadata.get("models", {})
        for model_key, model_info in model_defs.items():
            path = Path(model_info.get("path", ""))
            if not path.exists():
                # Try relative path from saved_models dir
                candidate = SAVED_MODELS_DIR / path.name
                if candidate.exists():
                    path = candidate
                else:
                    logger.error(f"Model file not found: {path} — '{model_key}' will be unavailable")
                    continue

            try:
                model = joblib.load(path)
                self._models[model_key] = model
                logger.info(f"  ✓ Loaded '{model_key}' from {path.name}")
            except Exception as exc:
                logger.error(f"  ✗ Failed to load '{model_key}': {exc}")

        self._loaded = len(self._models) > 0
        if not self._loaded:
            logger.error("No models loaded. Predictions will fall back to rule-based scoring.")
        else:
            logger.info(f"ModelRegistry ready — {len(self._models)} model(s) loaded")

    def _validate_feature_alignment(self):
        """
        Compare feature list in metadata against current feature_list.json.

        This enforces that:
        - Training feature order (saved in model_metadata.json) matches
          the active registry in feature_list.json.
        - Any mismatch is treated as a hard error, since it means the
          persisted models no longer align with the current feature set.

        Raises
        ------
        ModelVersionMismatch
            If the feature lists differ in length or order.
        """
        feature_list_path = MODELS_DIR / "feature_list.json"
        if not feature_list_path.exists():
            logger.warning("feature_list.json not found — skipping alignment check")
            return

        with open(feature_list_path) as f:
            registry = json.load(f)

        registry_features = registry["metadata"]["feature_names"]
        metadata_features  = self._metadata.get("feature_list", [])

        if registry_features != metadata_features:
            msg = (
                "FEATURE MISMATCH between training and active registry. "
                f"Trained model feature_list length={len(metadata_features)}, "
                f"current registry length={len(registry_features)}. "
                "Retrain models with the current feature_list.json or restore the "
                "matching feature_list.json used during training."
            )
            logger.error(msg)
            raise ModelVersionMismatch(msg)

        logger.info("Feature alignment: OK (✓ feature_list.json matches trained model)")


# ---------------------------------------------------------------------------
# Legacy shim: load_model(filename) — kept for backward compatibility
# ---------------------------------------------------------------------------

def load_model(model_filename: str) -> Any:
    """
    DEPRECATED — use ModelRegistry.get_instance().get('model_key') instead.
    """
    logger.warning(
        f"load_model('{model_filename}') is deprecated. Use ModelRegistry.get_instance()."
    )
    path = SAVED_MODELS_DIR / model_filename
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    return joblib.load(path)
