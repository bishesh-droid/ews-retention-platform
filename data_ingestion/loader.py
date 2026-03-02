"""
Loader — Dynamic Excel File Discoverer
Discovers, fingerprints, deduplicates, and categorises all .xlsx files
in the configured raw-data directory.

Key responsibilities
--------------------
1. Walk `data/raw/` and collect all .xlsx files.
2. Fingerprint each file (SHA-256 + file size) to detect byte-identical duplicates.
3. Group files by semantic type using keyword fingerprinting.
4. For duplicate groups, keep the canonical version (largest, or prefer the one
   without a trailing "(1)" suffix) and log the discarded duplicates.
5. Validate that required sheet names are present in each file.
6. Return a typed `FileManifest` ready for downstream consumers.
"""
import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from data_ingestion.ingestion_logger import get_ingestion_logger

logger = get_ingestion_logger("loader")

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

KNOWN_FILE_TYPES = {
    "trimester1_summary": [
        "trimester 1", "trim 1", "trimester1", "c-1, trimester 1",
        "live summary data c-1",
    ],
    "trimester2_summary": [
        "trimester 2", "trim 2", "trimester2", "summary data trimester 2",
    ],
    "engagement_analysis": [
        "engagement_analysis", "engagement analysis", "week 1-2",
        "week-wise", "student engagement analysis",
    ],
    "attendance_quiz_assignment": [
        "attendance quiz", "quiz-assignment-exam", "attendance",
    ],
    "learner_usage_week3": [
        "learner usage week 3", "learner_usage_week_3",
    ],
    "learner_usage_week5": [
        "learner usage week 5", "learner_usage_week_5",
    ],
    "graded_quiz": [
        "graded quiz", "graded_quiz", "quiz status",
    ],
}


@dataclass
class FileRecord:
    path: Path
    filename: str
    file_type: str
    size_bytes: int
    sha256: str
    sheet_names: List[str]
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    row_counts: Dict[str, int] = field(default_factory=dict)


# key = file_type, value = list of FileRecords (first entry = canonical)
FileManifest = Dict[str, List[FileRecord]]


# ---------------------------------------------------------------------------
# Core loader
# ---------------------------------------------------------------------------

