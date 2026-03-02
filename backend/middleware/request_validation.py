"""
Request validation middleware
-----------------------------
Lightweight request-level validation that complements Pydantic:

- Enforces JSON content-type for methods that are expected to carry a JSON body.
- Optionally can be extended to apply global constraints (payload size limits, etc.).
"""

from typing import Iterable

from fastapi import Request
from fastapi.responses import JSONResponse


JSON_METHODS: Iterable[str] = ("POST", "PUT", "PATCH")


async def request_validation_middleware(request: Request, call_next):
    # Enforce JSON Content-Type for mutating methods when a body is present
    if request.method in JSON_METHODS:
        content_type = request.headers.get("content-type", "")
        # Allow typical JSON content types; let empty bodies pass through
        if request.headers.get("content-length") not in (None, "0"):
            if "application/json" not in content_type:
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": {
                            "message": "Unsupported Media Type. Expected application/json.",
                            "details": {"content_type": content_type},
                        }
                    },
                )

    response = await call_next(request)
    return response

