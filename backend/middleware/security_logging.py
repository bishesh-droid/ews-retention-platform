"""
Security and access logging middleware.

Rate limiting is handled by slowapi with Redis backend (configured in main.py).
This middleware focuses on logging request/response metrics.
"""

import time
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from backend.core.logger import sys_logger


async def security_and_logging_middleware(request: Request, call_next):
    """
    Access logging middleware with distributed rate limiting via slowapi/Redis.

    Rate limiting is handled by the slowapi limiter attached to the app.
    This middleware focuses on logging request/response metrics.
    """
    client_ip = request.client.host

    # Log Request
    sys_logger.info(f"Incoming request: {request.method} {request.url.path} from {client_ip}")

    try:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        sys_logger.info(
            f"Request completed: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Time: {process_time:.4f}s"
        )
        return response
    except RateLimitExceeded:
        # This should be caught by the slowapi exception handler,
        # but log it here as well for visibility
        sys_logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise
    except Exception as e:
        sys_logger.error(
            f"Unhandled Server Error on {request.method} {request.url.path}: {str(e)}\n"
            f"{traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."},
        )
