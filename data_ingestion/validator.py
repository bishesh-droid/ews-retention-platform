"""
Validator — Column-Level and Row-Level Data Validation
Checks for required columns, type integrity, student-ID format, and
numeric domain bounds. Never raises — returns a ValidationReport always.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from data_ingestion.ingestion_logger import get_ingestion_logger
from data_ingestion.schema_mapper import CANONICAL_TYPES

logger = get_ingestion_logger("validator")

EMAIL_PATTERN = re.compile(r"^[\w\.\+\-]+@[\w\.\-]+\.\w{2,}$", re.I)

# Required columns per data source type
REQUIRED_COLUMNS: Dict[str, List[str]] = {
    "trimester1_summary":        ["student_id", "attendance_rate"],
    "trimester2_summary":        ["student_id", "attendance_rate"],
    "attendance_quiz_assignment": ["student_id"],
    "engagement_analysis":       ["student_id"],
    "learner_usage_week3":       ["student_id"],
    "learner_usage_week5":       ["student_id"],
    "graded_quiz":               ["student_id"],
    "unknown":                   ["student_id"],
}

# Numeric bounds for canonical columns (min, max)
NUMERIC_BOUNDS: Dict[str, Tuple[float, float]] = {
    "attendance_rate":         (0.0, 100.0),
    "quiz_score":              (0.0, 100.0),
    "avg_quiz_score":          (0.0, 100.0),
    "assignment_score":        (0.0, 100.0),
    "assignment_avg":          (0.0, 100.0),
    "exam_score":              (0.0, 100.0),
    "content_completion_rate": (0.0, 100.0),
    "quiz_completion_rate":    (0.0, 100.0),
    "num_logins":              (0.0, 100_000.0),
    "week_number":             (1.0, 52.0),
}


@dataclass
class ValidationReport:
    source_file: str
    total_rows: int
    valid_rows: int = 0
    missing_required_columns: List[str] = field(default_factory=list)
    type_errors: List[dict] = field(default_factory=list)
    anomalies: List[dict] = field(default_factory=list)
    row_errors: List[dict] = field(default_factory=list)
    passed: bool = True

    @property
    def invalid_rows(self) -> int:
        return self.total_rows - self.valid_rows

    def add_anomaly(self, column: str, message: str, severity: str = "WARNING"):
        self.anomalies.append({"column": column, "message": message, "severity": severity})
        if severity == "ERROR":
            self.passed = False

    def add_row_error(self, row_idx: int, column: str, message: str):
        self.row_errors.append({"row": row_idx, "column": column, "message": message})

    def summary(self) -> str:
        lines = [
            f"Validation Report — {self.source_file}",
            f"  Total rows: {self.total_rows}",
            f"  Valid rows: {self.valid_rows}",
            f"  Invalid rows: {self.invalid_rows}",
            f"  Missing required cols: {self.missing_required_columns}",
            f"  Type errors: {len(self.type_errors)}",
            f"  Anomalies: {len(self.anomalies)}",
            f"  Passed: {self.passed}",
        ]
        return "\n".join(lines)


class DataValidator:
    """
    Row-level and column-level DataFrame validator.
    All methods are safe (no exceptions propagated to caller).
    """

    def __init__(self, file_type: str = "unknown", strict: bool = False):
        self.file_type = file_type
        self.strict = strict  # if True, invalid rows are excluded from output

    # ------------------------------------------------------------------ #
    # High-level entry point
    # ------------------------------------------------------------------ #

    def validate(self, df: pd.DataFrame, source_file: str = "") -> Tuple[pd.DataFrame, ValidationReport]:
        """
        Full validation pass over a DataFrame.

        Returns
        -------
        clean_df : pd.DataFrame
            Rows that passed all checks (may equal df if strict=False).
        report : ValidationReport
        """
        report = ValidationReport(source_file=source_file, total_rows=len(df))

        # Deduplicate column names first to avoid Series/DataFrame ambiguity
        if df.columns.duplicated().any():
            df = df.loc[:, ~df.columns.duplicated(keep="last")]

        # 1. Column-level checks
        self._check_required_columns(df, report)
        self._check_column_types(df, report)
        self._check_numeric_bounds(df, report)

        # 2. Row-level checks
        valid_mask = pd.Series([True] * len(df), index=df.index)

        for idx, row in df.iterrows():
            row_ok = self._validate_row(row, idx, report)
            if not row_ok:
                valid_mask.at[idx] = False

        report.valid_rows = int(valid_mask.sum())

        logger.info(
            f"Validation complete: {report.valid_rows}/{report.total_rows} valid rows",
            source_file=source_file,
        )

        clean_df = df[valid_mask] if self.strict else df
        return clean_df, report

    # ------------------------------------------------------------------ #
    # Column-level checks
    # ------------------------------------------------------------------ #

    def _check_required_columns(self, df: pd.DataFrame, report: ValidationReport):
        required = REQUIRED_COLUMNS.get(self.file_type, ["student_id"])
        missing = [c for c in required if c not in df.columns]
        if missing:
            report.missing_required_columns = missing
            report.passed = False
            logger.error(
                f"Missing required columns: {missing} in file_type='{self.file_type}'",
                error_type="MISSING_COLUMNS",
                source_file=report.source_file,
            )

    def _get_col_series(self, df: pd.DataFrame, col: str) -> pd.Series:
        """Safely extract a single column as a Series, even if duplicates exist."""
        result = df[col]
        if isinstance(result, pd.DataFrame):
            result = result.iloc[:, 0]
        return result

    def _check_column_types(self, df: pd.DataFrame, report: ValidationReport):
        """Check that canonical columns have valid types."""
        for col in df.columns:
            if col not in df.columns:  # guard after dedup
                continue
            expected_type = CANONICAL_TYPES.get(col)
            if not expected_type:
                continue

            try:
                col_series = self._get_col_series(df, col)
            except Exception:
                continue

            if expected_type == "percentage":
                non_null = pd.to_numeric(col_series, errors="coerce").dropna()
                if len(non_null) > 0:
                    pct_valid = ((non_null >= 0) & (non_null <= 100)).mean()
                    if pct_valid < 0.9:
                        report.type_errors.append(
                            {"column": col, "issue": f"< 90% of values in [0,100] range (found {pct_valid:.1%})"}
                        )
                        logger.warning(
                            f"Column '{col}': only {pct_valid:.1%} values in valid [0,100] range",
                            source_file=report.source_file,
                        )

            elif expected_type in ("numeric", "integer"):
                non_null = pd.to_numeric(col_series, errors="coerce")
                bad_count = non_null.isna().sum() - col_series.isna().sum()
                if bad_count > 0:
                    report.type_errors.append(
                        {"column": col, "issue": f"{bad_count} non-numeric values"}
                    )

            elif expected_type == "email":
                sample = col_series.dropna().astype(str).head(200)
                valid_ratio = sample.str.match(EMAIL_PATTERN).mean()
                if valid_ratio < 0.5:
                    report.type_errors.append(
                        {"column": col, "issue": f"Only {valid_ratio:.1%} match email pattern"}
                    )
                    logger.warning(
                        f"Column '{col}': low email validity ({valid_ratio:.1%})",
                        source_file=report.source_file,
                    )

    def _check_numeric_bounds(self, df: pd.DataFrame, report: ValidationReport):
        """Flag columns with values outside expected numeric bounds."""
        for col, (lo, hi) in NUMERIC_BOUNDS.items():
            if col not in df.columns:
                continue
            try:
                col_series = self._get_col_series(df, col)
                numeric = pd.to_numeric(col_series, errors="coerce")
            except Exception:
                continue
            out_of_bounds = ((numeric < lo) | (numeric > hi)).sum()
            if out_of_bounds > 0:
                report.add_anomaly(
                    col,
                    f"{out_of_bounds} values outside [{lo}, {hi}]",
                    severity="WARNING",
                )
                logger.warning(
                    f"Column '{col}': {out_of_bounds} values outside [{lo}, {hi}]",
                    source_file=report.source_file,
                )

    # ------------------------------------------------------------------ #
    # Row-level checks
    # ------------------------------------------------------------------ #

    def _validate_row(self, row: pd.Series, idx: int, report: ValidationReport) -> bool:
        """Return True if row passes all checks."""
        valid = True

        # Student ID must be present and look like an email
        if "student_id" in row.index:
            sid = str(row["student_id"]).strip()
            if not sid or sid.lower() in ("nan", "none", ""):
                report.add_row_error(idx, "student_id", "Missing student_id")
                valid = False
            elif not EMAIL_PATTERN.match(sid):
                # Not a hard failure — some systems use numeric IDs
                report.add_row_error(idx, "student_id", f"Non-email student_id: '{sid}'")
                # Don't fail row; just flag it

        # Check for Excel formula errors (#DIV/0!, #N/A, etc.)
        for col, val in row.items():
            val_str = str(val)
            if val_str.startswith("#"):
                report.add_row_error(idx, str(col), f"Excel error value: {val_str}")
                valid = False

        return valid
