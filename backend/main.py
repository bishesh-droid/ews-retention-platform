"""
EWS Retention Platform API
--------------------------
Application entry point.
"""

import asyncio
import time
import traceback

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import API_HOST, API_PORT, CORS_ORIGINS
from backend.database.connection import init_db
from backend.database.session import SessionLocal
from backend.routes import api_router
from backend.core.logger import sys_logger
from backend.middleware.security_logging import security_and_logging_middleware
from backend.middleware.request_validation import request_validation_middleware
from backend.services.infrastructure.scheduler import scheduler_service
from backend.utils.api import AppError, error_response, success_response


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown sequence."""
    sys_logger.info("Starting EWS Retention Platform API...")

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
        await scheduler_service.start()
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

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
    """Liveness probe — returns 200 when the server is up."""
    return success_response(
        {"status": "healthy", "timestamp": time.time()},
        message="OK",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=API_HOST, port=API_PORT, reload=True)
