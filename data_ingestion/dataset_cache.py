"""
Dataset Cache — Hash-Based Caching Layer
Avoids reprocessing the full ingestion pipeline on every request.
Uses SHA-256 fingerprinting of all source files to detect any change.

Usage
-----
    from data_ingestion.dataset_cache import DatasetCache
    cache = DatasetCache()
    train_df, val_df = cache.get_dataset()
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from data_ingestion.ingestion_logger import get_ingestion_logger

logger = get_ingestion_logger("dataset_cache")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW     = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
MASTER_CSV   = DATA_PROCESSED / "clean_master_dataset.csv"
CACHE_META   = DATA_PROCESSED / ".cache_meta.json"


class DatasetCache:
    """
    Transparent cache over MasterDatasetBuilder.

    On first call (or when source files change) it runs the full builder
    and persists `clean_master_dataset.csv`.  On subsequent calls it reads
    from disk directly — O(1) instead of O(n) re-parsing.

    Parameters
    ----------
    data_dir : str
        Raw data directory (default: data/raw).
    force_refresh : bool
        If True, always rebuild regardless of cache state.
    """

    def __init__(
        self,
        data_dir: str = str(DATA_RAW),
        force_refresh: bool = False,
    ):
        self.data_dir = Path(data_dir)
        self.force_refresh = force_refresh
        DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_dataset(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Return (train_df, val_df).
        Builds from source if cache is stale or missing.
        """
        if not self.force_refresh and self._cache_is_valid():
            logger.info("Cache HIT — loading from disk")
            return self._load_from_cache()

        logger.info("Cache MISS — rebuilding master dataset")
        return self._rebuild()

    def invalidate(self):
        """Force cache invalidation on next call."""
        if CACHE_META.exists():
            CACHE_META.unlink()
        logger.info("Cache invalidated")

    def get_cache_info(self) -> dict:
        """Return metadata about the current cache state."""
        if not CACHE_META.exists():
            return {"status": "no_cache"}
        with open(CACHE_META) as f:
            return json.load(f)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _cache_is_valid(self) -> bool:
        """Return True if the master CSV exists and source hash hasn't changed."""
        if not MASTER_CSV.exists():
            logger.info("Cache miss: master CSV does not exist")
            return False
        if not CACHE_META.exists():
            logger.info("Cache miss: no cache metadata")
            return False

        with open(CACHE_META) as f:
            meta = json.load(f)

        current_hash = self._hash_source_dir()
        if meta.get("source_hash") != current_hash:
            logger.info(f"Cache miss: source files changed (hash mismatch)")
            return False

        logger.info(
            f"Cache hit: source_hash={current_hash[:16]}… "
            f"built_at={meta.get('built_at', 'unknown')}"
        )
        return True

    def _rebuild(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Run MasterDatasetBuilder and update cache metadata."""
        # Import here to avoid circular imports
        from data_ingestion.master_builder import MasterDatasetBuilder  # noqa

        builder = MasterDatasetBuilder(data_dir=str(self.data_dir))
        train_df, val_df = builder.run()

        # Update cache metadata
        source_hash = self._hash_source_dir()
        meta = {
            "source_hash": source_hash,
            "built_at": __import__("datetime").datetime.now().isoformat(),
            "train_rows": len(train_df),
            "val_rows": len(val_df),
            "master_csv": str(MASTER_CSV),
        }
        with open(CACHE_META, "w") as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Cache updated: train={len(train_df)}, val={len(val_df)}")
        return train_df, val_df

    def _load_from_cache(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load and split master CSV into train/val by trimester."""
        try:
            # Skip metadata comment lines (lines starting with #)
            with open(MASTER_CSV, "r", encoding="utf-8") as f:
                lines = f.readlines()
            skip_rows = sum(1 for line in lines if line.startswith("#"))

            df = pd.read_csv(MASTER_CSV, skiprows=skip_rows)

            if "trimester" not in df.columns:
                logger.warning("Master CSV has no 'trimester' column — returning full dataset as train")
                return df, pd.DataFrame()

            train_df = df[df["trimester"] == "T1"].copy().reset_index(drop=True)
            val_df   = df[df["trimester"] == "T2"].copy().reset_index(drop=True)
            logger.info(f"Loaded from cache: train={len(train_df)}, val={len(val_df)}")
            return train_df, val_df

        except Exception as exc:
            logger.error(
                f"Failed to load from cache: {exc} — rebuilding",
                error_type="CACHE_LOAD_ERROR",
            )
            return self._rebuild()

    def _hash_source_dir(self) -> str:
        """
        Compute a deterministic SHA-256 hash over all .xlsx files
        in the data directory (sorted by name for reproducibility).
        """
        h = hashlib.sha256()
        xlsx_files = sorted(self.data_dir.glob("*.xlsx"))
        for path in xlsx_files:
            h.update(path.name.encode("utf-8"))
            h.update(str(path.stat().st_size).encode("utf-8"))
            h.update(str(path.stat().st_mtime).encode("utf-8"))
        return h.hexdigest()
