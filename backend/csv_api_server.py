"""
CSV-Driven API Server for EWS Retention Platform.

This is a standalone server that provides only the CSV-driven endpoints
without dependencies on the existing LLM/AI infrastructure.

Run with: python csv_api_server.py
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.database import init_db
import sys
sys.path.insert(0, '/home/duffer/Music/ews-retention-platform/backend')

# Import router directly, avoiding the routes __init__.py
from backend.app.api import routes
students_router = routes.students.router

# Initialize FastAPI app
app = FastAPI(
    title="EWS Retention Platform - CSV API",
    description="CSV-driven analytics and risk scoring API",
    version="1.0.0"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React/Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include CSV-driven routes
app.include_router(students_router, prefix="/api/v1", tags=["students"])


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    print("Initializing database...")
    init_db()
    print("Database ready!")


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "EWS CSV-Driven API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "overview": "/api/v1/overview",
            "students_list": "/api/v1/students",
            "student_detail": "/api/v1/students/{id}",
            "risk_distribution": "/api/v1/risk-distribution",
            "analytics": "/api/v1/analytics/trends"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    print("="*60)
    print(" EWS Retention Platform - CSV API Server")
    print("="*60)
    print(" API Docs: http://localhost:8000/docs")
    print(" Frontend: Configure to use http://localhost:8000/api/v1")
    print("="*60)
    
    uvicorn.run(
        "csv_api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
