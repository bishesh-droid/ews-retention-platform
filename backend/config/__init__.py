"""
Config package
--------------
Central configuration for the EWS Retention Platform.
All settings are read from environment variables with safe defaults,
so the application can run locally without a .env file.
"""

import os
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Base paths
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent  # .../backend/
DATA_DIR = BACKEND_DIR / "data"

# ---------------------------------------------------------------------------
# API / Server
# ---------------------------------------------------------------------------
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS: list = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000"
).split(",")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'sql_app.db'}"
)

# ---------------------------------------------------------------------------
# Security / Auth
# ---------------------------------------------------------------------------
_INSECURE_DEFAULT_KEY = "CHANGE_ME_IN_PRODUCTION_a3f9c2e1b7d4e8f0a1b2c3d4e5f60718"
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()

SECRET_KEY: str = os.getenv("SECRET_KEY", _INSECURE_DEFAULT_KEY)

# Fail-fast: never allow the default key in production.
if ENVIRONMENT == "production" and SECRET_KEY == _INSECURE_DEFAULT_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable must be set to a strong, unique value in "
        "production. The hardcoded development default is NOT acceptable."
    )

ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ---------------------------------------------------------------------------
# Integration / External APIs
# ---------------------------------------------------------------------------
INTEGRATION_API_KEY: str = os.getenv("INTEGRATION_API_KEY", "")

# ---------------------------------------------------------------------------
# LLM / AI
# ---------------------------------------------------------------------------
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: int = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
LOG_FILE: str = os.getenv("LOG_FILE", str(BACKEND_DIR / "backend.log"))

# ---------------------------------------------------------------------------
# Redis Cache
# ---------------------------------------------------------------------------
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_EXPIRE_SECONDS: int = int(os.getenv("CACHE_EXPIRE_SECONDS", "300"))

# ---------------------------------------------------------------------------
# ML / Risk thresholds  (0-100 scale — matches RiskScorer output)
# ---------------------------------------------------------------------------
# High  : risk_score >= 70  → urgent intervention
# Medium: risk_score >= 40  → proactive outreach
# Low   : risk_score <  40  → monitoring only
RISK_THRESHOLD_HIGH: float = float(os.getenv("RISK_THRESHOLD_HIGH", "70.0"))
RISK_THRESHOLD_MEDIUM: float = float(os.getenv("RISK_THRESHOLD_MEDIUM", "40.0"))
RISK_THRESHOLD_LOW: float = float(os.getenv("RISK_THRESHOLD_LOW", "20.0"))

DEFAULT_MODEL_TYPE: str = os.getenv("DEFAULT_MODEL_TYPE", "xgboost")

SIGNAL_WEIGHTS: dict = {
    "attendance": float(os.getenv("WEIGHT_ATTENDANCE", "0.35")),
    "grades": float(os.getenv("WEIGHT_GRADES", "0.30")),
    "engagement": float(os.getenv("WEIGHT_ENGAGEMENT", "0.20")),
    "submissions": float(os.getenv("WEIGHT_SUBMISSIONS", "0.15")),
}

# ---------------------------------------------------------------------------
# Intervention thresholds & business logic
# ---------------------------------------------------------------------------
INTERVENTION_THRESHOLDS: dict = {
    "no_action": float(os.getenv("THRESHOLD_NO_ACTION", "30.0")),
    "gentle_reminder": float(os.getenv("THRESHOLD_GENTLE", "40.0")),
    "mentor_outreach": float(os.getenv("THRESHOLD_MENTOR", "60.0")),
    "urgent": float(os.getenv("THRESHOLD_URGENT", "80.0")),
}

INTERVENTION_COOLDOWN_DAYS: int = int(os.getenv("INTERVENTION_COOLDOWN_DAYS", "7"))
RISK_SPIKE_THRESHOLD: float = float(os.getenv("RISK_SPIKE_THRESHOLD", "0.15"))

# Business / revenue
AVERAGE_STUDENT_LTV: float = float(os.getenv("AVERAGE_STUDENT_LTV", "150000.0"))
TUITION_PER_SEMESTER: float = float(os.getenv("TUITION_PER_SEMESTER", "75000.0"))
INTERVENTION_COST_PER_STUDENT: float = float(os.getenv("INTERVENTION_COST_PER_STUDENT", "500.0"))
TARGET_RETENTION_RATE: float = float(os.getenv("TARGET_RETENTION_RATE", "0.90"))

# ---------------------------------------------------------------------------
# Data file paths
# ---------------------------------------------------------------------------
# Primary engagement data snapshot
ENGAGEMENT_DATA_PATH = DATA_DIR / os.getenv(
    "ENGAGEMENT_DATA_FILE", "Engagement_Analysis.xlsx"
)

# Quiz / exam data
QUIZ_EXAM_DATA_PATH = DATA_DIR / os.getenv(
    "QUIZ_EXAM_DATA_FILE",
    "_Trimester-1 2025 Attendance Quiz-Assignment-Exam 5Jan2025.xlsx"
)

# Additional snapshot files (may or may not exist — ingestion skips missing files)
WEEK12_ENGAGEMENT_PATH = DATA_DIR / os.getenv(
    "WEEK12_ENGAGEMENT_FILE",
    "Week 1-2 Student Engagement Analysis.xlsx"
)
QUIZ_STATUS_9FEB_PATH = DATA_DIR / os.getenv(
    "QUIZ_STATUS_9FEB_FILE",
    "Graded Quiz 1 Status 9 Feb.xlsx"
)
GRADED_QUIZ_10FEB_ORIG_PATH = DATA_DIR / os.getenv(
    "GRADED_QUIZ_10FEB_ORIG_FILE",
    "graded quiz 1 10 feb complete.xlsx"
)
GRADED_QUIZ_10FEB_1115AM_PATH = DATA_DIR / os.getenv(
    "GRADED_QUIZ_10FEB_1115AM_FILE",
    "graded quiz 1 10 feb 11 15 AM.xlsx"
)
GRADED_QUIZ_10FEB_451PM_PATH = DATA_DIR / os.getenv(
    "GRADED_QUIZ_10FEB_451PM_FILE",
    "graded quiz 1 10 feb 4 51 PM.xlsx"
)
WEEK3_USAGE_PATH = DATA_DIR / os.getenv(
    "WEEK3_USAGE_FILE",
    "Learner usage week 3.xlsx"
)
WEEK5_USAGE_PATH = DATA_DIR / os.getenv(
    "WEEK5_USAGE_FILE",
    "Learner usage week 5.xlsx"
)

# ML training sample data
SAMPLE_DATA_PATH = DATA_DIR / os.getenv("SAMPLE_DATA_FILE", "labels.csv")
