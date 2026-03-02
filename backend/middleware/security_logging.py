"""
Security and access logging middleware.
"""

import time
import traceback
from typing import Dict, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.core.logger import sys_logger


rate_limit_store: Dict[str, Tuple[float, int]] = {}


async def security_and_logging_middleware(request: Request, call_next):
    """
    Combined rate limiting and structured access logging.

    Preserves the original behavior from backend.main.
    """
    client_ip = request.client.host
    current_time = time.time()

    # Rate Limiting Logic (100 req / minute per IP)
    if client_ip in rate_limit_store:
        last_time, count = rate_limit_store[client_ip]
        if current_time - last_time < 60:
            if count >= 100:
                sys_logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return JSONResponse(status_code=429, content={"detail": "Too many requests"})
            rate_limit_store[client_ip] = (last_time, count + 1)
        else:
            rate_limit_store[client_ip] = (current_time, 1)
    else:
        rate_limit_store[client_ip] = (current_time, 1)

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
    except Exception as e:
        sys_logger.error(
            f"Unhandled Server Error on {request.method} {request.url.path}: {str(e)}\n"
            f"{traceback.format_exc()}"
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."},
        )

