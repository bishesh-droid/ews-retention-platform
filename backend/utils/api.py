"""
API utilities
-------------
Shared response builders and error types for controllers and services.

All HTTP JSON responses should use the standard envelope:

{
  "success": boolean,
  "message": string,
  "data": object | array | null,
  "meta": {
    "pagination"?: object,
    "model_version"?: string,
    "timestamp"?: string
  }
}
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone


class AppError(Exception):
    """Base application-level error with an HTTP status code and payload."""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, details=details)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=422, details=details)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=409, details=details)


def _build_meta(
    base_meta: Optional[Dict[str, Any]] = None,
    pagination: Optional[Dict[str, Any]] = None,
    model_version: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    meta: Dict[str, Any] = dict(base_meta or {})

    if pagination is not None:
        meta.setdefault("pagination", pagination)
    if model_version is not None:
        meta.setdefault("model_version", model_version)

    # Always attach an ISO timestamp for traceability
    meta.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    return meta or None


def success_response(
    data: Any,
    message: str = "OK",
    *,
    meta: Optional[Dict[str, Any]] = None,
    pagination: Optional[Dict[str, Any]] = None,
    model_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a standardized success response envelope.

    - `data` can be any JSON-serializable object/array/null
    - `message` is a human-readable summary
    - `meta` may include pagination/model_version/timestamp, etc.
    """
    return {
        "success": True,
        "message": message,
        "data": data,
        "meta": _build_meta(meta, pagination=pagination, model_version=model_version),
    }


def error_response(message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Build a standardized error response envelope.
    """
    return {
        "success": False,
        "message": message,
        "data": details or {},
        "meta": _build_meta(),
    }

