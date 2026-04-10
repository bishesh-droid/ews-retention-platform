"""
Standardized Error Response Handling

Provides consistent error shapes across the API with request ID tracking.
"""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def error_response(status_code: int, message: str, detail: str = None, request_id: str = None) -> dict:
    """
    Single standard error shape used everywhere in the API.

    Args:
        status_code: HTTP status code
        message: Human-readable error message
        detail: Optional additional details (sanitized for client exposure)
        request_id: Request tracking ID for support correlation

    Returns:
        Standardized error response dictionary
    """
    body = {
        "error": {
            "status": status_code,
            "message": message,
        }
    }
    if detail:
        body["error"]["detail"] = detail
    if request_id:
        body["error"]["request_id"] = request_id
    return body


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handler for HTTPException with standardized response shape."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"HTTPException [{exc.status_code}] {request.method} {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.status_code, str(exc.detail), request_id=request_id),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for request validation errors (422)."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"Validation error {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content=error_response(
            422,
            "Validation error",
            detail=str(exc.errors()),
            request_id=request_id
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handler for unhandled exceptions — returns safe generic message."""
    request_id = getattr(request.state, "request_id", None)
    logger.exception(f"Unhandled exception [request_id={request_id}] {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content=error_response(500, "Internal server error", request_id=request_id),
    )
