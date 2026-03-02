"""
EWS Data Ingestion Package
Production-grade ETL pipeline for Excel-based student datasets.

Usage:
    from data_ingestion.master_builder import MasterDatasetBuilder
    builder = MasterDatasetBuilder()
    df_train, df_val = builder.run()
"""
from data_ingestion.ingestion_logger import get_ingestion_logger

__version__ = "1.0.0"
__all__ = ["loader", "schema_mapper", "validator", "normalizer", "merger", "master_builder"]
