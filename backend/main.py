"""
EWS Retention Platform API
-------------------------
Main application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import API_HOST, API_PORT, CORS_ORIGINS, LOG_LEVEL
from backend.database import init_db, SessionLocal
from backend.routes import api_router
from backend.services.core.data_ingestion import ingest_all_data

import logging

# Configure logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting EWS Retention Platform API...")
    init_db()
    logger.info("Database initialized.")

    # Ingest XLSX data on first run
    db = SessionLocal()
    try:
        ingest_all_data(db)
    except Exception as e:
        logger.error(f"Data ingestion error: {e}")
    finally:
        db.close()

    yield
    
    # Shutdown
    logger.info("Shutting down...")


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

# Rate Limiting Middleware (Simple IP-based)
from fastapi import Request, HTTPException
import time
rate_limit_store = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    current_time = time.time()
    if client_ip in rate_limit_store:
        last_time, count = rate_limit_store[client_ip]
        if current_time - last_time < 60:
            if count >= 100:
                from fastapi.responses import JSONResponse
                return JSONResponse(status_code=429, content={"detail": "Too many requests"})
            rate_limit_store[client_ip] = (last_time, count + 1)
        else:
            rate_limit_store[client_ip] = (current_time, 1)
    else:
        rate_limit_store[client_ip] = (current_time, 1)
    return await call_next(request)

# Include API Router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the EWS Retention Platform API v2",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=API_HOST, port=API_PORT, reload=True)