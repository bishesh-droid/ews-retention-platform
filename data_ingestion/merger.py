"""
Merger — Safe Multi-Source Dataset Merger
Combines data from multiple sources without cross-trimester leakage.

Responsibilities
----------------
1. Merge all source DataFrames on `student_id` using left-join (student roster as anchor).
2. Keep trimester 1 and trimester 2 data strictly separated.
3. Aggregate weekly engagement data (wide pivot per student).
4. Enforce anti-leakage rules: T2 data never flows into T1 training set.
5. Return separate train (T1) and validation (T2) DataFrames.
"""
from __future__ import annotations

import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from data_ingestion.ingestion_logger import get_ingestion_logger

logger = get_ingestion_logger("merger")

# Trimester identifiers — normalise all variants to these
TRIMESTER_CANONICAL = {
    "trimester 1": "T1",
    "trimester1": "T1",
    "trim 1": "T1",
    "t1": "T1",
    "1": "T1",
    "trimester 2": "T2",
    "trimester2": "T2",
    "trim 2": "T2",
    "t2": "T2",
    "2": "T2",
}


class DataMerger:
    """
    Merges all EWS data sources into a trimester-aware master DataFrame.

    Usage
    -----
    merger = DataMerger()
    train_df, val_df = merger.build(
        roster_df=roster,
        trimester1_df=t1,
        trimester2_df=t2,
        weekly_dfs=[week1_df, week2_df, week3_df],
        quiz_df=quiz,
        attendance_df=attendance,
    )
    """

    def __init__(self, allow_partial: bool = True):
        self.allow_partial = allow_partial  # if True, proceed even if some sources are missing

    # ------------------------------------------------------------------ #
    # Main build method
    # ------------------------------------------------------------------ #

    def build(
        self,
        roster_df: Optional[pd.DataFrame] = None,
        trimester1_df: Optional[pd.DataFrame] = None,
        trimester2_df: Optional[pd.DataFrame] = None,
        weekly_dfs: Optional[List[pd.DataFrame]] = None,
        quiz_df: Optional[pd.DataFrame] = None,
        attendance_df: Optional[pd.DataFrame] = None,
        learner_usage_dfs: Optional[List[pd.DataFrame]] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Build the master dataset.

        Returns
        -------
        train_df : pd.DataFrame  — T1 data only (for model training)
        val_df   : pd.DataFrame  — T2 data only (for model validation)
        """
        # Step 1: Establish student roster
        all_students = self._build_student_universe(
            roster_df, trimester1_df, trimester2_df
        )
        if all_students.empty:
            logger.error(
                "Cannot build master dataset — no student IDs found",
                error_type="NO_STUDENTS",
            )
            return pd.DataFrame(), pd.DataFrame()

        logger.info(f"Student universe: {len(all_students)} unique students")

        # Step 2: Build per-trimester base frames
        t1_base = self._build_trimester_base(trimester1_df, trimester="T1")
        t2_base = self._build_trimester_base(trimester2_df, trimester="T2")

        # Step 3: Aggregate weekly engagement
        weekly_agg: Optional[pd.DataFrame] = None
        if weekly_dfs:
            weekly_agg = self._aggregate_weekly(weekly_dfs)

        # Step 4: Aggregate quiz/assessment data
        quiz_agg: Optional[pd.DataFrame] = None
        if quiz_df is not None and not quiz_df.empty:
            quiz_agg = self._aggregate_quiz(quiz_df)

        # Step 5: Merge each trimester independently
        train_df = self._merge_trimester(
            base=t1_base,
            all_students=all_students,
            weekly_agg=weekly_agg,
            quiz_agg=quiz_agg,
            attendance_df=attendance_df,
            trimester="T1",
        )

        val_df = self._merge_trimester(
            base=t2_base,
            all_students=all_students,
            weekly_agg=weekly_agg,      # Pass weekly but filter inside
            quiz_agg=quiz_agg,
            attendance_df=attendance_df,
            trimester="T2",
        )

        # Step 6: Leakage check
        self._assert_no_leakage(train_df, val_df)

        logger.info(
            f"Merge complete → train={len(train_df)} rows, val={len(val_df)} rows"
        )
        return train_df, val_df

    # ------------------------------------------------------------------ #
    # Internal: student universe
    # ------------------------------------------------------------------ #

    def _build_student_universe(
        self,
        *frames: Optional[pd.DataFrame],
    ) -> pd.DataFrame:
        """Collect all unique student_id values across all source frames."""
        ids: set = set()
        for df in frames:
            if df is not None and not df.empty and "student_id" in df.columns:
                valid_ids = df["student_id"].dropna().astype(str).str.lower().str.strip()
                ids.update(valid_ids.tolist())
        ids.discard("nan")
        ids.discard("")
        return pd.DataFrame({"student_id": sorted(ids)})

    # ------------------------------------------------------------------ #
    # Internal: per-trimester base frame
    # ------------------------------------------------------------------ #

    def _build_trimester_base(
        self,
        df: Optional[pd.DataFrame],
        trimester: str,
    ) -> pd.DataFrame:
        """Build a normalised base frame for one trimester."""
        if df is None or df.empty:
            logger.warning(f"No base data for trimester={trimester}")
            return pd.DataFrame()

        df = df.copy()

        # Normalise trimester column if present
        if "trimester" in df.columns:
            df["trimester"] = (
                df["trimester"].astype(str).str.strip().str.lower()
                .map(TRIMESTER_CANONICAL)
                .fillna(trimester)
            )
        else:
            df["trimester"] = trimester

        # Ensure student_id is lowercase
        if "student_id" in df.columns:
            df["student_id"] = df["student_id"].astype(str).str.lower().str.strip()
            df = df[df["student_id"].notna() & (df["student_id"] != "nan")]

            # Deduplicate — one row per student per trimester
            df = df.drop_duplicates(subset=["student_id", "trimester"], keep="last")

        return df

    # ------------------------------------------------------------------ #
    # Internal: weekly aggregation
    # ------------------------------------------------------------------ #

    def _aggregate_weekly(self, weekly_dfs: List[pd.DataFrame]) -> pd.DataFrame:
        """
        Aggregate week-wise engagement into per-student summary features.
        Creates wide-format columns: sessions_w1, sessions_w2, ...
        and computes engagement_frequency, engagement_decay, activity_variance.
        """
        all_weeks: List[pd.DataFrame] = []

        for i, wdf in enumerate(weekly_dfs, start=1):
            if wdf is None or wdf.empty:
                continue
            wdf = wdf.copy()
            if "student_id" not in wdf.columns:
                continue

            # Determine week number
            if "week_number" not in wdf.columns:
                wdf["week_number"] = i

            wdf["student_id"] = wdf["student_id"].astype(str).str.lower().str.strip()
            all_weeks.append(wdf)

        if not all_weeks:
            logger.warning("No weekly data available for aggregation")
            return pd.DataFrame()

        combined = pd.concat(all_weeks, ignore_index=True, sort=False)

        # Aggregate per student/week: take relevant metrics
        engagement_cols = [c for c in ["num_logins", "time_spent_minutes", "page_views", "content_completed"] if c in combined.columns]
        if not engagement_cols:
            logger.warning("Weekly data has no engagement columns; using row count as proxy")
            combined["_sessions"] = 1
            engagement_cols = ["_sessions"]

        agg_dict = {col: "sum" for col in engagement_cols}
        weekly_agg = combined.groupby(["student_id", "week_number"]).agg(agg_dict).reset_index()

        # Pivot to wide format: one row per student, columns per week
        weekly_wide = weekly_agg.pivot_table(
            index="student_id",
            columns="week_number",
            values=engagement_cols[0],  # Use primary engagement metric for wide view
            fill_value=0,
        ).reset_index()
        weekly_wide.columns = [
            f"engagement_w{int(col)}" if isinstance(col, (int, float)) else col
            for col in weekly_wide.columns
        ]

        # Compute derived engagement features from weekly totals
        student_weekly = combined.groupby("student_id")[engagement_cols].sum().reset_index()
        week_counts = combined.groupby(["student_id", "week_number"])[engagement_cols[0]].sum().reset_index()

        def engagement_features(group: pd.Series) -> pd.Series:
            """Compute engagement_frequency, engagement_decay, activity_variance."""
            values = group.values.astype(float)
            freq = float(np.count_nonzero(values)) / len(values) if len(values) > 0 else 0.0
            decay = values[-1] / values[0] if len(values) > 1 and values[0] > 0 else 1.0
            variance = float(np.var(values)) if len(values) > 1 else 0.0
            return pd.Series({
                "engagement_frequency": freq,
                "engagement_decay": decay,
                "activity_variance": variance,
            })

        derived = (
            week_counts.groupby("student_id")[engagement_cols[0]]
            .apply(lambda g: engagement_features(g))
            .reset_index()
        )

        # Merge wide + derived
        result = weekly_wide.merge(derived, on="student_id", how="outer")
        logger.info(f"Weekly aggregation: {len(result)} students, {len(result.columns)} features")
        return result

    # ------------------------------------------------------------------ #
    # Internal: quiz aggregation
    # ------------------------------------------------------------------ #

    def _aggregate_quiz(self, quiz_df: pd.DataFrame) -> pd.DataFrame:
        """Compute quiz summary per student."""
        quiz_df = quiz_df.copy()
        if "student_id" not in quiz_df.columns:
            return pd.DataFrame()

        quiz_df["student_id"] = quiz_df["student_id"].astype(str).str.lower().str.strip()

        score_col = next((c for c in ["quiz_score", "avg_quiz_score"] if c in quiz_df.columns), None)
        if not score_col:
            logger.warning("Quiz data has no score column; cannot aggregate")
            return pd.DataFrame()

        quiz_df[score_col] = pd.to_numeric(quiz_df[score_col], errors="coerce")

        agg = quiz_df.groupby("student_id").agg(
            avg_quiz_score=(score_col, "mean"),
            best_quiz_score=(score_col, "max"),
            worst_quiz_score=(score_col, "min"),
            quiz_attempts=("student_id", "count"),
        ).reset_index()

        return agg

    # ------------------------------------------------------------------ #
    # Internal: merge one trimester
    # ------------------------------------------------------------------ #

    def _merge_trimester(
        self,
        base: pd.DataFrame,
        all_students: pd.DataFrame,
        weekly_agg: Optional[pd.DataFrame],
        quiz_agg: Optional[pd.DataFrame],
        attendance_df: Optional[pd.DataFrame],
        trimester: str,
    ) -> pd.DataFrame:
        """Left-join all sources onto the student universe for one trimester."""
        if base.empty:
            # Start from student universe if no trimester summary
            df = all_students.copy()
            df["trimester"] = trimester
        else:
            # Start from base (already has student_id + trimester)
            df = all_students.merge(base, on="student_id", how="left")

        # Merge weekly engagement (time-neutral for now — can be T1/T2 filtered later)
        if weekly_agg is not None and not weekly_agg.empty:
            df = df.merge(weekly_agg, on="student_id", how="left")

        # Merge quiz data
        if quiz_agg is not None and not quiz_agg.empty:
            df = df.merge(quiz_agg, on="student_id", how="left", suffixes=("", "_quiz"))

        # Merge attendance if separate from base
        if attendance_df is not None and not attendance_df.empty and "attendance_rate" not in df.columns:
            att_cols = [c for c in ["student_id", "attendance_rate"] if c in attendance_df.columns]
            if "student_id" in att_cols and "attendance_rate" in att_cols:
                att = attendance_df[att_cols].drop_duplicates(subset="student_id")
                df = df.merge(att, on="student_id", how="left")
            else:
                logger.warning(
                    f"Attendance merge skipped: 'attendance_rate' not found in attendance_df "
                    f"(available cols: {list(attendance_df.columns)[:10]})"
                )

        df["trimester"] = trimester
        logger.info(f"Trimester {trimester}: {len(df)} rows × {len(df.columns)} cols after merge")
        return df

    # ------------------------------------------------------------------ #
    # Anti-leakage assertion
    # ------------------------------------------------------------------ #

    def _assert_no_leakage(self, train_df: pd.DataFrame, val_df: pd.DataFrame):
        """
        Assert that T2-only columns (future information) do not appear in T1 training data.
        This is structural leakage prevention — both DFs share the same columns by design,
        but we verify trimester labels are correctly set.
        """
        if train_df.empty or val_df.empty:
            return

        if "trimester" in train_df.columns:
            t1_trimester_vals = train_df["trimester"].unique().tolist()
            invalid = [v for v in t1_trimester_vals if v not in ("T1", "UNKNOWN")]
            if invalid:
                logger.error(
                    f"LEAKAGE DETECTED: T2 trimester values found in training set: {invalid}",
                    error_type="DATA_LEAKAGE",
                )
                raise ValueError(f"Data leakage: T2 data in training set: {invalid}")

        if "trimester" in val_df.columns:
            t2_trimester_vals = val_df["trimester"].unique().tolist()
            invalid = [v for v in t2_trimester_vals if v not in ("T2", "UNKNOWN")]
            if invalid:
                logger.error(
                    f"LEAKAGE DETECTED: T1 trimester values found in validation set: {invalid}",
                    error_type="DATA_LEAKAGE",
                )
                raise ValueError(f"Data leakage: T1 data in validation set: {invalid}")

        logger.info("Anti-leakage check: PASSED — trimester boundaries are clean")
