"""
015_fix_remaining_datetime_columns.py
--------------------------------------
Extend timezone-aware timestamps to all remaining tables.

This migration complements 014 by converting naive datetime columns
to timezone-aware TIMESTAMPTZ for all other model tables:
- audit_logs
- student_responses
- ingestion_runs
- raw_events
- intervention_logs
- risk_snapshots
- goals
- dim_students, dim_courses, fact_* tables
- course_content_registry

DATA SAFETY STRATEGY:
---------------------
1. Backfill NULL timestamps with sensible defaults BEFORE conversion
2. For audit/ingestion logs: use current UTC time for NULLs
3. For student responses: preserve NULL if outcome not determined
4. Convert naive timestamps to UTC-aware using AT TIME ZONE

Revision ID: 015
Revises: 014
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade():
    """
    Convert all remaining naive datetime columns to timezone-aware TIMESTAMPTZ.
    PostgreSQL-specific: TIMESTAMPTZ stores timestamps in UTC.
    """

    conn = op.get_bind()

    # =========================================================================
    # STEP 1: BACKFILL NULL VALUES
    # =========================================================================

    # audit_logs - use current UTC for any NULL timestamps
    op.execute("UPDATE audit_logs SET timestamp = NOW() AT TIME ZONE 'UTC' WHERE timestamp IS NULL")

    # student_responses - keep NULL for records where outcome not determined
    # No backfill needed, column allows NULL

    # ingestion_runs - use current UTC for NULLs
    op.execute("UPDATE ingestion_runs SET run_at = NOW() AT TIME ZONE 'UTC' WHERE run_at IS NULL")

    # raw_events - use current UTC for NULLs
    op.execute("UPDATE raw_events SET timestamp = NOW() AT TIME ZONE 'UTC' WHERE timestamp IS NULL")

    # intervention_logs - use current UTC for NULLs
    op.execute("UPDATE intervention_logs SET recommended_at = NOW() AT TIME ZONE 'UTC' WHERE recommended_at IS NULL")
    op.execute("UPDATE intervention_logs SET acted_on_at = NOW() AT TIME ZONE 'UTC' WHERE acted_on_at IS NULL")
    op.execute("UPDATE intervention_logs SET follow_up_at = NOW() AT TIME ZONE 'UTC' WHERE follow_up_at IS NULL")

    # risk_snapshots - use current UTC for NULLs
    op.execute("UPDATE risk_snapshots SET timestamp = NOW() AT TIME ZONE 'UTC' WHERE timestamp IS NULL")

    # goals - use current UTC for NULL start_date
    op.execute("UPDATE goals SET start_date = NOW() AT TIME ZONE 'UTC' WHERE start_date IS NULL")

    # dim_students - use current UTC for NULLs
    op.execute("UPDATE dim_students SET created_at = NOW() AT TIME ZONE 'UTC' WHERE created_at IS NULL")
    op.execute("UPDATE dim_students SET updated_at = NOW() AT TIME ZONE 'UTC' WHERE updated_at IS NULL")

    # dim_courses - use current UTC for NULLs
    op.execute("UPDATE dim_courses SET created_at = NOW() AT TIME ZONE 'UTC' WHERE created_at IS NULL")

    # fact_academic_performance - use current UTC for NULLs
    op.execute("UPDATE fact_academic_performance SET created_at = NOW() AT TIME ZONE 'UTC' WHERE created_at IS NULL")

    # fact_engagement - use current UTC for NULLs
    op.execute("UPDATE fact_engagement SET created_at = NOW() AT TIME ZONE 'UTC' WHERE created_at IS NULL")

    # fact_consistency - use current UTC for NULLs
    op.execute("UPDATE fact_consistency SET created_at = NOW() AT TIME ZONE 'UTC' WHERE created_at IS NULL")

    # fact_intent_responsiveness - use current UTC for NULLs
    op.execute("UPDATE fact_intent_responsiveness SET created_at = NOW() AT TIME ZONE 'UTC' WHERE created_at IS NULL")

    # data_lineage - use current UTC for NULLs
    op.execute("UPDATE data_lineage SET processing_timestamp = NOW() AT TIME ZONE 'UTC' WHERE processing_timestamp IS NULL")

    # course_content_registry - use current UTC for NULLs
    op.execute("UPDATE course_content_registry SET last_updated_at = NOW() AT TIME ZONE 'UTC' WHERE last_updated_at IS NULL")

    # =========================================================================
    # STEP 2: CONVERT TIMESTAMP COLUMNS TO TIMESTAMPTZ
    # =========================================================================

    # audit_logs
    op.execute("""
        ALTER TABLE audit_logs
        ALTER COLUMN timestamp TYPE TIMESTAMPTZ
        USING timestamp AT TIME ZONE 'UTC'
    """)

    # student_responses (recorded_at allows NULL)
    op.execute("""
        ALTER TABLE student_responses
        ALTER COLUMN recorded_at TYPE TIMESTAMPTZ
        USING recorded_at AT TIME ZONE 'UTC'
    """)

    # ingestion_runs
    op.execute("""
        ALTER TABLE ingestion_runs
        ALTER COLUMN run_at TYPE TIMESTAMPTZ
        USING run_at AT TIME ZONE 'UTC'
    """)

    # raw_events
    op.execute("""
        ALTER TABLE raw_events
        ALTER COLUMN timestamp TYPE TIMESTAMPTZ
        USING timestamp AT TIME ZONE 'UTC'
    """)

    # intervention_logs
    op.execute("""
        ALTER TABLE intervention_logs
        ALTER COLUMN recommended_at TYPE TIMESTAMPTZ
        USING recommended_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE intervention_logs
        ALTER COLUMN acted_on_at TYPE TIMESTAMPTZ
        USING acted_on_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE intervention_logs
        ALTER COLUMN follow_up_at TYPE TIMESTAMPTZ
        USING follow_up_at AT TIME ZONE 'UTC'
    """)

    # risk_snapshots
    op.execute("""
        ALTER TABLE risk_snapshots
        ALTER COLUMN timestamp TYPE TIMESTAMPTZ
        USING timestamp AT TIME ZONE 'UTC'
    """)

    # goals
    op.execute("""
        ALTER TABLE goals
        ALTER COLUMN start_date TYPE TIMESTAMPTZ
        USING start_date AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE goals
        ALTER COLUMN end_date TYPE TIMESTAMPTZ
        USING end_date AT TIME ZONE 'UTC'
    """)

    # dim_students
    op.execute("""
        ALTER TABLE dim_students
        ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE dim_students
        ALTER COLUMN updated_at TYPE TIMESTAMPTZ
        USING updated_at AT TIME ZONE 'UTC'
    """)

    # dim_courses
    op.execute("""
        ALTER TABLE dim_courses
        ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC'
    """)

    # fact_academic_performance
    op.execute("""
        ALTER TABLE fact_academic_performance
        ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_academic_performance
        ALTER COLUMN submission_timestamp TYPE TIMESTAMPTZ
        USING submission_timestamp AT TIME ZONE 'UTC'
    """)

    # fact_engagement
    op.execute("""
        ALTER TABLE fact_engagement
        ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC'
    """)

    # fact_consistency
    op.execute("""
        ALTER TABLE fact_consistency
        ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC'
    """)

    # fact_intent_responsiveness
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN created_at TYPE TIMESTAMPTZ
        USING created_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN quiz_deadline TYPE TIMESTAMPTZ
        USING quiz_deadline AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN first_attempt_timestamp TYPE TIMESTAMPTZ
        USING first_attempt_timestamp AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN final_submission_timestamp TYPE TIMESTAMPTZ
        USING final_submission_timestamp AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN message_sent_date TYPE TIMESTAMPTZ
        USING message_sent_date AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN response_received_date TYPE TIMESTAMPTZ
        USING response_received_date AT TIME ZONE 'UTC'
    """)

    # data_lineage
    op.execute("""
        ALTER TABLE data_lineage
        ALTER COLUMN processing_timestamp TYPE TIMESTAMPTZ
        USING processing_timestamp AT TIME ZONE 'UTC'
    """)

    # course_content_registry
    op.execute("""
        ALTER TABLE course_content_registry
        ALTER COLUMN last_updated_at TYPE TIMESTAMPTZ
        USING last_updated_at AT TIME ZONE 'UTC'
    """)


