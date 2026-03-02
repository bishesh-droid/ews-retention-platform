"""
Normalizer — Data Standardisation
Handles all format conversions and normalisation needed before merging:
- Attendance: converts 0-1 fraction to 0-100 percentage
- Quiz / Assignment / Exam scores: scales to 0-100 uniformly
- Dates: parses to datetime, then to ISO strings
- Numeric coercion: safely converts string numerics
- Deduplication: removes identical rows and rows with duplicate student_id
- Missing values: NEVER blindly imputes; marks gaps with NaN; sentinel-fills only categoricals
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from data_ingestion.ingestion_logger import get_ingestion_logger

logger = get_ingestion_logger("normalizer")

# Columns that represent attendance and should live in [0, 100]
ATTENDANCE_COLUMNS = {"attendance_rate", "attendance_percentage"}

# Score columns; we normalise to 0-100 from whatever raw scale
SCORE_COLUMNS = {
    "quiz_score", "avg_quiz_score",
    "assignment_score", "assignment_avg",
    "exam_score", "midterm_score", "final_score",
}

# Columns that should be coerced to numeric
NUMERIC_COLUMNS = ATTENDANCE_COLUMNS | SCORE_COLUMNS | {
    "num_logins", "time_spent_minutes", "time_spent_hours",
    "content_completed", "content_required",
    "quiz_completed", "quiz_attempts",
    "sessions_attended", "total_sessions",
    "discussion_posts", "page_views", "week_number",
    "content_completion_rate", "quiz_completion_rate",
}

# Date columns
DATE_COLUMNS = {"submission_date", "deadline_date", "login_date", "metric_date"}

# Categorical sentinel for truly missing strings
MISSING_CATEGORICAL_SENTINEL = "UNKNOWN"


class DataNormalizer:
    """
    Normalises a single DataFrame after schema mapping.

    All operations log what they do and never raise silently.
    """

    def __init__(self, source_file: str = ""):
        self.source_file = source_file

    # ------------------------------------------------------------------ #
    # Main entry point
    # ------------------------------------------------------------------ #

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run the full normalization pipeline in a fixed order.
        Returns a cleaned copy; original is not modified.
        """
        df = df.copy()
        df = self._normalize_student_ids(df)
        df = self._coerce_numerics(df)
        df = self._normalize_attendance(df)
        df = self._normalize_scores(df)
        df = self._normalize_dates(df)
        df = self._deduplicate(df)
        df = self._handle_missing(df)
        return df

    # ------------------------------------------------------------------ #
    # Student ID
    # ------------------------------------------------------------------ #

    def _normalize_student_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        if "student_id" not in df.columns:
            return df
        before = df["student_id"].isna().sum()
        df["student_id"] = (
            df["student_id"]
            .astype(str)
            .str.strip()
            .str.lower()
            .replace({"nan": np.nan, "none": np.nan, "": np.nan})
        )
        after = df["student_id"].isna().sum()
        if after > before:
            logger.warning(
                f"student_id: {after - before} values became NaN after normalisation",
                source_file=self.source_file,
            )
        return df

    # ------------------------------------------------------------------ #
    # Numeric coercion
    # ------------------------------------------------------------------ #

    def _coerce_numerics(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in NUMERIC_COLUMNS:
            if col not in df.columns:
                continue
            original = df[col].copy()
            # Strip % signs and commas
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False).str.strip()
            df[col] = pd.to_numeric(df[col], errors="coerce")
            bad = df[col].isna().sum() - original.isna().sum()
            if bad > 0:
                logger.warning(
                    f"Column '{col}': {bad} values could not be converted to numeric → set to NaN",
                    source_file=self.source_file,
                )
        return df

    # ------------------------------------------------------------------ #
    # Attendance normalisation (fraction → percentage)
    # ------------------------------------------------------------------ #

    def _normalize_attendance(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in ATTENDANCE_COLUMNS:
            if col not in df.columns:
                continue
            series = pd.to_numeric(df[col], errors="coerce")
            non_null = series.dropna()
            if len(non_null) == 0:
                continue
            max_val, min_val = non_null.max(), non_null.min()

            if max_val <= 1.0 and min_val >= 0.0:
                # Legacy fraction format — convert to percentage
                df[col] = (series * 100).round(2)
                logger.info(
                    f"Attendance '{col}': converted from fraction [0,1] → percentage [0,100]",
                    source_file=self.source_file,
                )
            elif max_val > 100:
                # Cap at 100 (some sheets have attendance counts, not rates)
                # Try dividing by total_sessions if available
                if "total_sessions" in df.columns and not df["total_sessions"].isna().all():
                    total = pd.to_numeric(df["total_sessions"], errors="coerce")
                    computed = (series / total.replace(0, np.nan) * 100).clip(0, 100).round(2)
                    df[col] = computed
                    logger.info(
                        f"Attendance '{col}': derived from sessions_attended / total_sessions",
                        source_file=self.source_file,
                    )
                else:
                    df[col] = series.clip(0, 100)
                    logger.warning(
                        f"Attendance '{col}': values > 100 capped (max was {max_val})",
                        source_file=self.source_file,
                    )
            # else: already in [0,100] range — no action needed
        return df

    # ------------------------------------------------------------------ #
    # Score normalisation (raw → 0-100)
    # ------------------------------------------------------------------ #

    def _normalize_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in SCORE_COLUMNS:
            if col not in df.columns:
                continue
            series = pd.to_numeric(df[col], errors="coerce")
            non_null = series.dropna()
            if len(non_null) == 0:
                continue
            max_val = non_null.max()

            if max_val > 100 and max_val <= 200:
                # Assume out of 200 — common for doubled rubrics
                df[col] = (series / 200 * 100).clip(0, 100).round(2)
                logger.info(
                    f"Score '{col}': normalised from /200 → /100",
                    source_file=self.source_file,
                )
            elif max_val > 200:
                # Raw marks out of something else — normalise by observed max
                df[col] = (series / max_val * 100).clip(0, 100).round(2)
                logger.warning(
                    f"Score '{col}': normalised by observed max={max_val:.1f} → /100 (verify correctness)",
                    source_file=self.source_file,
                )
            elif max_val <= 1.0 and non_null.min() >= 0.0:
                # Fraction — convert to percentage
                df[col] = (series * 100).clip(0, 100).round(2)
                logger.info(
                    f"Score '{col}': converted from fraction → percentage",
                    source_file=self.source_file,
                )
        return df

    # ------------------------------------------------------------------ #
    # Date normalisation
    # ------------------------------------------------------------------ #

    def _normalize_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in DATE_COLUMNS:
            if col not in df.columns:
                continue
            try:
                parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
                failed = parsed.isna().sum() - df[col].isna().sum()
                df[col] = parsed.dt.strftime("%Y-%m-%d")
                if failed > 0:
                    logger.warning(
                        f"Date column '{col}': {failed} values failed to parse → NaN",
                        source_file=self.source_file,
                    )
            except Exception as exc:
                logger.error(
                    f"Date normalisation failed for '{col}': {exc}",
                    error_type="DATE_PARSE_ERROR",
                    source_file=self.source_file,
                )
        return df

    # ------------------------------------------------------------------ #
    # Deduplication
    # ------------------------------------------------------------------ #

    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        before = len(df)

        # 1. Remove fully identical rows
        df = df.drop_duplicates()

        # 2. Remove rows with duplicate student_id (within same trimester scope)
        key_cols = [c for c in ["student_id", "trimester", "week_number", "course_id"] if c in df.columns]
        if "student_id" in df.columns:
            df = df.drop_duplicates(subset=key_cols, keep="last")

        after = len(df)
        if before > after:
            logger.info(
                f"Deduplication: removed {before - after} duplicate rows ({before} → {after})",
                source_file=self.source_file,
            )
        return df

    # ------------------------------------------------------------------ #
    # Missing value handling — NO blind imputation
    # ------------------------------------------------------------------ #

    def _handle_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Policy:
        - Numeric columns: leave as NaN — downstream feature engineering
          decides how to handle per-feature.
        - Categorical / string columns: fill with MISSING_CATEGORICAL_SENTINEL
          only if the column is non-critical.
        - student_id: NEVER filled — rows with missing student_id are dropped.
        """
        # Drop rows with no student_id — cannot be attributed to anyone
        if "student_id" in df.columns:
            missing_ids = df["student_id"].isna().sum()
            if missing_ids > 0:
                logger.warning(
                    f"Dropping {missing_ids} rows with missing student_id",
                    source_file=self.source_file,
                )
                df = df.dropna(subset=["student_id"])

        # Categorical sentinel fills
        categorical_cols = [c for c in ["program", "trimester", "course_name", "enrollment_status"] if c in df.columns]
        for col in categorical_cols:
            null_count = df[col].isna().sum()
            if null_count > 0:
                df[col] = df[col].fillna(MISSING_CATEGORICAL_SENTINEL)
                logger.info(
                    f"Column '{col}': filled {null_count} NaN with '{MISSING_CATEGORICAL_SENTINEL}'",
                    source_file=self.source_file,
                )

        return df
