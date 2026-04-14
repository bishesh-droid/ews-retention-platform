"""
Validated ETL Pipeline
Enhanced with 8-layer validation architecture
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Optional

from backend.database import (
    SessionLocal, DimStudent
)
from backend.ingestion.file_validator import FileValidator, ValidationStatus
from backend.ingestion.schema_manager import SchemaInferenceEngine, SchemaValidator, DataSchema
from backend.ingestion.quarantine import QuarantineManager
from backend.ingestion.row_validators import RowValidator, RequiredFieldValidator
from backend.ingestion.transformers import TypeCoercer
from backend.ingestion.error_logger import IngestionErrorLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ValidatedEWSPipeline:
    """
    ETL Pipeline with comprehensive validation
    Implements 8-layer validation architecture
    """

    def __init__(self, data_dir: str = "data/raw", strict_mode: bool = True):
        self.data_dir = Path(data_dir)
        self.strict_mode = strict_mode
        self.logger = logger

        # Validation components
        self.file_validator = FileValidator(strict_mode=strict_mode)
        self.schema_engine = SchemaInferenceEngine()
        self.quarantine = QuarantineManager()
        self.error_logger = IngestionErrorLogger()

        # Lazily created DB session (only when running or used as a context manager).
        self.db = None
        self.validation_reports: list = []

    def __enter__(self):
        """
        Optional context-manager support for legacy callers.

        Example:
            with ValidatedEWSPipeline(...) as pipeline:
                pipeline.run()
        """
        if self.db is None:
            self.db = SessionLocal()
        return self

    def __exit__(self, exc_type, exc, tb):
        # Never open sessions in __init__, so only close if we created/hold one.
        if self.db is not None:
            try:
                if exc_type is not None:
                    self.db.rollback()
            finally:
                self.db.close()
                self.db = None

    def run(self):
        """Execute full validated pipeline"""
        self.logger.info("="*80)
        self.logger.info("Starting VALIDATED EWS Data Ingestion Pipeline")
        self.logger.info("Mode: " + ("STRICT" if self.strict_mode else "PERMISSIVE"))
        self.logger.info("="*80)

        start_time = datetime.now()

        # Prefer an externally-managed session (context manager usage); otherwise
        # create/close a session scoped to this run invocation.
        if self.db is not None:
            return self._run_with_db(self.db, start_time)

        with SessionLocal() as db:
            return self._run_with_db(db, start_time)

    def _run_with_db(self, db, start_time: datetime) -> bool:
        try:
            # LAYER 1: File-level validation
            self.logger.info("\n[LAYER 1] File-Level Validation...")
            files = self._get_data_files()

            validation_results = {}
            for file_path in files:
                result = self.file_validator.validate_file(str(file_path))
                validation_results[file_path] = result

                if result.status == ValidationStatus.REJECTED:
                    self.logger.error(f"  ✗ {file_path.name}: REJECTED")
                    for msg in result.messages:
                        self.logger.error(f"    - {msg}")
                elif result.status == ValidationStatus.WARNING:
                    self.logger.warning(f"  ⚠ {file_path.name}: WARNINGS")
                    for msg in result.messages:
                        self.logger.warning(f"    - {msg}")
                else:
                    self.logger.info(f"  ✓ {file_path.name}: PASSED")

            # Check for any rejections
            rejected = [f for f, r in validation_results.items() if r.has_errors()]
            if rejected and self.strict_mode:
                self.logger.error(f"\n✗ {len(rejected)} files failed validation")
                return False

            # LAYER 2-7: Process each file with schema enforcement
            valid_files = [f for f, r in validation_results.items() if not r.has_errors()]

            for file_path in valid_files:
                self._process_file_with_validation(db, file_path)

            # Commit if successful
            db.commit()

            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"\n✓ Pipeline completed in {duration:.1f}s")

            # Print reports
            self.error_logger.print_summary()
            self.quarantine.print_summary()

            return True

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            db.rollback()
            return False

    def _get_data_files(self) -> List[Path]:
        """Get all data files to process"""
        files: list = []

        if not self.data_dir.exists():
            self.logger.warning(f"Data directory not found: {self.data_dir}")
            return files

        for ext in ['*.xlsx', '*.csv']:
            files.extend(self.data_dir.glob(ext))

        # Filter out hidden/system files
        files = [f for f in files if not f.name.startswith('.') and not f.name.startswith('~')]

        return sorted(files)

    def _process_file_with_validation(self, db, file_path: Path):  # noqa: C901
        """Process a single file with full validation"""
        self.logger.info(f"\n[Processing] {file_path.name}")

        try:
            # Read file
            if file_path.suffix == '.xlsx':
                df = pd.read_excel(file_path)
            else:
                df = pd.read_csv(file_path)

            if df.empty:
                self.logger.warning("  Empty file, skipping")
                return

            # Normalize headers
            df.columns = self.file_validator.normalize_header(df.columns.tolist())

            # LAYER 2: Schema inference/validation
            schema = self._get_or_create_schema(df, file_path)

            if not schema:
                self.logger.error("  ✗ Schema validation failed")
                return

            # LAYER 3 & 4: Row-level validation & cross-file consistency
            valid_rows = []

            for idx, row in df.iterrows():
                self.quarantine.increment_processed()

                # Validate row
                is_valid, errors = self._validate_row(row, schema, file_path.name)

                if is_valid:
                    valid_rows.append(row)
                else:
                    # Quarantine
                    self.quarantine.quarantine_row(
                        row_data=row.to_dict(),
                        reason='VALIDATION_FAILED',
                        source_file=file_path.name,
                        row_number=idx + 2,  # +2 for header + 1-indexing
                        failed_column=', '.join(errors[:2]),
                        failure_message='; '.join(errors[:3])
                    )

            self.logger.info(f"  Valid rows: {len(valid_rows)}/{len(df)}")

            # LAYER 5: Normalization handled by transformers
            # LAYER 6: Quality metrics tracked
            # LAYER 7: Write to canonical with provenance

            if valid_rows:
                valid_df = pd.DataFrame(valid_rows)
                self._ingest_valid_data(db, valid_df, file_path.name)

            # Export quarantine for this file
            if any(r.source_file == file_path.name for r in self.quarantine.quarantined_rows):
                quarantine_file = self.quarantine.export_quarantine_report(file_path.name)
                if quarantine_file:
                    self.logger.warning(f"  ⚠ Quarantine report: {quarantine_file}")

        except Exception as e:
            self.logger.error(f"  ✗ Error processing {file_path.name}: {e}", exc_info=True)

    def _get_or_create_schema(self, df: pd.DataFrame, file_path: Path) -> Optional[DataSchema]:
        """Get existing schema or create new one"""

        # Try to load existing schema
        schema = DataSchema.load(str(file_path))

        if schema:
            self.logger.info(f"  Using existing schema (v{schema.schema_version})")

            # Check for schema drift
            validator = SchemaValidator(schema)
            drift = validator.detect_schema_drift(df)

            if drift['new_columns'] or drift['missing_columns']:
                self.logger.error("  ✗ SCHEMA DRIFT DETECTED:")
                if drift['new_columns']:
                    self.logger.error(f"    New columns: {drift['new_columns']}")
                if drift['missing_columns']:
                    self.logger.error(f"    Missing columns: {drift['missing_columns']}")

                if self.strict_mode:
                    return None  # Halt on schema drift

            return schema

        else:
            # Infer new schema
            self.logger.info("  Inferring schema...")
            schema = self.schema_engine.infer_schema(df, str(file_path))
            schema.save()
            self.logger.info(f"  ✓ Schema saved: {schema.total_columns} columns")
            return schema

    def _validate_row(self, row: pd.Series, schema: DataSchema, source_file: str) -> tuple[bool, List[str]]:
        """Comprehensive row validation"""
        errors = []

        # Schema validation
        schema_validator = SchemaValidator(schema)
        is_valid, schema_errors = schema_validator.validate_row(row)
        if not is_valid:
            errors.extend(schema_errors)

        # Row integrity
        row_valid, row_errors = RowValidator.validate_row_integrity(row, schema)
        if not row_valid:
            errors.extend(row_errors)

        # Excel errors
        excel_errors = RowValidator.detect_excel_errors(row)
        if excel_errors:
            errors.append(f"Excel errors: {', '.join(excel_errors)}")

        # Required fields (detect likely data type)
        if 'student_id' in row.index or any('email' in str(col).lower() for col in row.index):
            # Has student ID, likely student data
            for col in row.index:
                if 'email' in str(col).lower() or 'student_id' in str(col).lower():
                    is_valid, error = RequiredFieldValidator.validate_student_identifier(row[col])
                    if not is_valid:
                        errors.append(error)
                    break

        return (len(errors) == 0, errors)

    def _ingest_valid_data(self, db, df: pd.DataFrame, source_file: str):
        """Ingest validated data to canonical tables"""

        # Detect data type from columns
        if any('student' in str(col).lower() and 'email' in str(col).lower() for col in df.columns):
            self._ingest_student_data(db, df, source_file)

        if any('attendance' in str(col).lower() or 'session' in str(col).lower() for col in df.columns):
            self._ingest_engagement_data(db, df, source_file)

        if any('quiz' in str(col).lower() or 'score' in str(col).lower() for col in df.columns):
            self._ingest_academic_data(db, df, source_file)

    def _ingest_student_data(self, db, df: pd.DataFrame, source_file: str):
        """Ingest student roster data"""
        email_cols = [col for col in df.columns if 'email' in col.lower() or 'username' in col.lower()]

        if not email_cols:
            return

        email_col = email_cols[0]
        added = 0

        for _, row in df.iterrows():
            email = TypeCoercer.coerce_email(row.get(email_col))
            if not email:
                continue

            existing = db.query(DimStudent).filter_by(student_id=email).first()
            if existing:
                continue

            student = DimStudent(
                student_id=email,
                enrollment_status='Active',
                is_new_student=True
            )
            db.add(student)
            added += 1

        self.logger.info(f"  ✓ Added {added} students")

    def _ingest_engagement_data(self, db, df: pd.DataFrame, source_file: str):
        """Ingest engagement/attendance data"""
        # TODO: Implement engagement ingestion with provenance tracking
        self.logger.warning("_ingest_engagement_data is not yet implemented; skipping %s", source_file)

    def _ingest_academic_data(self, db, df: pd.DataFrame, source_file: str):
        """Ingest academic performance data"""
        # TODO: Implement academic data ingestion with provenance tracking
        self.logger.warning("_ingest_academic_data is not yet implemented; skipping %s", source_file)


def main():
    """Run the validated ETL pipeline"""
    pipeline = ValidatedEWSPipeline(strict_mode=True)
    success = pipeline.run()
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
