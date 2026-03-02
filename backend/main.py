"""
EWS Retention Platform API
-------------------------
Main application entry point.
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import traceback

from backend.config import API_HOST, API_PORT, CORS_ORIGINS
from backend.database import init_db, SessionLocal
from backend.routes import api_router
from backend.data_ingestion import ingest_all_data
from backend.core.logger import sys_logger
from backend.core.security import security_manager
from backend.middleware.security_logging import security_and_logging_middleware
from backend.middleware.request_validation import request_validation_middleware
from backend.utils.api import AppError, error_response, success_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    sys_logger.info("Starting EWS Retention Platform API...")
    init_db()
    sys_logger.info("Database initialized.")

    # Ingest XLSX data on first run
    db = SessionLocal()
    try:
        ingest_all_data(db)
    except Exception as e:
        sys_logger.error(f"Data ingestion error: {e}")
    finally:
        db.close()

    yield
    
    # Shutdown
    sys_logger.info("Shutting down...")


# Initialize App
app = FastAPI(
    title="EWS Retention Platform",
    description="Early Warning System for Student Retention with AI-driven interventions.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting & Access Logging Middleware
app.middleware("http")(security_and_logging_middleware)

# Request validation middleware
app.middleware("http")(request_validation_middleware)


# Centralised error handlers
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """
    Handle known application-level errors and return consistent JSON.
    """
    sys_logger.warning(f"AppError on {request.method} {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.message, exc.details),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Override default HTTPException handler to return a consistent JSON error format
    while preserving the original status code and detail message.
    """
    sys_logger.warning(
        f"HTTPException on {request.method} {request.url.path}: "
        f"{exc.status_code} {exc.detail}"
    )
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(detail),
    )

# Include API Router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    sys_logger.info("Root endpoint accessed")
    payload = {
        "message": "Welcome to the EWS Retention Platform API v2",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }
    return success_response(payload, message="EWS API root")

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for monitoring uptime."""
    sys_logger.info("Health check endpoint pinged")
    payload = {
        "status": "healthy",
        "uptime": "ok",
        "timestamp": time.time(),
    }
    return success_response(payload, message="Health check OK")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=API_HOST, port=API_PORT, reload=True)