import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from backend.api.deps import get_current_user
from backend.database.models.user import User


# Check if we're in test mode
IS_TESTING = os.environ.get("TESTING", "false").lower() == "true"


def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key - returns a unique key per test when TESTING is set."""
    if IS_TESTING:
        # In tests, use a unique key per request to avoid rate limits
        import uuid
        return f"test-{uuid.uuid4()}"
    return get_remote_address(request)


# Default global limiter (IP-based for non-authenticated routes)
# When TESTING, use unlimited by default
if IS_TESTING:
    limiter = Limiter(key_func=get_rate_limit_key, default_limits=[])
else:
    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# ---------------------------------------------------------------------------
# User-based rate limiting for authenticated endpoints
# ---------------------------------------------------------------------------
#
# Redis key naming convention for per-user rate limits:
#   llm_ratelimit:{user_id}:{window}
#
# Examples:
#   llm_ratelimit:42:per_minute  -> sliding window for 5 req/min limit
#   llm_ratelimit:42:per_hour    -> sliding window for 20 req/hour limit
#
# This ensures limits are per-user, not global across all users.
# ---------------------------------------------------------------------------

def get_user_id_from_request(request: Request) -> str:
    """Extract user ID from request state (set by get_current_user dependency)."""
    # Try to get user from request state (injected by auth dependencies)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return str(user.id)
    # Fallback: check if user_id was set directly on state
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return str(user_id)
    # Final fallback to remote address (shouldn't happen for auth routes)
    return get_remote_address(request)


# LLM-specific rate limits (per authenticated user)
# 5 requests per minute, 20 requests per hour
LLM_RATE_LIMIT_MINUTE = "5/minute"
LLM_RATE_LIMIT_HOUR = "20/hour"


def get_llm_limiter_key(request: Request) -> str:
    """Generate per-user key for LLM rate limiting."""
    return f"llm:{get_user_id_from_request(request)}"


async def llm_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom 429 handler for LLM rate limits with Retry-After header."""
    retry_after = getattr(exc, "retry_after", 60)
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "LLM rate limit exceeded. Please wait before retrying.",
            "retry_after": retry_after,
            "limit_type": "llm_per_user",
        },
        headers={"Retry-After": str(retry_after)},
    )


def require_llm_rate_limit():
    """
    Dependency factory that enforces per-user LLM rate limits.

    Limits: 5 requests per minute, 20 requests per hour per authenticated user.

    Usage:
        @router.post("/advice")
        def get_advice(
            request: Request,
            current_user: User = Depends(get_current_user),
            _rate_limit: None = Depends(require_llm_rate_limit()),
        ):
            ...

    Redis keys follow the convention:
        llm_ratelimit:{user_id}:{window}
    """
    def check_rate_limit(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> None:
        # Store user on request state for key function access
        request.state.user = current_user

        # Use the limiter's limit decorator logic directly
        # Check minute window (5/min)
        minute_key = f"llm_ratelimit:{current_user.id}:per_minute"
        hour_key = f"llm_ratelimit:{current_user.id}:per_hour"

        # Get storage backend from limiter
        storage = getattr(limiter, '_storage', None)
        if storage is None or not hasattr(storage, 'incr'):
            logger.warning("Rate limiter storage unavailable — skipping LLM rate limit check")
            return  # Degrade gracefully

        # Check minute limit (5/min)
        minute_count = storage.incr(minute_key, 60)  # type: ignore[union-attr]
        if int(minute_count) > 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: 5 requests per minute. Please wait.",
                headers={"Retry-After": str(storage.get_expiry(minute_key))},  # type: ignore[union-attr]
            )

        # Check hour limit (20/hour)
        hour_count = storage.incr(hour_key, 3600)  # type: ignore[union-attr]
        if int(hour_count) > 20:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: 20 requests per hour. Please wait.",
                headers={"Retry-After": str(storage.get_expiry(hour_key))},  # type: ignore[union-attr]
            )

    return check_rate_limit


async def rate_limit_exceeded_handler(request: Request, exc: Exception):
    """
    Handler for rate limit exceeded exceptions.
    Defensively handles any exception type since slowapi may pass non-RateLimitExceeded exceptions.
    """
    # Safely extract retry_after if available
    retry_after = getattr(exc, "retry_after", 60)
    # Safely extract detail message - don't assume .detail attribute exists
    detail = getattr(exc, "detail", None) or str(exc) or "Rate limit exceeded"
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please wait before retrying.",
            "retry_after": retry_after,
            "info": str(detail),
        },
        headers={"Retry-After": str(retry_after)},
    )
