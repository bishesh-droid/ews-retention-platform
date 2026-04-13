"""
Standardized Error Response Handling (SOA Unified Schema)

Provides consistent error shapes across the API with request ID tracking.
All error responses follow the unified SOA format:

{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {},
    "request_id": "req_xxx",
    "timestamp": "2026-04-13T..."
  }
}
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pydantic import BaseModel
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "make_error",
    "http_exception_handler",
    "validation_exception_handler",
    "unhandled_exception_handler",
]


class ErrorDetail(BaseModel):
    """Nested error detail structure for SOA unified error format."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: str
    timestamp: str


class ErrorResponse(BaseModel):
    """SOA unified error response structure."""
    error: ErrorDetail


def make_error(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> dict:
    """
    Create a standardized SOA error response dictionary.

    Args:
        code: Error code (e.g., "VALIDATION_ERROR", "NOT_FOUND")
        message: Human-readable error message
        details: Optional dictionary with additional error details
        request_id: Request tracking ID for support correlation

    Returns:
        Dictionary matching the SOA unified error format
    """
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id or "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler for HTTPException with SOA unified response shape."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"HTTPException [{exc.status_code}] {request.method} {request.url.path}: {exc.detail}")

    # Map status code to error code
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    error_code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")

    return JSONResponse(
        status_code=exc.status_code,
        content=make_error(
            code=error_code,
            message=str(exc.detail),
            request_id=request_id
        ),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for request validation errors (422) with SOA unified format."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"Validation error {request.method} {request.url.path}: {exc.errors()}")

    # Format validation errors into a structured details dict
    validation_details = {"errors": exc.errors()}

    return JSONResponse(
        status_code=422,
        content=make_error(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=validation_details,
            request_id=request_id
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handler for unhandled exceptions — returns safe generic message in SOA format."""
    request_id = getattr(request.state, "request_id", None)
    logger.exception(f"Unhandled exception [request_id={request_id}] {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content=make_error(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            request_id=request_id
        ),
    )


# Backward compatibility alias
error_response = make_error
