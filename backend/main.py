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
from backend.services.core.data_ingestion import ingest_all_data
from backend.core.logger import sys_logger
from backend.core.security import security_manager


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
rate_limit_store = {}

@app.middleware("http")
async def security_and_logging_middleware(request: Request, call_next):
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
        sys_logger.info(f"Request completed: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
        return response
    except Exception as e:
        sys_logger.error(f"Unhandled Server Error on {request.method} {request.url.path}: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Please try again later."}
        )

# Include API Router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    sys_logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to the EWS Retention Platform API v2",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for monitoring uptime."""
    sys_logger.info("Health check endpoint pinged")
    return {
        "status": "healthy",
        "uptime": "ok",
        "timestamp": time.time()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=API_HOST, port=API_PORT, reload=True)