"""
Monitoring routes
-----------------
Lightweight operational endpoints for health and prediction statistics.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_db
from backend.database.models.user import User
from backend.database.models.ingestion_run import IngestionRun
from backend.core.logger import sys_logger
from backend.services.ml_service import ml_service
from backend.utils.api import success_response

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    health: Dict[str, Any] = {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

    # Check DB connectivity
    try:
        db.execute(text("SELECT 1"))
        health["database"] = "connected"
    except Exception:
        health["database"] = "error"
        health["status"] = "unhealthy"

    # Check ingestion staleness
    latest_run = (
        db.query(IngestionRun)
        .order_by(IngestionRun.run_at.desc())
        .first()
    )
    if latest_run is None:
        health["last_ingestion"] = "never"
        health["ingestion_status"] = "warning"
    else:
        age_hours = (
            datetime.now(timezone.utc) - latest_run.run_at.replace(tzinfo=timezone.utc)  # type: ignore[union-attr]
        ).total_seconds() / 3600
        health["last_ingestion_hours_ago"] = round(age_hours, 1)
        health["last_ingestion_status"] = latest_run.status or ""
        if latest_run.status != "success" or age_hours > 48:
            health["ingestion_status"] = "stale"
            health["status"] = "degraded"  # not unhealthy — server is up, just data is old
        else:
            health["ingestion_status"] = "ok"

    status_code = 200 if health["status"] == "healthy" else 503 if health["status"] == "unhealthy" else 200
    return JSONResponse(content=health, status_code=status_code)


@router.get("/predictions")
def get_prediction_stats(
    _user: User = Depends(get_current_user),
):
    """
    Return in-memory statistics about prediction calls.
    Requires authentication (does not expose PII, but leaks operational
    details that should not be visible to anonymous callers).
    """
    try:
        stats = ml_service.get_runtime_stats()
        return success_response(stats, message="ML pipeline stats")
    except Exception as exc:
        # Keep monitoring endpoint resilient and avoid leaking internals.
        sys_logger.error(f"Failed to fetch ML runtime stats: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Monitoring service temporarily unavailable.",
        )
