"""
Monitoring routes
-----------------
Lightweight operational endpoints for health and prediction statistics.
"""

from fastapi import APIRouter

from models.predict_model import REGISTRY, RUNTIME_STATS  # type: ignore
from backend.utils.api import success_response

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/predictions")
def get_prediction_stats():
    """
    Return in-memory statistics about prediction calls.

    This is intended for lightweight monitoring/observability and does not
    expose any personally identifiable student data.
    """
    stats = dict(RUNTIME_STATS)

    # Enrich with model registry status
    registry_loaded = bool(REGISTRY and REGISTRY.is_loaded())
    model_version = REGISTRY.get_model_version() if registry_loaded else "unknown"
    stats.update(
        {
            "registry_loaded": registry_loaded,
            "available_models": REGISTRY.available_models() if registry_loaded else [],
            "model_version": model_version,
        }
    )
    return success_response(
        stats,
        message="Prediction monitoring stats",
        meta={"model_version": model_version},
    )

