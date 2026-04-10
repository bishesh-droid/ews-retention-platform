"""
Admin ingestion endpoints for triggering data ingestion via API.
"""

import logging
import uuid
from pathlib import Path
from typing import Optional

import magic
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from backend.api.deps import get_db, require_role
from backend.core.rate_limiting import limiter
from backend.database.models.user import User
from backend.services.task_tracker import create_task, get_task, update_task
from backend.database.connection import SessionLocal
from backend.config import RATE_LIMIT_INGEST, MAX_UPLOAD_SIZE_MB

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_SIZE = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Convert MB to bytes

ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls
    "text/csv",
    "application/csv",
    "application/octet-stream",  # some browsers send this for xlsx
}

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


@router.post("/admin/ingest", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(RATE_LIMIT_INGEST)
async def trigger_ingestion(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_role(["Admin"])),
    db: Session = Depends(get_db),
):
    """
    Trigger data ingestion in the background.

    Optionally accepts a new Excel file upload which will be saved to the data directory
    before ingestion begins.

    Returns 202 Accepted immediately with a task ID. Poll /admin/ingest/status/{task_id}
    to check completion.
    """
    task_id = create_task("ingest_all_data")

    saved_file_path = None

    if file:
        # 1. Read content first (so we can validate before writing)
        content = await file.read()

        # 2. Validate file size (SEC-2)
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE_MB}MB."
            )

        # 3. Validate extension first (quick reject)
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # 4. Validate actual MIME type using file magic bytes (SEC-3)
        detected_mime = magic.from_buffer(content[:2048], mime=True)
        if detected_mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File content does not match expected type. Detected: {detected_mime}"
            )

        # 5. Path traversal sanitization (SEC-4)
        # NEVER use file.filename directly in a path
        safe_basename = Path(file.filename or "upload").name  # strips any ../ or absolute path components
        # Extra safety: replace any remaining suspicious characters
        safe_basename = "".join(c for c in safe_basename if c.isalnum() or c in "._- ")
        safe_basename = safe_basename.strip()
        if not safe_basename:
            safe_basename = "upload"

        # Prepend UUID to prevent collisions and make filenames unpredictable
        unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_basename}"

        # Save to data directory
        data_dir = Path("backend/data")
        data_dir.mkdir(parents=True, exist_ok=True)

        dest = data_dir / unique_filename
        try:
            with open(dest, "wb") as f:
                f.write(content)
            saved_file_path = str(dest)
            logger.info(
                f"File saved: {unique_filename} ({len(content)} bytes) from upload: {file.filename!r} by {current_user.username}"
            )
        except Exception:
            logger.exception(f"File upload failed for {file.filename!r}", extra={"filename": file.filename})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File upload failed. Please try again or contact support."
            )

    async def run_ingestion():
        """Background task wrapper for ingestion."""
        update_task(task_id, "running")

        # Create a new DB session for the background task
        session = SessionLocal()
        try:
            from backend.services.core.data_ingestion import ingest_all_data
            from pathlib import Path

            # Pass uploaded file path for cleanup after ingestion
            uploaded_path = Path(saved_file_path) if saved_file_path else None

            await ingest_all_data(
                session,
                triggered_by=f"api:{current_user.username}",
                uploaded_filepath=uploaded_path
            )
            update_task(task_id, "success")
            logger.info(f"Background ingestion completed successfully (task {task_id})")
        except Exception as e:
            error_msg = "Background ingestion failed — see server logs for details"
            update_task(task_id, "failed", error=error_msg)
            logger.exception(f"Background ingestion failed (task {task_id})", exc_info=e)
        finally:
            session.close()

    background_tasks.add_task(run_ingestion)

    return {
        "task_id": task_id,
        "status": "accepted",
        "message": "Ingestion started in background",
        "saved_file": saved_file_path,
    }


@router.get("/admin/ingest/status/{task_id}")
async def get_ingestion_status(
    task_id: str,
    current_user: User = Depends(require_role(["Admin"])),
):
    """
    Get the status of a background ingestion task.

    Returns task status including:
    - id: task ID
    - label: task description
    - status: "pending", "running", "success", or "failed"
    - started_at: ISO timestamp when task started (if running/completed)
    - finished_at: ISO timestamp when task completed (if completed)
    - error: Error message if task failed
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    return task


@router.get("/admin/ingest/tasks")
async def list_recent_tasks(
    limit: int = 20,
    current_user: User = Depends(require_role(["Admin"])),
):
    """
    List recent ingestion tasks.

    Args:
        limit: Maximum number of tasks to return (default 20, max 100)

    Returns:
        List of task status dicts, most recent first
    """
    from backend.services.task_tracker import list_tasks

    limit = min(limit, 100)  # Cap at 100
    tasks = list_tasks(limit=limit)
    return {"tasks": tasks, "count": len(tasks)}