class ExcelLoader:
    """
    Discovers and catalogues all .xlsx files in `data_dir`.

    Parameters
    ----------
    data_dir : str
        Path to raw data directory (default: ``data/raw``).
    strict_duplicates : bool
        If True, log duplicate files as WARNINGs. If False, silently skip.
    """

    def __init__(
        self,
        data_dir: str = "data/raw",
        strict_duplicates: bool = True,
    ):
        self.data_dir = Path(data_dir)
        self.strict_duplicates = strict_duplicates

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def load_manifest(self) -> FileManifest:
        """
        Discover all .xlsx files and return a typed FileManifest.

        Returns
        -------
        FileManifest
            Dict keyed by file_type → list[FileRecord].
            The first entry in each list is the **canonical** file.
        """
        logger.info(f"Scanning '{self.data_dir}' for .xlsx files …")

        if not self.data_dir.exists():
            logger.error(
                f"Data directory not found: {self.data_dir}",
                error_type="FILE_NOT_FOUND",
            )
            return {}

        all_files = sorted(
            f for f in self.data_dir.glob("*.xlsx")
            if not f.name.startswith("~")  # skip Excel lock files
        )

        logger.info(f"Found {len(all_files)} .xlsx file(s)")

        records: List[FileRecord] = []
        for path in all_files:
            record = self._build_record(path)
            if record:
                records.append(record)

        # Deduplicate by SHA-256 hash
        records = self._mark_duplicates(records)

        # Group by semantic type
        manifest: FileManifest = {}
        for record in records:
            manifest.setdefault(record.file_type, []).append(record)

        # Sort each group: canonical first (non-duplicate, larger file)
        for ftype, group in manifest.items():
            canonical = [r for r in group if not r.is_duplicate]
            dupes = [r for r in group if r.is_duplicate]
            manifest[ftype] = canonical + dupes

        self._print_manifest_summary(manifest)
        return manifest

    def load_dataframe(
        self,
        record: FileRecord,
        sheet_name: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Load a FileRecord into a dict of sheet_name → DataFrame.

        Parameters
        ----------
        record : FileRecord
        sheet_name : str, optional
            If given, load only that sheet. Otherwise load all sheets.
        """
        if record.is_duplicate:
            logger.warning(
                f"Loading duplicate file '{record.filename}' — "
                f"consider using '{record.duplicate_of}' instead",
                source_file=record.filename,
            )

        frames: Dict[str, pd.DataFrame] = {}
        try:
            xl = pd.ExcelFile(record.path, engine="openpyxl")
            sheets_to_load = (
                [sheet_name] if sheet_name and sheet_name in xl.sheet_names
                else xl.sheet_names
            )
            for sname in sheets_to_load:
                try:
                    df = pd.read_excel(xl, sheet_name=sname, dtype=str)
                    frames[sname] = df
                    logger.info(
                        f"  Loaded sheet '{sname}' → {df.shape[0]} rows × {df.shape[1]} cols",
                        source_file=record.filename,
                    )
                except Exception as exc:
                    logger.error(
                        f"Error reading sheet '{sname}' from '{record.filename}': {exc}",
                        error_type="SHEET_READ_ERROR",
                        source_file=record.filename,
                    )
        except Exception as exc:
            logger.error(
                f"Cannot open file '{record.filename}': {exc}",
                error_type="FILE_OPEN_ERROR",
                source_file=record.filename,
            )
        return frames

    def get_canonical(self, manifest: FileManifest, file_type: str) -> Optional[FileRecord]:
        """Return the canonical (first, non-duplicate) record for a given type."""
        records = manifest.get(file_type, [])
        non_dupes = [r for r in records if not r.is_duplicate]
        return non_dupes[0] if non_dupes else (records[0] if records else None)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_record(self, path: Path) -> Optional[FileRecord]:
        """Build a FileRecord for a single xlsx file."""
        try:
            size = path.stat().st_size
            sha256 = self._sha256(path)
            file_type = self._classify(path.name)

            xl = pd.ExcelFile(path, engine="openpyxl")
            sheet_names = xl.sheet_names

            # Count rows per sheet (cheap head-count)
            row_counts: Dict[str, int] = {}
            for sname in sheet_names:
                try:
                    df_tmp = pd.read_excel(xl, sheet_name=sname, nrows=5000, dtype=str)
                    row_counts[sname] = len(df_tmp)
                except Exception:
                    row_counts[sname] = -1

            logger.info(
                f"  '{path.name}' | type={file_type} | sheets={sheet_names} | "
                f"size={size // 1024}KB | sha256={sha256[:8]}…",
                source_file=path.name,
            )
            return FileRecord(
                path=path,
                filename=path.name,
                file_type=file_type,
                size_bytes=size,
                sha256=sha256,
                sheet_names=sheet_names,
                row_counts=row_counts,
            )

        except Exception as exc:
            logger.error(
                f"Cannot build record for '{path.name}': {exc}",
                error_type="RECORD_BUILD_ERROR",
                source_file=path.name,
            )
            return None

    def _sha256(self, path: Path) -> str:
        """Compute SHA-256 hash of a file in streaming chunks."""
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _classify(self, filename: str) -> str:
        """
        Map a filename to a semantic type using keyword matching.
        Falls back to 'unknown' if no match is found.
        """
        lower = filename.lower()
        for file_type, keywords in KNOWN_FILE_TYPES.items():
            if any(kw in lower for kw in keywords):
                return file_type
        return "unknown"

    def _mark_duplicates(self, records: List[FileRecord]) -> List[FileRecord]:
        """
        Identify byte-identical files (same SHA-256).
        Among duplicates: the one without '(1)' suffix is canonical;
        if both have it, the larger file is canonical.
        """
        seen: Dict[str, FileRecord] = {}  # sha256 → first canonical seen

        for record in records:
            h = record.sha256
            if h not in seen:
                seen[h] = record
            else:
                # We have a duplicate — decide which is canonical
                existing = seen[h]
                # Prefer filename without trailing "(1)" or "(2)"
                existing_has_suffix = bool(re.search(r"\(\d+\)\.xlsx$", existing.filename, re.I))
                current_has_suffix = bool(re.search(r"\(\d+\)\.xlsx$", record.filename, re.I))

                if existing_has_suffix and not current_has_suffix:
                    # Replace existing as canonical
                    existing.is_duplicate = True
                    existing.duplicate_of = record.filename
                    seen[h] = record
                else:
                    # Mark current as duplicate
                    record.is_duplicate = True
                    record.duplicate_of = existing.filename

                if self.strict_duplicates:
                    logger.warning(
                        f"DUPLICATE FILE detected: '{record.filename}' is identical to "
                        f"'{seen[h].filename}' (sha256={h[:12]}…)",
                        source_file=record.filename,
                    )
        return records

    def _print_manifest_summary(self, manifest: FileManifest):
        logger.info("─" * 60)
        logger.info("FILE MANIFEST SUMMARY")
        for ftype, records in manifest.items():
            canonical = [r for r in records if not r.is_duplicate]
            dupes = [r for r in records if r.is_duplicate]
            logger.info(
                f"  [{ftype}] → {len(canonical)} canonical, {len(dupes)} duplicate(s)"
            )
        logger.info("─" * 60)
