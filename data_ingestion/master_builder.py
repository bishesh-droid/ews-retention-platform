"""
Master Dataset Builder — ETL Pipeline Orchestrator
Orchestrates the full ingestion flow:
  Loader → SchemaMapper → Validator → Normalizer → Merger
Produces `data/processed/clean_master_dataset.csv` with:
  - One row per student per trimester
  - All derived features computed (attendance_rate, avg_quiz_score, etc.)
  - Metadata header row
  - Trimester labels (T1 = train, T2 = validation)
"""
from __future__ import annotations

import os
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from data_ingestion.ingestion_logger import get_ingestion_logger
from data_ingestion.loader import ExcelLoader, FileRecord, FileManifest
from data_ingestion.schema_mapper import SchemaMapper
from data_ingestion.validator import DataValidator
from data_ingestion.normalizer import DataNormalizer
from data_ingestion.merger import DataMerger

logger = get_ingestion_logger("master_builder")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
MASTER_CSV = DATA_PROCESSED / "clean_master_dataset.csv"


class MasterDatasetBuilder:
    """
    Orchestrates the full EWS data pipeline.

    Parameters
    ----------
    data_dir : str
        Path to raw Excel files.
    strict : bool
        If True, stop on critical validation failures.
    """

    def __init__(
        self,
        data_dir: str = str(DATA_RAW),
        strict: bool = False,
    ):
        self.data_dir = data_dir
        self.strict = strict
        self.loader = ExcelLoader(data_dir=data_dir, strict_duplicates=True)
        self.mapper = SchemaMapper()
        self.merger = DataMerger(allow_partial=not strict)
        DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Main entry point
    # ------------------------------------------------------------------ #

    def run(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Execute the full pipeline.

        Returns
        -------
        train_df : pd.DataFrame  — Trimester 1 (training set)
        val_df   : pd.DataFrame  — Trimester 2 (validation set)
        """
        logger.info("=" * 70)
        logger.info("MasterDatasetBuilder — starting pipeline run")
        logger.info(f"  data_dir  : {self.data_dir}")
        logger.info(f"  output    : {MASTER_CSV}")
        logger.info("=" * 70)
        start = datetime.now()

        # ── Phase 1: Discover files ────────────────────────────────────
        manifest = self.loader.load_manifest()
        if not manifest:
            logger.error("No files found in data directory. Aborting.", error_type="NO_FILES")
            return pd.DataFrame(), pd.DataFrame()

        # ── Phase 2: Load & normalise each source ─────────────────────
        # The engagement_analysis file contains per-student data with Username (email).
        # T1/T2 summary files are COURSE-LEVEL aggregate tables — not directly per-student.
        # We treat engagement_analysis as the primary per-student source, filtered by semester.
        engagement_df = self._load_and_normalise(manifest, "engagement_analysis")

        # Split engagement into T1/T2 based on semester_name / trimester column
        t1_df = self._split_by_trimester(engagement_df, "T1") if engagement_df is not None else None
        t2_df = self._split_by_trimester(engagement_df, "T2") if engagement_df is not None else None

        # Fall back to dedicated summary files if engagement_analysis lacks trimester info
        if t1_df is None or t1_df.empty:
            t1_df = self._load_and_normalise(manifest, "trimester1_summary", trimester="T1")
        if t2_df is None or t2_df.empty:
            t2_df = self._load_and_normalise(manifest, "trimester2_summary", trimester="T2")

        weekly_dfs = []
        quiz_df   = self._load_and_normalise(manifest, "graded_quiz")
        att_df    = self._load_and_normalise(manifest, "attendance_quiz_assignment")
        usage_dfs = [
            self._load_and_normalise(manifest, "learner_usage_week3"),
            self._load_and_normalise(manifest, "learner_usage_week5"),
        ]
        usage_dfs = [u for u in usage_dfs if u is not None and not u.empty]

        # Merge usage into weekly list
        all_weekly = weekly_dfs + usage_dfs

        # ── Phase 3: Merge into master ─────────────────────────────────
        train_df, val_df = self.merger.build(
            trimester1_df=t1_df,
            trimester2_df=t2_df,
            weekly_dfs=all_weekly if all_weekly else None,
            quiz_df=quiz_df,
            attendance_df=att_df,
        )

        # ── Phase 4: Derive master-level features ──────────────────────
        train_df = self._compute_derived_features(train_df)
        val_df   = self._compute_derived_features(val_df)

        # ── Phase 5: Save master CSV ───────────────────────────────────
        master_df = pd.concat([train_df, val_df], ignore_index=True, sort=False)
        self._save_master_csv(master_df)

        duration = (datetime.now() - start).total_seconds()
        logger.info(f"Pipeline complete in {duration:.1f}s → {len(master_df)} total rows")
        logger.print_summary()

        return train_df, val_df

    # ------------------------------------------------------------------ #
    # Load helpers
    # ------------------------------------------------------------------ #

    def _load_and_normalise(
        self,
        manifest: FileManifest,
        file_type: str,
        trimester: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """Load canonical record for a given type, map schema, validate, normalise."""
        record = self.loader.get_canonical(manifest, file_type)
        if record is None:
            logger.warning(f"No file found for type='{file_type}'")
            return None

        frames = self.loader.load_dataframe(record)
        if not frames:
            return None

        combined_sheets: List[pd.DataFrame] = []
        for sheet_name, df in frames.items():
            if df.empty:
                continue

            # Map column names
            df, rename_log = self.mapper.apply(df, source_file=record.filename)

            # Validate
            validator = DataValidator(file_type=file_type, strict=self.strict)
            df, report = validator.validate(df, source_file=record.filename)
            logger.info(report.summary(), source_file=record.filename)

            if not report.passed and self.strict:
                logger.error(
                    f"Validation FAILED for {record.filename} / {sheet_name} — skipping in strict mode",
                    error_type="VALIDATION_FAILED",
                    source_file=record.filename,
                )
                continue

            # Normalise
            normalizer = DataNormalizer(source_file=record.filename)
            df = normalizer.normalize(df)

            if trimester and "trimester" not in df.columns:
                df["trimester"] = trimester

            if not df.empty:
                combined_sheets.append(df)

        if not combined_sheets:
            return None

        result = pd.concat(combined_sheets, ignore_index=True, sort=False)
        # Final dedup across sheets
        if "student_id" in result.columns:
            result = result.drop_duplicates(
                subset=[c for c in ["student_id", "trimester", "week_number"] if c in result.columns],
                keep="last",
            )
        return result

    def _split_by_trimester(self, df: Optional[pd.DataFrame], trimester: str) -> Optional[pd.DataFrame]:
        """Filter a DataFrame by trimester column if it exists."""
        if df is None or df.empty:
            return None
        
        # Check for trimester / semester columns
        for col in ("trimester", "semester_name", "semester_code"):
            if col not in df.columns:
                continue
            col_vals = df[col].astype(str).str.lower()
            t1_patterns = ["t1", "trimester 1", "trim 1", "trimester1", "1"]
            t2_patterns = ["t2", "trimester 2", "trim 2", "trimester2", "2"]
            if trimester == "T1":
                mask = col_vals.isin(t1_patterns) | col_vals.str.contains("trimester.?1|t1", regex=True, na=False)
            else:
                mask = col_vals.isin(t2_patterns) | col_vals.str.contains("trimester.?2|t2", regex=True, na=False)
            filtered = df[mask].copy()
            if not filtered.empty:
                filtered["trimester"] = trimester
                return filtered
        
        # No trimester column — return as-is with label
        result = df.copy()
        result["trimester"] = trimester
        return result

    def _load_weekly_sources(self, manifest: FileManifest) -> List[pd.DataFrame]:
        """Load engagement analysis source files."""
        weekly: List[pd.DataFrame] = []
        for ftype in ("engagement_analysis",):
            df = self._load_and_normalise(manifest, ftype)
            if df is not None and not df.empty:
                weekly.append(df)
        return weekly

    # ------------------------------------------------------------------ #
    # Derived feature computation (master-level)
    # ------------------------------------------------------------------ #

    def _compute_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all features that require the full merged dataset.
        All computations are safe — missing inputs produce NaN, not errors.
        """
        if df.empty:
            return df

        df = df.copy()

        # 1. attendance_rate — already normalised, just ensure it exists
        if "attendance_rate" not in df.columns:
            if "sessions_attended" in df.columns and "total_sessions" in df.columns:
                total = pd.to_numeric(df["total_sessions"], errors="coerce")
                attended = pd.to_numeric(df["sessions_attended"], errors="coerce")
                df["attendance_rate"] = (attended / total.replace(0, np.nan) * 100).clip(0, 100)
            else:
                df["attendance_rate"] = np.nan

        # 2. avg_quiz_score — already aggregated; just fill if missing
        if "avg_quiz_score" not in df.columns:
            df["avg_quiz_score"] = np.nan

        # 3. assignment_avg
        if "assignment_avg" not in df.columns:
            if "assignment_score" in df.columns:
                df["assignment_avg"] = pd.to_numeric(df["assignment_score"], errors="coerce")
            else:
                df["assignment_avg"] = np.nan

        # 4. performance_trend — linear regression slope of [attendance, quiz, assignment]
        df["performance_trend"] = df.apply(self._compute_trend, axis=1)

        # 5. submission_delay_avg — from late_submission flag as proxy
        if "late_submission" in df.columns:
            df["submission_delay_avg"] = pd.to_numeric(df["late_submission"], errors="coerce").fillna(0)
        else:
            df["submission_delay_avg"] = np.nan

        # 6. engagement_frequency, engagement_decay, activity_variance — from merger
        for feat in ("engagement_frequency", "engagement_decay", "activity_variance"):
            if feat not in df.columns:
                df[feat] = np.nan

        return df

    def _compute_trend(self, row: pd.Series) -> float:
        """
        Compute a simple performance trend score as the mean slope
        of [attendance_rate, avg_quiz_score, assignment_avg].
        Returns positive if improving, negative if declining.
        """
        values = []
        for col in ("attendance_rate", "avg_quiz_score", "assignment_avg"):
            v = pd.to_numeric(row.get(col, np.nan), errors="coerce")
            if pd.notna(v):
                values.append(v)

        if len(values) < 2:
            return np.nan

        # Slope of naive enumeration
        x = np.arange(len(values), dtype=float)
        y = np.array(values, dtype=float)
        if np.std(y) == 0:
            return 0.0
        slope = np.polyfit(x, y, 1)[0]
        return round(float(slope), 4)

    # ------------------------------------------------------------------ #
    # Save master CSV
    # ------------------------------------------------------------------ #

    def _save_master_csv(self, df: pd.DataFrame):
        """Save master dataset to CSV with a metadata comment header."""
        # Safe trimester counting — df['trimester'] may not exist
        def _count_trimester(t: str) -> int:
            if "trimester" not in df.columns:
                return 0
            return int((df["trimester"] == t).sum())

        meta_lines = [
            f"# EWS Clean Master Dataset",
            f"# Generated: {datetime.now().isoformat()}",
            f"# Rows: {len(df)}",
            f"# Columns: {len(df.columns)}",
            f"# T1 rows (train): {_count_trimester('T1')}",
            f"# T2 rows (val):   {_count_trimester('T2')}",
            f"# Unique students: {df['student_id'].nunique() if 'student_id' in df.columns else 'N/A'}",
        ]

        with open(MASTER_CSV, "w", newline="", encoding="utf-8") as f:
            for line in meta_lines:
                f.write(line + "\n")
            df.to_csv(f, index=False)

        logger.info(f"Master dataset saved → {MASTER_CSV} ({len(df)} rows)")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    builder = MasterDatasetBuilder()
    train, val = builder.run()
    print(f"\nTrain set: {train.shape}")
    print(f"Val set:   {val.shape}")
    if not train.empty:
        print("\nTrain columns:", train.columns.tolist())
        print(train.head(3))
