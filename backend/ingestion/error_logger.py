"""
Error logging utility for ETL pipeline
"""

import json
import os
from datetime import datetime
from typing import Any, Dict


class IngestionErrorLogger:
    """Track and log data quality issues"""

    def __init__(self, log_file: str = "data/ingestion_errors.log"):
        self.log_file = log_file
        self.error_summary: Dict[str, Any] = {
            "total_rows_processed": 0,
            "rows_with_errors": 0,
            "errors_by_type": {},
            "errors_by_file": {},
        }

        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    def log_error(
        self,
        source_file: str,
        row_number: int,
        field: str,
        error_type: str,
        message: str,
    ):
        """Log a single error"""

        error_record = {
            "timestamp": datetime.now().isoformat(),
            "source_file": source_file,
            "row_number": row_number,
            "field": field,
            "error_type": error_type,
            "message": message,
        }

        # Write to log file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(error_record) + "\\n")

        # Update summary
        self.error_summary["rows_with_errors"] += 1
        self.error_summary["errors_by_type"][error_type] = (
            self.error_summary["errors_by_type"].get(error_type, 0) + 1
        )
        self.error_summary["errors_by_file"][source_file] = (
            self.error_summary["errors_by_file"].get(source_file, 0) + 1
        )

    def increment_processed(self, count: int = 1):
        """Increment processed row count"""
        self.error_summary["total_rows_processed"] += count

    def get_summary(self) -> Dict:
        """Return error summary for reporting"""
        summary = self.error_summary.copy()
        if summary["total_rows_processed"] > 0:
            summary["error_rate"] = (
                summary["rows_with_errors"] / summary["total_rows_processed"]
            ) * 100
        else:
            summary["error_rate"] = 0.0
        return summary

    def print_summary(self):
        """Print formatted error summary"""
        summary = self.get_summary()
        print("\\n" + "=" * 80)
        print("ETL ERROR SUMMARY")
        print("=" * 80)
        print(f"Total Rows Processed: {summary['total_rows_processed']:,}")
        print(f"Rows with Errors: {summary['rows_with_errors']:,}")
        print(f"Error Rate: {summary['error_rate']:.2f}%")

        if summary["errors_by_type"]:
            print("\\nErrors by Type:")
            for error_type, count in sorted(summary["errors_by_type"].items()):
                print(f"  {error_type}: {count}")

        if summary["errors_by_file"]:
            print("\\nErrors by File:")
            for file, count in sorted(summary["errors_by_file"].items()):
                print(f"  {file}: {count}")