def downgrade():
    """
    Revert TIMESTAMPTZ columns back to naive TIMESTAMP.
    Note: This loses timezone information but converts back to UTC.
    """

    # audit_logs
    op.execute("""
        ALTER TABLE audit_logs
        ALTER COLUMN timestamp TYPE TIMESTAMP
        USING timestamp AT TIME ZONE 'UTC'
    """)

    # student_responses
    op.execute("""
        ALTER TABLE student_responses
        ALTER COLUMN recorded_at TYPE TIMESTAMP
        USING recorded_at AT TIME ZONE 'UTC'
    """)

    # ingestion_runs
    op.execute("""
        ALTER TABLE ingestion_runs
        ALTER COLUMN run_at TYPE TIMESTAMP
        USING run_at AT TIME ZONE 'UTC'
    """)

    # raw_events
    op.execute("""
        ALTER TABLE raw_events
        ALTER COLUMN timestamp TYPE TIMESTAMP
        USING timestamp AT TIME ZONE 'UTC'
    """)

    # intervention_logs
    op.execute("""
        ALTER TABLE intervention_logs
        ALTER COLUMN recommended_at TYPE TIMESTAMP
        USING recommended_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE intervention_logs
        ALTER COLUMN acted_on_at TYPE TIMESTAMP
        USING acted_on_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE intervention_logs
        ALTER COLUMN follow_up_at TYPE TIMESTAMP
        USING follow_up_at AT TIME ZONE 'UTC'
    """)

    # risk_snapshots
    op.execute("""
        ALTER TABLE risk_snapshots
        ALTER COLUMN timestamp TYPE TIMESTAMP
        USING timestamp AT TIME ZONE 'UTC'
    """)

    # goals
    op.execute("""
        ALTER TABLE goals
        ALTER COLUMN start_date TYPE TIMESTAMP
        USING start_date AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE goals
        ALTER COLUMN end_date TYPE TIMESTAMP
        USING end_date AT TIME ZONE 'UTC'
    """)

    # dim_students
    op.execute("""
        ALTER TABLE dim_students
        ALTER COLUMN created_at TYPE TIMESTAMP
        USING created_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE dim_students
        ALTER COLUMN updated_at TYPE TIMESTAMP
        USING updated_at AT TIME ZONE 'UTC'
    """)

    # dim_courses
    op.execute("""
        ALTER TABLE dim_courses
        ALTER COLUMN created_at TYPE TIMESTAMP
        USING created_at AT TIME ZONE 'UTC'
    """)

    # fact_academic_performance
    op.execute("""
        ALTER TABLE fact_academic_performance
        ALTER COLUMN created_at TYPE TIMESTAMP
        USING created_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_academic_performance
        ALTER COLUMN submission_timestamp TYPE TIMESTAMP
        USING submission_timestamp AT TIME ZONE 'UTC'
    """)

    # fact_engagement
    op.execute("""
        ALTER TABLE fact_engagement
        ALTER COLUMN created_at TYPE TIMESTAMP
        USING created_at AT TIME ZONE 'UTC'
    """)

    # fact_consistency
    op.execute("""
        ALTER TABLE fact_consistency
        ALTER COLUMN created_at TYPE TIMESTAMP
        USING created_at AT TIME ZONE 'UTC'
    """)

    # fact_intent_responsiveness
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN created_at TYPE TIMESTAMP
        USING created_at AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN quiz_deadline TYPE TIMESTAMP
        USING quiz_deadline AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN first_attempt_timestamp TYPE TIMESTAMP
        USING first_attempt_timestamp AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN final_submission_timestamp TYPE TIMESTAMP
        USING final_submission_timestamp AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN message_sent_date TYPE TIMESTAMP
        USING message_sent_date AT TIME ZONE 'UTC'
    """)
    op.execute("""
        ALTER TABLE fact_intent_responsiveness
        ALTER COLUMN response_received_date TYPE TIMESTAMP
        USING response_received_date AT TIME ZONE 'UTC'
    """)

    # data_lineage
    op.execute("""
        ALTER TABLE data_lineage
        ALTER COLUMN processing_timestamp TYPE TIMESTAMP
        USING processing_timestamp AT TIME ZONE 'UTC'
    """)

    # course_content_registry
    op.execute("""
        ALTER TABLE course_content_registry
        ALTER COLUMN last_updated_at TYPE TIMESTAMP
        USING last_updated_at AT TIME ZONE 'UTC'
    """)
