"""
Ingestion Logger
Structured, file-backed logging for all EWS pipeline stages.
Provides per-stage log context and a summary report at the end of each run.
"""
import logging
import json
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional


LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

INGESTION_LOG_FILE = LOG_DIR / "ingestion.log"
DISCREPANCY_LOG_FILE = LOG_DIR / "risk_discrepancy.log"


class IngestionLogger:
    """
    Centralised logger for the ingestion pipeline.

    Features
    --------
    - Writes human-readable lines to logs/ingestion.log
    - Maintains an in-memory event list for JSON summary export
    - Never raises — all log calls are safe
    """

    def __init__(self, stage: str = "pipeline"):
        self.stage = stage
        self._events: list[dict] = []
        self._error_counts: dict = defaultdict(int)

        # Root logger backed by a rotating file + console
        self._logger = logging.getLogger(f"ews.ingestion.{stage}")
        if not self._logger.handlers:
            self._logger.setLevel(logging.DEBUG)

            # Console handler
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            ch.setFormatter(logging.Formatter("[%(levelname)s] %(name)s — %(message)s"))
            self._logger.addHandler(ch)

            # File handler
            fh = logging.FileHandler(INGESTION_LOG_FILE, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S",
                )
            )
            self._logger.addHandler(fh)

    # ------------------------------------------------------------------ #
    # Public logging helpers
    # ------------------------------------------------------------------ #

    def info(self, message: str, source_file: str = "", row: int = 0):
        self._logger.info(message)
        self._record_event("INFO", message, source_file, row)

    def warning(self, message: str, source_file: str = "", row: int = 0):
        self._logger.warning(message)
        self._error_counts["WARNING"] += 1
        self._record_event("WARNING", message, source_file, row)

    def error(self, message: str, error_type: str = "GENERIC", source_file: str = "", row: int = 0):
        self._logger.error(message)
        self._error_counts[error_type] += 1
        self._record_event("ERROR", message, source_file, row, error_type=error_type)

    def critical(self, message: str, source_file: str = "", row: int = 0):
        self._logger.critical(message)
        self._error_counts["CRITICAL"] += 1
        self._record_event("CRITICAL", message, source_file, row)

    def schema_mismatch(self, source_file: str, expected: list, got: list):
        msg = (
            f"SCHEMA MISMATCH in '{source_file}': "
            f"missing={list(set(expected) - set(got))}, "
            f"extra={list(set(got) - set(expected))}"
        )
        self.error(msg, error_type="SCHEMA_MISMATCH", source_file=source_file)

    def feature_validation_error(self, student_id: str, feature: str, reason: str):
        msg = f"FEATURE_VALIDATION | student={student_id} | feature={feature} | reason={reason}"
        self.error(msg, error_type="FEATURE_VALIDATION", source_file="feature_engineering")

    def prediction_error(self, student_id: str, reason: str):
        msg = f"PREDICTION_ERROR | student={student_id} | reason={reason}"
        self.error(msg, error_type="PREDICTION", source_file="predict_model")

    # ------------------------------------------------------------------ #
    # Summary & export
    # ------------------------------------------------------------------ #

    def get_summary(self) -> dict:
        """Return a structured summary of this pipeline run."""
        return {
            "stage": self.stage,
            "generated_at": datetime.now().isoformat(),
            "total_events": len(self._events),
            "error_counts": dict(self._error_counts),
            "errors": [e for e in self._events if e["level"] in ("ERROR", "CRITICAL")],
        }

    def print_summary(self):
        self._logger.info("=" * 60)
        self._logger.info(f"INGESTION SUMMARY — stage={self.stage}")
        for error_type, count in self._error_counts.items():
            self._logger.info(f"  {error_type}: {count}")
        self._logger.info("=" * 60)

    def export_json_summary(self, output_path: Optional[str] = None) -> str:
        summary = self.get_summary()
        path = output_path or str(LOG_DIR / f"ingestion_summary_{self.stage}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        return path

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _record_event(
        self,
        level: str,
        message: str,
        source_file: str,
        row: int,
        error_type: str = "",
    ):
        self._events.append(
            {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "stage": self.stage,
                "source_file": source_file,
                "row": row,
                "message": message,
                "error_type": error_type,
            }
        )


# ------------------------------------------------------------------ #
# Module-level convenience factory
# ------------------------------------------------------------------ #

_loggers: dict[str, IngestionLogger] = {}


def get_ingestion_logger(stage: str = "pipeline") -> IngestionLogger:
    """Return (or create) a named logger for the given pipeline stage."""
    if stage not in _loggers:
        _loggers[stage] = IngestionLogger(stage)
    return _loggers[stage]
