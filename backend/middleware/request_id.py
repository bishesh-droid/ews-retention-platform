"""
Request ID Middleware

Assigns a unique request ID to every incoming request for tracing and logging.
Accepts X-Request-ID from client or generates a UUID.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a request ID to each request.
    
    - Checks for X-Request-ID header from client (useful for tracing across services)
    - Generates a short UUID if no header provided
    - Makes request_id available via request.state.request_id
    - Returns X-Request-ID in response headers for client correlation
    """
    
    async def dispatch(self, request: Request, call_next):
        # Use client-provided request ID or generate one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # Process the request
        response = await call_next(request)
        
        # Include request ID in response headers
        response.headers["X-Request-ID"] = request_id
        return response
