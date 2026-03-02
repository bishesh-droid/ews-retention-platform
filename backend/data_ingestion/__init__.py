"""
Data ingestion facade
---------------------
Provides a single import surface for ingestion workflows.
"""

from backend.services.core.data_ingestion import ingest_all_data
from backend.ingestion.pipeline import EWSDataPipeline

__all__ = ["ingest_all_data", "EWSDataPipeline"]

