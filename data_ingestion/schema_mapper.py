"""
Schema Mapper — Canonical Column Name Normaliser
Maps the wildly inconsistent column names found across EWS Excel datasets
to a single authoritative schema.

How it works
------------
1. Strip leading/trailing whitespace from all column names.
2. Lower-case normalise the header.
3. Apply the COLUMN_ALIASES registry for exact matches.
4. If no exact match, attempt a fuzzy word-overlap match against canonical names.
5. Columns that cannot be mapped stay as-is but are flagged in the rename log.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from data_ingestion.ingestion_logger import get_ingestion_logger

logger = get_ingestion_logger("schema_mapper")

# ---------------------------------------------------------------------------
# Central Alias Registry
# Format: "alias_variant" → "canonical_name"
# All keys MUST be lowercase-stripped.
# ---------------------------------------------------------------------------
COLUMN_ALIASES: Dict[str, str] = {
    # ── Student Identity ──────────────────────────────────────────────────
    "student id":                 "student_id",
    "student_id":                 "student_id",
    "id":                         "student_id",
    "studentid":                  "student_id",
    "student email":              "student_id",
    "studentemail":               "student_id",
    "email":                      "student_id",
    "email address":              "student_id",
    "username":                   "student_id",
    "user name":                  "student_id",
    "user":                       "student_id",
    "learner":                    "student_id",
    "learner email":              "student_id",
    "participant":                "student_id",

    # ── Student Name ─────────────────────────────────────────────────────
    "name":                       "student_name",
    "full name":                  "student_name",
    "student name":               "student_name",
    "studentname":                "student_name",
    "first name":                 "first_name",
    "firstname":                  "first_name",
    "last name":                  "last_name",
    "lastname":                   "last_name",
    "surname":                    "last_name",

    # ── Program / Course ─────────────────────────────────────────────────
    "program":                    "program",
    "programme":                  "program",
    "course":                     "course_name",
    "course name":                "course_name",
    "course title":               "course_name",
    "coursename":                 "course_name",
    "subject":                    "course_name",
    "course id":                  "course_id",
    "courseid":                   "course_id",

    # ── Trimester / Semester ─────────────────────────────────────────────
    "trimester":                  "trimester",
    "semester":                   "trimester",
    "term":                       "trimester",
    "period":                     "trimester",

    # ── Week ─────────────────────────────────────────────────────────────
    "week":                       "week_number",
    "week no":                    "week_number",
    "week number":                "week_number",
    "weekno":                     "week_number",
    "week #":                     "week_number",

    # ── Attendance ────────────────────────────────────────────────────────
    "attendance":                 "attendance_rate",
    "attendance %":               "attendance_rate",
    "attendance%":                "attendance_rate",
    "attendance percentage":      "attendance_rate",
    "attendancepct":              "attendance_rate",
    "attendance rate":            "attendance_rate",
    "total attendance":           "attendance_rate",
    "attendance_percentage":      "attendance_rate",
    "% attendance":               "attendance_rate",
    "sessions attended":          "sessions_attended",
    "total sessions":             "total_sessions",
    "sessions present":           "sessions_attended",
    "classes attended":           "sessions_attended",

    # ── Quiz Scores ───────────────────────────────────────────────────────
    "quiz score":                 "quiz_score",
    "quiz_score":                 "quiz_score",
    "quiz marks":                 "quiz_score",
    "quiz_marks":                 "quiz_score",
    "quiz result":                "quiz_score",
    "quiz grade":                 "quiz_score",
    "quiz avg":                   "avg_quiz_score",
    "quiz average":               "avg_quiz_score",
    "avg quiz":                   "avg_quiz_score",
    "average quiz score":         "avg_quiz_score",
    "quiz completion":            "quiz_completion_rate",
    "quiz completed":             "quiz_completed",
    "quiz attempts":              "quiz_attempts",
    "total quiz attempts":        "quiz_attempts",
    "quiz status":                "quiz_status",

    # ── Assignment ────────────────────────────────────────────────────────
    "assignment score":           "assignment_score",
    "assignment marks":           "assignment_score",
    "assignment avg":             "assignment_avg",
    "assignment average":         "assignment_avg",
    "average assignment":         "assignment_avg",
    "assignment grade":           "assignment_score",
    "assignment submitted":       "assignment_submitted",
    "submission status":          "submission_status",
    "late submission":            "late_submission",

    # ── Exam ─────────────────────────────────────────────────────────────
    "exam score":                 "exam_score",
    "exam marks":                 "exam_score",
    "exam grade":                 "exam_score",
    "exam percentage":            "exam_score",
    "exam result":                "exam_score",
    "midterm":                    "midterm_score",
    "midterm score":              "midterm_score",
    "final":                      "final_score",
    "final score":                "final_score",
    "final exam":                 "final_score",

    # ── Engagement / Usage ────────────────────────────────────────────────
    "logins":                     "num_logins",
    "login count":                "num_logins",
    "number of logins":           "num_logins",
    "no. of logins":              "num_logins",
    "total logins":               "num_logins",
    "page views":                 "page_views",
    "pageviews":                  "page_views",
    "content views":              "page_views",
    "time spent":                 "time_spent_minutes",
    "total time spent":           "time_spent_minutes",
    "time on platform":           "time_spent_minutes",
    "platform time":              "time_spent_minutes",
    "time spent (mins)":          "time_spent_minutes",
    "time spent (hours)":         "time_spent_hours",
    "discussion posts":           "discussion_posts",
    "forum posts":                "discussion_posts",
    "posts":                      "discussion_posts",

    # ── Content Completion ────────────────────────────────────────────────
    "content completed":          "content_completed",
    "content completion":         "content_completion_rate",
    "completion rate":            "content_completion_rate",
    "completion %":               "content_completion_rate",
    "content required":           "content_required",
    "modules completed":          "content_completed",

    # ── Risk / Label ─────────────────────────────────────────────────────
    "risk":                       "risk_label",
    "risk level":                 "risk_label",
    "risk category":              "risk_label",
    "dropout":                    "is_dropout",
    "at risk":                    "is_dropout",
    "status":                     "enrollment_status",
    "enrollment status":          "enrollment_status",
}


# ---------------------------------------------------------------------------
# Canonical columns with their required types (for downstream validation)
# ---------------------------------------------------------------------------
CANONICAL_TYPES: Dict[str, str] = {
    "student_id":              "email",
    "attendance_rate":         "percentage",
    "quiz_score":              "numeric",
    "avg_quiz_score":          "numeric",
    "assignment_score":        "numeric",
    "assignment_avg":          "numeric",
    "exam_score":              "numeric",
    "trimester":               "string",
    "week_number":             "integer",
    "num_logins":              "integer",
    "time_spent_minutes":      "numeric",
    "content_completion_rate": "percentage",
    "quiz_completion_rate":    "percentage",
    "content_completed":       "integer",
    "content_required":        "integer",
    "quiz_completed":          "integer",
    "quiz_attempts":           "integer",
    "is_dropout":              "boolean",
}


# ---------------------------------------------------------------------------
# SchemaMapper
# ---------------------------------------------------------------------------

class SchemaMapper:
    """
    Applies the COLUMN_ALIASES registry to a DataFrame's columns.

    Usage
    -----
    >>> mapper = SchemaMapper()
    >>> df, log = mapper.apply(df, source_file="Trimester1.xlsx")
    """

    def __init__(self, extra_aliases: Optional[Dict[str, str]] = None):
        self.aliases = dict(COLUMN_ALIASES)
        if extra_aliases:
            self.aliases.update({k.lower().strip(): v for k, v in extra_aliases.items()})

    # ------------------------------------------------------------------ #
    # Public
    # ------------------------------------------------------------------ #

    def apply(
        self, df: pd.DataFrame, source_file: str = ""
    ) -> Tuple[pd.DataFrame, List[dict]]:
        """
        Rename DataFrame columns to canonical names.

        Returns
        -------
        df : pd.DataFrame
            DataFrame with renamed columns.
        rename_log : list[dict]
            Audit log of every column rename.
        """
        rename_log: List[dict] = []
        new_columns: List[str] = []

        for original in df.columns:
            canonical, method = self._resolve(str(original))
            new_columns.append(canonical)

            if canonical != original:
                rename_log.append(
                    {
                        "original": original,
                        "canonical": canonical,
                        "method": method,
                        "source_file": source_file,
                    }
                )
                logger.info(
                    f"  RENAME [{method}] '{original}' → '{canonical}'",
                    source_file=source_file,
                )
            else:
                if canonical not in CANONICAL_TYPES:
                    logger.warning(
                        f"  UNMAPPED column: '{original}' — no canonical name found",
                        source_file=source_file,
                    )

        df = df.copy()
        df.columns = new_columns
        return df, rename_log

    def get_canonical_type(self, column: str) -> Optional[str]:
        """Return the expected type string for a canonical column name."""
        return CANONICAL_TYPES.get(column)

    def get_unmapped(self, df: pd.DataFrame) -> List[str]:
        """Return columns that are not in the canonical schema."""
        return [c for c in df.columns if c not in CANONICAL_TYPES]

    # ------------------------------------------------------------------ #
    # Internal resolution
    # ------------------------------------------------------------------ #

    def _resolve(self, original: str) -> Tuple[str, str]:
        """
        Resolve a column name to its canonical equivalent.

        Resolution order
        ----------------
        1. Exact match after strip + lowercase.
        2. Normalise (remove special chars, collapse whitespace) + exact match.
        3. Word-overlap fuzzy match.
        4. Return original unchanged.
        """
        normalised = original.strip().lower()

        # 1. Direct exact match
        if normalised in self.aliases:
            return self.aliases[normalised], "exact"

        # 2. Normalised match (strip punctuation, collapse spaces)
        cleaned = re.sub(r"[^a-z0-9\s]", " ", normalised)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned in self.aliases:
            return self.aliases[cleaned], "normalised"

        # 3. Word-overlap fuzzy match — any alias whose every word appears in column
        input_words = set(cleaned.split())
        best: Optional[Tuple[str, int]] = None  # (canonical, overlap_score)
        for alias, canonical in self.aliases.items():
            alias_words = set(alias.split())
            overlap = len(alias_words & input_words)
            if overlap == len(alias_words) and len(alias_words) > 0:
                if best is None or overlap > best[1]:
                    best = (canonical, overlap)
        if best:
            return best[0], "fuzzy"

        # 4. No match — keep original with underscores
        snake = re.sub(r"\s+", "_", cleaned)
        return snake if snake else original.strip(), "unchanged"
