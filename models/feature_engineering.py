"""
Feature Engineering Pipeline — Production Grade
Single source of truth for feature computation used by both training and inference.

Contracts
---------
- FeatureEngineer.compute(raw_record) always returns features in the EXACT ORDER defined in feature_list.json.
- validate_feature_vector(vec) raises FeatureValidationError if contract is violated.
- FEATURE_COLS is derived from feature_list.json — never hardcoded.
- Both train_model.py and predict_model.py import FEATURE_COLS and FeatureEngineer from here.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ── Path setup ─────────────────────────────────────────────────────────────
MODELS_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = MODELS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Feature Registry ────────────────────────────────────────────────────────
FEATURE_LIST_PATH = MODELS_DIR / "feature_list.json"

if not FEATURE_LIST_PATH.exists():
    raise FileNotFoundError(
        f"feature_list.json not found at {FEATURE_LIST_PATH}. "
        "This file is required before running any model training or inference."
    )

with open(FEATURE_LIST_PATH, "r") as _f:
    _REGISTRY: Dict = json.load(_f)

# The single authoritative feature name list — ORDER IS FIXED
FEATURE_COLS: List[str] = _REGISTRY["metadata"]["feature_names"]
_FEATURE_META: Dict[str, Dict] = {f["name"]: f for f in _REGISTRY["features"]}
TARGET_COL = _REGISTRY["target"]["name"]  # "is_dropout"


# ── Exception ────────────────────────────────────────────────────────────────
class FeatureValidationError(ValueError):
    """Raised when a feature vector does not conform to the registry."""
    pass


# ── Feature Engineer ────────────────────────────────────────────────────────
class FeatureEngineer:
    """
    Computes and validates model-ready feature vectors.

    Usage (inference)
    -----------------
    fe = FeatureEngineer()
    vec = fe.compute(raw_record)  # dict
    X   = fe.to_dataframe([vec])  # pd.DataFrame, columns=FEATURE_COLS

    Usage (training)
    ----------------
    fe = FeatureEngineer(fit=True)
    X, y = fe.fit_transform(master_df)
    """

    def __init__(self, fit: bool = False):
        """
        Parameters
        ----------
        fit : bool
            If True, compute imputation medians from training data.
            If False (inference), imputation medians must have been set via load_imputation_stats().
        """
        self._fit = fit
        self._imputation_medians: Dict[str, float] = {}

    # ------------------------------------------------------------------ #
    # Public — inference path
    # ------------------------------------------------------------------ #

    def compute(self, raw_record: Dict[str, Any]) -> Dict[str, float]:
        """
        Compute a model-ready feature vector from a raw student record.

        Parameters
        ----------
        raw_record : dict
            Keys are raw or canonical column names. Values are raw data.

        Returns
        -------
        dict
            Keys = FEATURE_COLS in order. Values = float.
        """
        vec: Dict[str, float] = {}

        for feat_name in FEATURE_COLS:
            meta = _FEATURE_META[feat_name]
            raw_val = raw_record.get(feat_name, None)

            # Coerce to float
            value = self._coerce_float(raw_val)

            # Apply missing strategy
            if value is None or (isinstance(value, float) and np.isnan(value)):
                value = self._apply_missing_strategy(feat_name, meta)

            # Clamp to valid range
            lo, hi = meta.get("range", [None, None])
            if lo is not None and value is not None:
                value = max(lo, min(hi, value))

            vec[feat_name] = float(value) if value is not None else 0.0

        return vec

    def to_dataframe(self, records: List[Dict[str, float]]) -> pd.DataFrame:
        """Convert list of feature vectors to a properly-ordered DataFrame."""
        df = pd.DataFrame(records, columns=FEATURE_COLS)
        return df[FEATURE_COLS]  # Guarantee column order

    def validate_feature_vector(self, vec: Dict[str, float]) -> None:
        """
        Validate that `vec` conforms to the feature registry.
        Raises FeatureValidationError on any violation.
        """
        # Check all expected features are present
        missing_keys = [f for f in FEATURE_COLS if f not in vec]
        if missing_keys:
            raise FeatureValidationError(
                f"Feature vector is missing {len(missing_keys)} features: {missing_keys}"
            )

        # Check for unexpected features
        extra_keys = [k for k in vec if k not in FEATURE_COLS]
        if extra_keys:
            logger.warning(f"Feature vector has {len(extra_keys)} extra (ignored) keys: {extra_keys}")

        # Check ranges and types
        for feat_name in FEATURE_COLS:
            val = vec.get(feat_name)
            if val is None:
                raise FeatureValidationError(f"Feature '{feat_name}' is None in vector")

            meta = _FEATURE_META[feat_name]
            lo, hi = meta.get("range", [None, None])
            if lo is not None and (val < lo or val > hi):
                raise FeatureValidationError(
                    f"Feature '{feat_name}' = {val} is outside valid range [{lo}, {hi}]"
                )

    # ------------------------------------------------------------------ #
    # Public — training path
    # ------------------------------------------------------------------ #

    def fit_transform(
        self,
        df: pd.DataFrame,
        trimester_filter: Optional[str] = None,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Fit imputation medians on df (training data) and return (X, y).
        Optionally filter by trimester first.

        Parameters
        ----------
        df : pd.DataFrame
            Master dataset (loaded from clean_master_dataset.csv).
        trimester_filter : str, optional
            If given, only rows where df['trimester'] == trimester_filter are used.

        Returns
        -------
        X : pd.DataFrame, shape (n_samples, 16), columns = FEATURE_COLS
        y : pd.Series, shape (n_samples,), values = 0/1
        """
        if trimester_filter:
            df = df[df["trimester"] == trimester_filter].copy()

        if df.empty:
            logger.error(f"No rows for trimester_filter={trimester_filter!r}")
            return pd.DataFrame(columns=FEATURE_COLS), pd.Series(dtype=int)

        # Fit imputation medians from training data
        for feat_name in FEATURE_COLS:
            if feat_name in df.columns:
                col_numeric = pd.to_numeric(df[feat_name], errors="coerce")
                self._imputation_medians[feat_name] = float(col_numeric.median()) if col_numeric.notna().any() else 0.0
            else:
                self._imputation_medians[feat_name] = 0.0

        # Build feature vectors
        records = []
        for _, row in df.iterrows():
            vec = self.compute(row.to_dict())
            records.append(vec)

        X = pd.DataFrame(records, columns=FEATURE_COLS)

        # Build target
        y = self._build_target(df)

        logger.info(
            f"fit_transform: {len(X)} samples, {X.shape[1]} features"
            + (f" [trimester={trimester_filter}]" if trimester_filter else "")
        )
        logger.info(f"Target distribution: {y.value_counts().to_dict()}")
        return X, y

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform df to feature matrix using fitted imputation medians.
        Must call fit_transform first (or load_imputation_stats).
        """
        records = [self.compute(row.to_dict()) for _, row in df.iterrows()]
        return pd.DataFrame(records, columns=FEATURE_COLS)

    def save_imputation_stats(self, path: Optional[str] = None) -> str:
        """Persist imputation medians to JSON for use at inference time."""
        save_path = path or str(MODELS_DIR / "saved_models" / "imputation_stats.json")
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(self._imputation_medians, f, indent=2)
        logger.info(f"Imputation stats saved → {save_path}")
        return save_path

    def load_imputation_stats(self, path: Optional[str] = None) -> None:
        """Load imputation medians (for inference — call after model load)."""
        load_path = path or str(MODELS_DIR / "saved_models" / "imputation_stats.json")
        if not Path(load_path).exists():
            logger.warning(f"No imputation stats at {load_path} — using 0.0 fallback")
            return
        with open(load_path, "r") as f:
            self._imputation_medians = json.load(f)
        logger.info(f"Imputation stats loaded from {load_path}")

    # ------------------------------------------------------------------ #
    # Internal utilities
    # ------------------------------------------------------------------ #

    def _coerce_float(self, val: Any) -> Optional[float]:
        if val is None:
            return None
        if isinstance(val, float) and np.isnan(val):
            return None
        try:
            result = float(str(val).replace("%", "").replace(",", "").strip())
            return result if np.isfinite(result) else None
        except (ValueError, TypeError):
            return None

    def _apply_missing_strategy(self, feat_name: str, meta: Dict) -> float:
        strategy = meta.get("missing_strategy", "zero_fill")
        if strategy == "zero_fill":
            return 0.0
        elif strategy == "median_impute":
            return self._imputation_medians.get(feat_name, 0.0)
        return 0.0

    def _build_target(self, df: pd.DataFrame) -> pd.Series:
        """
        Build the is_dropout target variable.
        Priority:
          1. Use `is_dropout` column if it exists and has two classes.
          2. Use rule-based proxy (bottom 20% attendance OR quiz score).
          3. Log error if only one class found.
        """
        if TARGET_COL in df.columns:
            y = pd.to_numeric(df[TARGET_COL], errors="coerce").fillna(0).astype(int)
            if y.nunique() == 2:
                return y.reset_index(drop=True)
            logger.warning(
                f"'{TARGET_COL}' column exists but has only {y.nunique()} class(es); "
                "falling back to rule-based proxy."
            )

        # Rule-based proxy
        att = pd.to_numeric(df.get("attendance_rate", pd.Series([np.nan] * len(df))), errors="coerce")
        quiz = pd.to_numeric(df.get("avg_quiz_score", pd.Series([np.nan] * len(df))), errors="coerce")
        logins = pd.to_numeric(df.get("num_logins", pd.Series([0] * len(df))), errors="coerce")

        att_thresh  = att.quantile(0.20)  if att.notna().sum() > 5 else 50.0
        quiz_thresh = quiz.quantile(0.20) if quiz.notna().sum() > 5 else 40.0

        is_risk = (
            (att < att_thresh)  |
            (quiz < quiz_thresh) |
            (logins < 5)
        ).astype(int)

        dropout_rate = is_risk.mean()
        if is_risk.nunique() == 1:
            logger.error(
                "Target variable has only one class — all students mapped to the same label. "
                "Provide labelled data or adjust thresholds."
            )
        elif dropout_rate > 0.9 or dropout_rate < 0.1:
            logger.warning(
                f"Target is heavily imbalanced (dropout_rate={dropout_rate:.1%}). "
                "Consider collecting more balanced data."
            )

        return is_risk.reset_index(drop=True)


# ── Dataset loading ──────────────────────────────────────────────────────────

MASTER_CSV = PROJECT_ROOT / "data" / "processed" / "clean_master_dataset.csv"


def load_master_dataset() -> pd.DataFrame:
    """
    Load the clean master dataset from disk.
    Skips metadata comment lines at the top of the CSV.
    Returns empty DataFrame if file does not exist.
    """
    if not MASTER_CSV.exists():
        logger.error(
            f"clean_master_dataset.csv not found at {MASTER_CSV}. "
            "Run data_ingestion.master_builder first."
        )
        return pd.DataFrame()

    with open(MASTER_CSV, "r", encoding="utf-8") as f:
        lines = f.readlines()
    skip_rows = sum(1 for line in lines if line.startswith("#"))

    df = pd.read_csv(MASTER_CSV, skiprows=skip_rows)
    logger.info(f"Loaded master dataset: {df.shape} (skip_rows={skip_rows})")
    return df


# ── Legacy compatibility shim ─────────────────────────────────────────────────
# Kept so that any existing imports of load_data_from_db / engineer_features
# don't immediately break, while logging a deprecation warning.

def load_data_from_db() -> pd.DataFrame:
    """
    DEPRECATED — use load_master_dataset() instead.
    Attempts to load from clean_master_dataset.csv; falls back to empty DataFrame.
    """
    logger.warning(
        "load_data_from_db() is deprecated. Use load_master_dataset() from feature_engineering.py "
        "or DatasetCache from data_ingestion.dataset_cache."
    )
    return load_master_dataset()


def engineer_features(raw_df: pd.DataFrame, semester: Optional[str] = None) -> pd.DataFrame:
    """
    DEPRECATED — use FeatureEngineer.fit_transform(df, trimester_filter) instead.
    Kept for backward compatibility.
    """
    logger.warning(
        "engineer_features() is deprecated. Use FeatureEngineer.fit_transform()."
    )
    if raw_df.empty:
        return pd.DataFrame()

    # Map legacy semester names to trimester codes
    trimester_map = {"Trimester 1": "T1", "Trimester 2": "T2", None: None}
    trim_code = trimester_map.get(semester, semester)

    fe = FeatureEngineer(fit=True)
    X, y = fe.fit_transform(raw_df, trimester_filter=trim_code)
    result = X.copy()
    result["is_dropout"] = y.values
    if "student_id" in raw_df.columns:
        result.insert(0, "student_id", raw_df["student_id"].values[: len(result)])
    return result


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = load_master_dataset()
    if df.empty:
        print("No master dataset found. Run: python -m data_ingestion.master_builder")
    else:
        fe = FeatureEngineer(fit=True)
        X, y = fe.fit_transform(df, trimester_filter="T1")
        print(f"Feature matrix (T1 train): {X.shape}")
        print(f"Feature columns: {FEATURE_COLS}")
        print(f"Target distribution: {y.value_counts().to_dict()}")
        print(X.describe())
