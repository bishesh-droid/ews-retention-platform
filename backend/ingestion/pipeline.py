# DEPRECATED: EWSDataPipeline is a standalone CLI tool only.
# The production ingestion path uses ingest_all_data() from data_ingestion.py.
# Do not use EWSDataPipeline from FastAPI route handlers.
"""
EWS Data Pipeline - Main ETL Orchestrator (CLI ONLY - DEPRECATED for API use)
Simplified version for initial implementation
"""
import pandas as pd
import os
from pathlib import Path
from datetime import datetime, date

from backend.database import (
    DimStudent, DimCourse,
    FactAcademicPerformance, FactEngagement
)
from backend.ingestion.transformers import TypeCoercer
from backend.ingestion.error_logger import IngestionErrorLogger
from backend.core.logger import setup_logger

logger = setup_logger("ews_pipeline")


class EWSDataPipeline:
    """Main ingestion pipeline for EWS raw data"""

    def __init__(self, data_dir: str = "data/raw", db_session=None):
        self.data_dir = Path(data_dir)
        self.logger = logger
        self.error_logger = IngestionErrorLogger()
        # Session must be passed in as a parameter, never created inside __init__
        self.db = db_session
        self.staging: dict = {}  # In-memory staging area

    def run(self):
        """Execute full pipeline"""
        self.logger.info("="*80)
        self.logger.info("Starting EWS Data Ingestion Pipeline")
        self.logger.info("="*80)

        start_time = datetime.now()

        try:
            # Phase 1: Load student roster
            self.logger.info("\\n[Phase 1] Loading student roster...")
            self.ingest_student_roster()

            # Phase 2: Load courses
            self.logger.info("\\n[Phase 2] Loading courses...")
            self.ingest_courses()

            # Phase 3: Load attendance
            self.logger.info("\\n[Phase 3] Loading attendance data...")
            self.ingest_attendance()

            # Phase 4: Load assessments
            self.logger.info("\\n[Phase 4] Loading assessment data...")
            self.ingest_assessments()

            # Commit transaction
            self.db.commit()

            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"\\n✓ Pipeline completed successfully in {duration:.1f}s")

            # Print error summary
            self.error_logger.print_summary()

            return True

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            self.db.rollback()
            return False
        finally:
            self.db.close()

    def ingest_student_roster(self):  # noqa: C901
        """Load student dimension from enrollment files"""
        if self.db is None:
            raise RuntimeError("No database session provided. Pass db_session to __init__.")
        # Primary file: Trimester 1 attendance file (has Total_Enrolled sheet)
        file_path = self.data_dir / "_Trimester-1 2025 Attendance Quiz-Assignment-Exam 5Jan2025.xlsx"

        if not file_path.exists():
            self.logger.warning(f"File not found: {file_path}")
            return

        try:
            # Read Total_Enrolled sheet
            xl = pd.ExcelFile(file_path)

            # Try to find enrollment/student list sheet
            enrollment_sheets = [s for s in xl.sheet_names if 'enroll' in s.lower() or 'total' in s.lower()]

            if not enrollment_sheets:
                self.logger.warning("No enrollment sheet found")
                return

            df = pd.read_excel(file_path, sheet_name=enrollment_sheets[0])

            # Normalize column names
            df.columns = [str(col).strip() for col in df.columns]

            # Find student ID columns
            id_cols = [col for col in df.columns if any(x in col.lower() for x in ['username', 'email', 'student'])]

            if not id_cols:
                self.logger.warning("No student ID column found")
                return

            students_added = 0

            for idx, row in df.iterrows():
                try:
                    # Extract student email
                    student_id = None
                    for col in id_cols:
                        val = row.get(col)
                        if pd.notna(val) and '@' in str(val):
                            student_id = TypeCoercer.coerce_email(val)
                            break

                    if not student_id:
                        continue

                    # Check if student exists
                    existing = self.db.query(DimStudent).filter_by(student_id=student_id).first()
                    if existing:
                        continue

                    # Create student record
                    student = DimStudent(
                        student_id=student_id,
                        student_name=str(row.get('first_name', '')) + ' ' + str(row.get('last_name', '')),
                        program='BS',  # Default, can be refined
                        enrollment_status='Active',
                        is_new_student=True
                    )

                    self.db.add(student)
                    students_added += 1

                except Exception as e:
                    self.error_logger.log_error(
                        source_file=file_path.name,
                        row_number=idx,
                        field='student_record',
                        error_type='parsing_error',
                        message=str(e)
                    )

            self.logger.info(f"  ✓ Added {students_added} students")

        except Exception as e:
            self.logger.error(f"Error loading student roster: {e}")

    def ingest_courses(self) -> None:
        """
        Ingest course catalog from enrollment data headers or dedicated course column.

        TODO: Replace placeholder with real implementation that extracts course names
        from the enrollment sheet headers (e.g., "Course: Data Pre-processing") or
        a dedicated 'course_name' column if available in the data files.
        """
        # Minimal real implementation: try to extract course names from enrollment data
        course_names = set()
        try:
            # Attempt to read course names from enrollment sheet headers
            # This assumes the enrollment data has a 'course_name' column or similar
            enrollment_path = Path(self.data_dir) / "engagement_data.xlsx"
            if enrollment_path.exists():
                import pandas as pd
                df = pd.read_excel(enrollment_path, nrows=5)  # Read header only
                if 'course_name' in df.columns:
                    course_names = set(df['course_name'].dropna().unique())
        except Exception as e:
            logger.warning(f"Could not extract course names from enrollment data: {e}")

        # Fallback to placeholder if no courses found
        if not course_names:
            course_names = {"Default Course"}

        for course_name in course_names:
            course_code = course_name.upper().replace(" ", "_")[:20]
            logger.info(f"Course catalog entry: {course_name} ({course_code})")

            existing = self.db.query(DimCourse).filter_by(course_id=course_code).first()
            if not existing:
                course = DimCourse(
                    course_id=course_code,
                    course_name=course_name,
                    program='BS'
                )
                self.db.add(course)

        self.logger.info(f"  ✓ Loaded {len(course_names)} courses")

    def ingest_attendance(self):  # noqa: C901
        """Load attendance records from Live Summary sheets"""
        if self.db is None:
            raise RuntimeError("No database session provided. Pass db_session to __init__.")
        files_processed = 0
        records_added = 0

        # Process both trimester files
        attendance_files = [
            "B.S and M.Sc Live Summary Data C-1, Trimester 1.xlsx",
            "B.S and M.Sc Summary Data Trimester 2.xlsx"
        ]

        for filename in attendance_files:
            file_path = self.data_dir / filename
            if not file_path.exists():
                continue

            try:
                xl = pd.ExcelFile(file_path)

                # Find attendance sheets
                attendance_sheets = [s for s in xl.sheet_names if 'bs' in s.lower() or 'msc' in s.lower()]

                for sheet_name in attendance_sheets:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)

                    # Look for student email and attendance columns
                    email_cols = [col for col in df.columns if 'email' in str(col).lower() or 'username' in str(col).lower()]

                    if not email_cols:
                        continue

                    email_col = email_cols[0]

                    # Process each student
                    for idx, row in df.iterrows():
                        email = TypeCoercer.coerce_email(row.get(email_col))
                        if not email:
                            continue

                        # Check if student exists in dim
                        student = self.db.query(DimStudent).filter_by(student_id=email).first()
                        if not student:
                            continue

                        # Extract attendance percentage if available
                        attendance_pct = None
                        for col in df.columns:
                            if 'attendance' in str(col).lower() or '%' in str(col):
                                attendance_pct = TypeCoercer.coerce_percentage(row.get(col))
                                if attendance_pct is not None:
                                    break

                        if attendance_pct is not None:
                            # Create engagement record
                            engagement = FactEngagement(
                                student_id=email,
                                course_id='DEFAULT_COURSE',
                                metric_date=date.today(),
                                attendance_percentage=attendance_pct,
                                data_snapshot_date=date.today(),
                                source_file=filename
                            )
                            self.db.add(engagement)
                            records_added += 1

                files_processed += 1

            except Exception as e:
                self.logger.error(f"Error processing {filename}: {e}")

        self.logger.info(f"  ✓ Processed {files_processed} files, added {records_added} attendance records")

    def ingest_assessments(self):
        """Load assessment records from quiz files"""
        if self.db is None:
            raise RuntimeError("No database session provided. Pass db_session to __init__.")
        quiz_files = [f for f in os.listdir(self.data_dir) if 'quiz' in f.lower() and f.endswith('.xlsx')]

        records_added = 0

        for filename in quiz_files:
            file_path = self.data_dir / filename

            try:
                df = pd.read_excel(file_path)

                # Look for student email column
                email_cols = [col for col in df.columns if 'email' in str(col).lower() or 'username' in str(col).lower()]
                if not email_cols:
                    continue

                email_col = email_cols[0]

                # Look for score columns
                score_cols = [col for col in df.columns if 'score' in str(col).lower() or 'grade' in str(col).lower()]

                for idx, row in df.iterrows():
                    email = TypeCoercer.coerce_email(row.get(email_col))
                    if not email:
                        continue

                    # Check if student exists
                    student = self.db.query(DimStudent).filter_by(student_id=email).first()
                    if not student:
                        continue

                    # Extract score
                    score = None
                    if score_cols:
                        score = TypeCoercer.coerce_float(row.get(score_cols[0]))

                    # Create academic performance record
                    perf = FactAcademicPerformance(
                        student_id=email,
                        course_id='DEFAULT_COURSE',
                        trimester='T1-2025',
                        assessment_type='Quiz',
                        assessment_name=filename.replace('.xlsx', ''),
                        scored=score if score else 0,
                        percentage=score if score else 0,
                        submitted=score is not None,
                        data_snapshot_date=date.today(),
                        source_file=filename
                    )
                    self.db.add(perf)
                    records_added += 1

            except Exception as e:
                self.logger.error(f"Error processing quiz file {filename}: {e}")

        self.logger.info(f"  ✓ Added {records_added} assessment records from {len(quiz_files)} quiz files")


def main():
    """Run the ETL pipeline"""
    pipeline = EWSDataPipeline()
    success = pipeline.run()
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
