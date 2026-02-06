"""
Core Services Package
---------------------
Core business logic services including EWS engine, decision engine, and feature service.
"""

from backend.app.services.core.ews_engine import calculate_student_risk, batch_predict, get_signal_summary
from backend.app.services.core.data_ingestion import ingest_data

__all__ = [
    "calculate_student_risk",
    "batch_predict",
    "get_signal_summary",
    "ingest_data",
]
