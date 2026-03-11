"""
Preprocessing Pipeline — Production Grade
==========================================
Sklearn-based preprocessing pipeline with:
  - Missing value imputation (median strategy)
  - IQR-based outlier clamping
  - Standard scaling (z-score normalisation)
  - Duplicate row detection & removal
  - Serialisable pipeline for train/inference parity

Usage (training)
----------------
    from models.preprocessing import PreprocessingPipeline
    pp = PreprocessingPipeline()
    X_train_clean = pp.fit_transform(X_train)
    pp.save()                     # persists to models/saved_models/

Usage (inference)
-----------------
    pp = PreprocessingPipeline.load()
    X_new_clean = pp.transform(X_new)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent
SAVED_MODELS_DIR = MODELS_DIR / "saved_models"


# ── Custom Transformers ──────────────────────────────────────────────────────

class OutlierClamper(BaseEstimator, TransformerMixin):
    """
    Clamp extreme values using the IQR method.

    For each feature, values below Q1 - factor*IQR or above Q3 + factor*IQR
    are clamped to those bounds.  This is fitted on training data only to
    prevent data leakage.
    """

    def __init__(self, factor: float = 1.5):
        self.factor = factor
        self.lower_bounds_: Optional[np.ndarray] = None
        self.upper_bounds_: Optional[np.ndarray] = None

    def fit(self, X, y=None):
        X_arr = np.asarray(X, dtype=float)
        q1 = np.nanpercentile(X_arr, 25, axis=0)
        q3 = np.nanpercentile(X_arr, 75, axis=0)
        iqr = q3 - q1
        self.lower_bounds_ = q1 - self.factor * iqr
        self.upper_bounds_ = q3 + self.factor * iqr
        return self

    def transform(self, X):
        X_arr = np.asarray(X, dtype=float).copy()
        X_arr = np.clip(X_arr, self.lower_bounds_, self.upper_bounds_)
        return X_arr


class DuplicateRemover(BaseEstimator, TransformerMixin):
    """
    Detects and removes exact duplicate rows during fit_transform.

    During transform (inference) duplicates are NOT removed — each input
    row produces exactly one output row — but a warning is logged.
    """

    def __init__(self):
        self.n_duplicates_removed_: int = 0

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if isinstance(X, pd.DataFrame):
            n_before = len(X)
            X_clean = X.drop_duplicates()
            self.n_duplicates_removed_ = n_before - len(X_clean)
            if self.n_duplicates_removed_ > 0:
                logger.info(
                    f"DuplicateRemover: removed {self.n_duplicates_removed_} "
                    f"duplicate rows ({n_before} → {len(X_clean)})"
                )
            return X_clean
        # For numpy arrays, don't remove (can't easily track indices)
        return X


# ── Preprocessing Pipeline ───────────────────────────────────────────────────

class PreprocessingPipeline:
    """
    End-to-end preprocessing pipeline wrapping sklearn components.

    Stages:
        1. Duplicate removal (training only)
        2. Missing value imputation (median)
        3. Outlier clamping (IQR)
        4. Standard scaling (z-score)

    The pipeline is fit on training data and applied identically at
    inference time to prevent train/serve skew.
    """

    PIPELINE_FILENAME = "preprocessing_pipeline.pkl"
    STATS_FILENAME = "preprocessing_stats.json"

    def __init__(self, outlier_factor: float = 1.5):
        self.outlier_factor = outlier_factor
        self.feature_names_: Optional[List[str]] = None
        self._pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("outlier_clamper", OutlierClamper(factor=outlier_factor)),
            ("scaler", StandardScaler()),
        ])
        self._fitted = False
        self._stats: Dict = {}

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    # ── Fit / Transform ──────────────────────────────────────────────────

    def fit(self, X: pd.DataFrame, y=None) -> "PreprocessingPipeline":
        """
        Fit the preprocessing pipeline on training data.

        Parameters
        ----------
        X : pd.DataFrame
            Training feature matrix (numerical columns only).
        """
        self.feature_names_ = list(X.columns)

        # Remove duplicates before fitting
        n_before = len(X)
        X_dedup = X.drop_duplicates()
        n_removed = n_before - len(X_dedup)
        if n_removed > 0:
            logger.info(f"Removed {n_removed} duplicate rows before fitting ({n_before} → {len(X_dedup)})")

        self._pipeline.fit(X_dedup.values)
        self._fitted = True

        # Collect stats for metadata
        self._stats = {
            "n_features": len(self.feature_names_),
            "n_training_samples": n_before,
            "n_duplicates_removed": n_removed,
            "n_training_samples_after_dedup": len(X_dedup),
            "imputer_strategy": "median",
            "outlier_factor": self.outlier_factor,
            "scaler": "StandardScaler",
            "imputed_medians": {
                name: float(val)
                for name, val in zip(
                    self.feature_names_,
                    self._pipeline.named_steps["imputer"].statistics_,
                )
            },
        }
        logger.info(f"PreprocessingPipeline fitted on {len(X_dedup)} samples, {len(self.feature_names_)} features")
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Transform features using the fitted pipeline.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix with the same columns used during fit.

        Returns
        -------
        pd.DataFrame
            Preprocessed feature matrix (same column names).
        """
        if not self._fitted:
            raise RuntimeError("PreprocessingPipeline must be fitted before transform(). Call fit() first.")

        X_transformed = self._pipeline.transform(X.values)
        return pd.DataFrame(X_transformed, columns=self.feature_names_, index=X.index)

    def fit_transform(self, X: pd.DataFrame, y=None) -> pd.DataFrame:
        """Fit and transform in one step."""
        self.fit(X, y)
        # Re-transform the full X (including duplicates) to preserve row alignment
        return self.transform(X)

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self, directory: Optional[Path] = None) -> Path:
        """Save the fitted pipeline and stats to disk."""
        save_dir = directory or SAVED_MODELS_DIR
        save_dir.mkdir(parents=True, exist_ok=True)

        pipeline_path = save_dir / self.PIPELINE_FILENAME
        joblib.dump({
            "pipeline": self._pipeline,
            "feature_names": self.feature_names_,
            "outlier_factor": self.outlier_factor,
            "stats": self._stats,
        }, pipeline_path)
        logger.info(f"Preprocessing pipeline saved → {pipeline_path}")

        # Also save human-readable stats
        stats_path = save_dir / self.STATS_FILENAME
        with open(stats_path, "w") as f:
            json.dump(self._stats, f, indent=2)

        return pipeline_path

    @classmethod
    def load(cls, directory: Optional[Path] = None) -> "PreprocessingPipeline":
        """Load a fitted pipeline from disk."""
        load_dir = directory or SAVED_MODELS_DIR
        pipeline_path = load_dir / cls.PIPELINE_FILENAME

        if not pipeline_path.exists():
            raise FileNotFoundError(
                f"Preprocessing pipeline not found at {pipeline_path}. "
                "Run the training pipeline first."
            )

        data = joblib.load(pipeline_path)
        instance = cls(outlier_factor=data.get("outlier_factor", 1.5))
        instance._pipeline = data["pipeline"]
        instance.feature_names_ = data["feature_names"]
        instance._stats = data.get("stats", {})
        instance._fitted = True
        logger.info(f"Preprocessing pipeline loaded from {pipeline_path}")
        return instance

    def get_stats(self) -> Dict:
        """Return preprocessing statistics."""
        return self._stats.copy()

    # ── Utility ──────────────────────────────────────────────────────────

    def detect_outliers(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Return a boolean mask of outlier positions (True = outlier).

        Useful for inspection before clamping.
        """
        clamper = self._pipeline.named_steps["outlier_clamper"]
        if clamper.lower_bounds_ is None:
            raise RuntimeError("Pipeline not fitted yet.")

        X_arr = X.values.astype(float)
        is_outlier = (X_arr < clamper.lower_bounds_) | (X_arr > clamper.upper_bounds_)
        return pd.DataFrame(is_outlier, columns=X.columns, index=X.index)
