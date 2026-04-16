"""
Ingestion Audit Log Model
-------------------------
Tracks data ingestion runs with detailed statistics and error logging.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Float, JSON
from ..connection import Base


class IngestionRun(Base):
    """Audit log for data ingestion runs with detailed statistics."""

    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True)
    run_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    triggered_by = Column(String(64), nullable=True)  # "startup"|"api"|"manual"
    files_processed = Column(JSON, default=list)  # [{"name": str, "rows": int}]
    students_created = Column(Integer, default=0)
    students_updated = Column(Integer, default=0)
    enrollments_created = Column(Integer, default=0)
    enrollments_updated = Column(Integer, default=0)
    graded_components_added = Column(Integer, default=0)
    risk_scores_updated = Column(Integer, default=0)
    errors = Column(JSON, default=list)  # [{"file": str, "error": str}]
    duration_seconds = Column(Float, nullable=True)
    status = Column(
        String(32), default="running"
    )  # "running"|"success"|"partial"|"failed"
