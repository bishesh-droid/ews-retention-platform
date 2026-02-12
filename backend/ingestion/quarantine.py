"""
Quarantine Management
Store and track rejected rows with full context
"""
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import pandas as pd


@dataclass
class QuarantinedRow:
    """A single quarantined row with context"""
    source_file: str
    sheet_name: Optional[str]
    row_number: int
    quarantine_reason: str
    failed_column: str
    failure_message: str
    original_row: Dict
    quarantined_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class QuarantineSummary:
    """Summary statistics for quarantine"""
    total_quarantined: int
    by_file: Dict[str, int]
    by_reason: Dict[str, int]
    by_column: Dict[str, int]
    quarantine_rate: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


class QuarantineManager:
    """Manage rejected rows with full audit trail"""
    
    def __init__(self, quarantine_dir: str = "data/quarantine"):
        self.quarantine_dir = Path(quarantine_dir)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        self.quarantined_rows: List[QuarantinedRow] = []
        self.total_rows_processed = 0
    
    def quarantine_row(
        self,
        row_data: Dict,
        reason: str,
        source_file: str,
        row_number: int,
        failed_column: str = "",
        failure_message: str = "",
        sheet_name: Optional[str] = None
    ):
        """
        Add a row to quarantine
        
        Args:
            row_data: Original row data as dict
            reason: Category of failure (e.g., 'SCHEMA_VIOLATION', 'BOUNDS_ERROR')
            source_file: Source filename
            row_number: Row number in source file
            failed_column: Column that triggered failure
            failure_message: Detailed error message
            sheet_name: Sheet name (for Excel)
        """
        quarantined = QuarantinedRow(
            source_file=source_file,
            sheet_name=sheet_name,
            row_number=row_number,
            quarantine_reason=reason,
            failed_column=failed_column,
            failure_message=failure_message,
            original_row=row_data,
            quarantined_at=datetime.now().isoformat()
        )
        
        self.quarantined_rows.append(quarantined)
    
    def increment_processed(self, count: int = 1):
        """Track total rows processed"""
        self.total_rows_processed += count
    
    def get_summary(self) -> QuarantineSummary:
        """Generate quarantine summary"""
        by_file = {}
        by_reason = {}
        by_column = {}
        
        for row in self.quarantined_rows:
            # Count by file
            by_file[row.source_file] = by_file.get(row.source_file, 0) + 1
            
            # Count by reason
            by_reason[row.quarantine_reason] = by_reason.get(row.quarantine_reason, 0) + 1
            
            # Count by column
            if row.failed_column:
                by_column[row.failed_column] = by_column.get(row.failed_column, 0) + 1
        
        quarantine_rate = (len(self.quarantined_rows) / self.total_rows_processed * 100) if self.total_rows_processed > 0 else 0.0
        
        return QuarantineSummary(
            total_quarantined=len(self.quarantined_rows),
            by_file=by_file,
            by_reason=by_reason,
            by_column=by_column,
            quarantine_rate=round(quarantine_rate, 2)
        )
    
    def export_quarantine_report(self, source_file: str, format: str = 'csv') -> Optional[Path]:
        """
        Export quarantined rows for a specific file
        
        Args:
            source_file: Source filename to export
            format: 'csv' or 'json'
        
        Returns:
            Path to exported file
        """
        # Filter rows for this file
        file_rows = [r for r in self.quarantined_rows if r.source_file == source_file]
        
        if not file_rows:
            return None
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y-%m-%d')
        base_name = Path(source_file).stem
        
        if format == 'csv':
            output_path = self.quarantine_dir / f"{base_name}_rejected_{timestamp}.csv"
            self._export_csv(file_rows, output_path)
        else:
            output_path = self.quarantine_dir / f"{base_name}_errors_{timestamp}.jsonl"
            self._export_jsonl(file_rows, output_path)
        
        return output_path
    
    def _export_csv(self, rows: List[QuarantinedRow], output_path: Path):
        """Export as CSV"""
        if not rows:
            return
        
        # Collect all columns from original rows
        all_columns = set()
        for row in rows:
            all_columns.update(row.original_row.keys())
        
        all_columns = sorted(all_columns)
        
        with open(output_path, 'w', newline='') as f:
            # Add metadata columns
            fieldnames = ['row_number', 'quarantine_reason', 'failed_column', 'failure_message'] + all_columns
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for row in rows:
                row_dict = {
                    'row_number': row.row_number,
                    'quarantine_reason': row.quarantine_reason,
                    'failed_column': row.failed_column,
                    'failure_message': row.failure_message,
                    **row.original_row
                }
                writer.writerow(row_dict)
    
    def _export_jsonl(self, rows: List[QuarantinedRow], output_path: Path):
        """Export as JSON Lines"""
        with open(output_path, 'w') as f:
            for row in rows:
                f.write(json.dumps(row.to_dict()) + '\n')
    
    def print_summary(self):
        """Print formatted quarantine summary"""
        summary = self.get_summary()
        
        print("\n" + "="*80)
        print("QUARANTINE SUMMARY")
        print("="*80)
        print(f"Total Rows Processed: {self.total_rows_processed:,}")
        print(f"Rows Quarantined: {summary.total_quarantined:,}")
        print(f"Quarantine Rate: {summary.quarantine_rate:.2f}%")
        
        if summary.by_file:
            print("\nQuarantined by File:")
            for file, count in sorted(summary.by_file.items()):
                print(f"  {file}: {count}")
        
        if summary.by_reason:
            print("\nQuarantined by Reason:")
            for reason, count in sorted(summary.by_reason.items(), key=lambda x: x[1], reverse=True):
                print(f"  {reason}: {count}")
        
        if summary.by_column:
            print("\nTop Failed Columns:")
            top_columns = sorted(summary.by_column.items(), key=lambda x: x[1], reverse=True)[:10]
            for column, count in top_columns:
                print(f"  {column}: {count}")
        
        print("="*80)
    
    def clear(self):
        """Clear quarantine data"""
        self.quarantined_rows = []
        self.total_rows_processed = 0
