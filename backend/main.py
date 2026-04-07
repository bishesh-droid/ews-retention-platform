"""
EWS Retention Platform API
--------------------------
Application entry point.
"""

import asyncio
import time
import traceback
import socket
import os
from urllib.parse import urlparse

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from slowapi import Limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from backend.config import API_HOST, API_PORT, CORS_ORIGINS, REDIS_URL, ENVIRONMENT
from backend.database.connection import init_db, SessionLocal
from backend.routes import api_router
from backend.core.logger import sys_logger
from backend.middleware.security_logging import security_and_logging_middleware
from backend.middleware.request_validation import request_validation_middleware
from backend.services.infrastructure.scheduler import scheduler_service
from backend.services.ml_service import ml_service
from backend.utils.api import AppError, error_response, success_response


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

def check_redis_connection() -> bool:
    """Verify Redis is reachable before accepting traffic."""
    try:
        # Parse REDIS_URL (format: redis://host:port/db)
        # Simple parsing for common format
        url = REDIS_URL.replace("redis://", "")
        host_port = url.split("/")[0]  # Remove database number
        if ":" in host_port:
            host, port_str = host_port.rsplit(":", 1)
            port = int(port_str)
        else:
            host, port = host_port, 6379

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        sys_logger.error(f"Redis health check failed: {e}")
        return False


def parse_cors_origins(raw_origins) -> list[str]:
    """
    Normalize CORS origins from config/env:
    - strips whitespace
    - removes empties
    - de-duplicates preserving order
    """
    if isinstance(raw_origins, str):
        candidates = [p.strip() for p in raw_origins.split(",")]
    else:
        candidates = [str(p).strip() for p in (raw_origins or [])]
    cleaned = [c for c in candidates if c]
    return list(dict.fromkeys(cleaned))


def validate_environment() -> None:
    """Fail-fast validation for critical runtime configuration."""
    errors = []

    if not (1 <= int(API_PORT) <= 65535):
        errors.append(f"API_PORT must be in [1, 65535], got {API_PORT}")

    parsed_redis = urlparse(REDIS_URL)
    if parsed_redis.scheme not in {"redis", "rediss"} or not parsed_redis.hostname:
        errors.append(f"REDIS_URL must be a valid redis:// URL, got '{REDIS_URL}'")

    origins = parse_cors_origins(CORS_ORIGINS)
    if not origins:
        errors.append("CORS_ORIGINS resolved to empty list")

    if errors:
        raise RuntimeError("Environment validation failed: " + "; ".join(errors))


def check_db_connection() -> bool:
    """Verify DB connectivity via lightweight query."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        sys_logger.error(f"Database health check failed: {exc}")
        return False
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown sequence."""
    sys_logger.info("Starting EWS Retention Platform API...")
    validate_environment()

    # Health check Redis and select limiter backend.
    redis_ok = check_redis_connection()
    limiter_storage_uri = REDIS_URL
    if not redis_ok:
        message = (
            "Redis is not reachable. Ensure Redis is running and REDIS_URL is correct. "
            f"Attempted connection to: {REDIS_URL}"
        )
        if ENVIRONMENT == "development":
            sys_logger.warning(
                message
                + " Using in-memory rate limiter because ENVIRONMENT=development."
            )
            limiter_storage_uri = "memory://"
        else:
            raise RuntimeError(message)
    else:
        sys_logger.info("Redis connection verified.")

    # Initialize rate limiter with selected backend.
    try:
        limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=limiter_storage_uri,
            default_limits=["100/minute"],
        )
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        sys_logger.info(f"Rate limiter initialized with backend: {limiter_storage_uri}")
    except Exception as e:
        sys_logger.error(f"Failed to initialize rate limiter: {e}")
        raise

    # Create DB tables synchronously (fast, local SQLite)
    init_db()
    sys_logger.info("Database initialised.")

    # Run XLSX ingestion off the event loop so startup is non-blocking.
    # If ingestion fails the server still starts — it just won't have data.
    async def _run_ingestion():
        try:
            from backend.services.core.data_ingestion import ingest_all_data
            def _run_ingestion_in_thread():
                db = SessionLocal()
                try:
                    ingest_all_data(db)
                    # Services flush; commit here to finalize the transaction.
                    db.commit()
                    sys_logger.info("Data ingestion complete.")
                except Exception:
                    db.rollback()
                    raise
                finally:
                    db.close()

            await asyncio.to_thread(_run_ingestion_in_thread)
        except Exception as exc:
            sys_logger.error(f"Data ingestion error (non-fatal): {exc}")

    asyncio.create_task(_run_ingestion())

    try:
        await scheduler_service.start(run_daily_on_startup=True)
        sys_logger.info(f"Scheduler status after startup: {scheduler_service.get_status()}")
    except Exception as exc:
        sys_logger.error(f"Scheduler startup error (non-fatal): {exc}")

    yield

    try:
        await scheduler_service.stop()
    except Exception as exc:
        sys_logger.error(f"Scheduler shutdown error: {exc}")

    sys_logger.info("Shutting down EWS Retention Platform API.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="EWS Retention Platform",
    description=(
        "Early Warning System for Student Retention — "
        "AI-driven risk prediction and intervention management."
    ),
    version="2.1.0",
    lifespan=lifespan,
)

# CORS
CORS_ORIGINS_NORMALIZED = parse_cors_origins(CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS_NORMALIZED,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiting middleware (slowapi with Redis backend)
# Note: The limiter instance is stored in app.state.limiter during lifespan startup
app.add_middleware(SlowAPIMiddleware)

# Custom middleware (applied last-registered = outermost)
app.middleware("http")(security_and_logging_middleware)
app.middleware("http")(request_validation_middleware)


# ---------------------------------------------------------------------------
# Centralised exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    sys_logger.warning(
        f"AppError [{exc.status_code}] {request.method} {request.url.path}: {exc.message}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.message, exc.details),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    sys_logger.warning(
        f"HTTPException [{exc.status_code}] {request.method} {request.url.path}: {exc.detail}"
    )
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(detail),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    sys_logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}\n"
        + traceback.format_exc()
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response("An internal server error occurred."),
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(api_router, prefix="/api/v1")


# ---------------------------------------------------------------------------
# System endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["System"])
def read_root():
    return success_response(
        {"docs_url": "/docs", "redoc_url": "/redoc"},
        message="EWS Retention Platform API v2.1",
    )


@app.get("/health", tags=["System"])
def health_check():
    """Health probe with dependency checks for production readiness."""
    db_ok = check_db_connection()
    redis_ok = check_redis_connection()
    ml_stats = ml_service.get_runtime_stats()
    ml_ok = ml_stats is not None and "model_status" in ml_stats
    healthy = db_ok and redis_ok and ml_ok

    payload = {
        "status": "healthy" if healthy else "degraded",
        "timestamp": time.time(),
        "checks": {
            "database": db_ok,
            "redis": redis_ok,
            "ml_pipeline": ml_ok,
        },
        "ml": ml_stats,
    }
    http_status = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=http_status, content=success_response(payload, message="OK"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    env = os.getenv("ENVIRONMENT", "development").lower()
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=(env == "development"),
    )
