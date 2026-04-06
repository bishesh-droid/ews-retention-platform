"""
Monitoring routes
-----------------
Lightweight operational endpoints for health and prediction statistics.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_current_user
from backend.database.models.user import User
from backend.core.logger import sys_logger
from backend.services.ml_service import ml_service
from backend.utils.api import success_response

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


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
