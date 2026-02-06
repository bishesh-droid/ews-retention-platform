"""
Services Package
---------------
Business logic and service layer for the EWS Retention Platform.
"""

# Use relative imports to avoid circular dependencies
try:
    from .ai import get_ai_advice
    from .core import (
        calculate_student_risk,
        batch_predict,
        get_signal_summary,
        ingest_data,
    )
except ImportError:
    # Fallback for tests
    pass

__all__ = [
    "get_ai_advice",
    "calculate_student_risk",
    "batch_predict",
    "get_signal_summary",
    "ingest_data",
]
