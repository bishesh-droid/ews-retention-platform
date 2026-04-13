"""
Config package
--------------
Central configuration for the EWS Retention Platform.
All settings are read from environment variables with safe defaults,
so the application can run locally without a .env file.
"""

import os
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

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
TESTING: bool = os.getenv("TESTING", "false").lower() == "true"

# Force in-memory SQLite when TESTING=true, regardless of DATABASE_URL
DATABASE_URL: str
if TESTING:
    DATABASE_URL = "sqlite:///:memory:"
    logger = logging.getLogger(__name__)
    logger.info("TESTING=true: using in-memory SQLite database")
else:
    # In non-test environments, require explicit DATABASE_URL (PostgreSQL recommended)
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required. "
            "Example: postgresql://user:password@localhost/ews_db "
            "For SQLite (development only): sqlite:///./data.db"
        )
    DATABASE_URL = db_url

# ---------------------------------------------------------------------------
# Security / Auth
# ---------------------------------------------------------------------------
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").lower()

EWS_SERVICE_NAME: str = os.getenv("EWS_SERVICE_NAME", "ews-retention-platform")
EWS_TOKEN_AUDIENCE: str = os.getenv("EWS_TOKEN_AUDIENCE", "ews-api")

SECRET_KEY: str = os.getenv("SECRET_KEY", "")


# Validate on startup — crash immediately if misconfigured rather than running insecurely
def validate_security_config():
    # Validate SECRET_KEY
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    if len(SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters")
    if ENVIRONMENT != "development" and SECRET_KEY in ("dev", "test", "changeme", "secret"):
        raise RuntimeError("Insecure SECRET_KEY detected in non-development environment")

    # Validate against placeholder patterns in non-test environments
    if not TESTING and ENVIRONMENT != "development":
        _validate_no_placeholders("SECRET_KEY", SECRET_KEY)
        _validate_no_placeholders("CLAUDE_API_KEY", CLAUDE_API_KEY)
        _validate_no_placeholders("INTEGRATION_API_KEY_HASH", INTEGRATION_API_KEY_HASH)


def _validate_no_placeholders(name: str, value: str):
    """Raise RuntimeError if value is empty or contains placeholder patterns."""
    if not value:
        raise RuntimeError(
            f"{name} environment variable is not set. "
            "Generate a new secure value and update your .env file."
        )

    lower_value = value.lower()
    placeholder_patterns = [
        "change-this", "example", "placeholder", "your-", "changeme",
        "test", "dummy", "fake", "invalid", "none", "null", "0000000000000000"
    ]

    for pattern in placeholder_patterns:
        if pattern in lower_value:
            raise RuntimeError(
                f"{name} contains placeholder value '{pattern}'. "
                "Generate a new secure value and update your .env file."
            )

    # Detect live Anthropic API keys (sk-ant- prefix) in non-test environments
    if name == "CLAUDE_API_KEY" and value.startswith("sk-ant-"):
        raise RuntimeError(
            f"{name} appears to contain a live Anthropic API key. "
            "Generate a new key at https://console.anthropic.com/ and never commit it to version control."
        )


def validate_ml_config():
    """Validate ML configuration — crash on startup if weights don't sum to 1.0."""
    total = sum(FEATURE_WEIGHTS.values())
    if not (0.99 <= total <= 1.01):
        raise RuntimeError(
            f"FEATURE_WEIGHTS values sum to {total:.4f} — must equal 1.0. "
            f"Current weights: {FEATURE_WEIGHTS}"
        )


# ---------------------------------------------------------------------------
# ML Model Versioning (ML-2)
# ---------------------------------------------------------------------------
# Version string stored with every prediction for traceability and rollback.
# Update this when the scoring formula changes significantly.
# Format: {model-type}-v{major}.{minor}
RISK_MODEL_VERSION: str = os.getenv("RISK_MODEL_VERSION", "rule-based-v1.0")
# When XGBoost is re-enabled, set to: "xgboost-v2.1"


ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
RATE_LIMIT_LOGIN: str = os.getenv("RATE_LIMIT_LOGIN", "5/minute")
RATE_LIMIT_INGEST: str = os.getenv("RATE_LIMIT_INGEST", "10/hour")
RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "200/minute")

# ---------------------------------------------------------------------------
# File Upload
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))

# ---------------------------------------------------------------------------
# Integration / External APIs
# ---------------------------------------------------------------------------
INTEGRATION_API_KEY_HASH: str = os.getenv("INTEGRATION_API_KEY_HASH", "")
# This is the SHA-256 hash of the actual key, NOT the key itself
# Generate with: python -c "import hashlib; print(hashlib.sha256(b'your-key').hexdigest())"

# ---------------------------------------------------------------------------
# LLM / AI
# ---------------------------------------------------------------------------
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro-002")
# Note: update this deliberately when upgrading. Do not use aliases.
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

# Model type configuration:
# "rule_based" = deterministic weighted formula (current implementation)
# "xgboost" = reserved for future trained model — do not set until training pipeline exists
DEFAULT_MODEL_TYPE: str = os.getenv("DEFAULT_MODEL_TYPE", "rule_based")

# Rule-based RiskScorer + advisor explainability (risk_formula signal rollup).
# Logical keys map to FeatureEngineer outputs via backend.services.risk_scoring._LOGICAL_TO_FEATURE_KEY.
FEATURE_WEIGHTS: dict = {
    "content_completion": float(os.getenv("WEIGHT_CONTENT_COMPLETION", "0.30")),
    "login_consistency": float(os.getenv("WEIGHT_LOGIN_CONSISTENCY", "0.20")),
    "quiz_engagement": float(os.getenv("WEIGHT_QUIZ_ENGAGEMENT", "0.20")),
    "assignment": float(os.getenv("WEIGHT_ASSIGNMENT", "0.15")),
    "time_investment": float(os.getenv("WEIGHT_TIME_INVESTMENT", "0.08")),
    "discussion": float(os.getenv("WEIGHT_DISCUSSION", "0.02")),
    "self_directed_learning": float(os.getenv("WEIGHT_SELF_DIRECTED_LEARNING", "0.05")),  # risk reducer
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
RISK_SPIKE_THRESHOLD: float = float(os.getenv("RISK_SPIKE_THRESHOLD", "15.0"))

# Business / revenue
AVERAGE_STUDENT_LTV: float = float(os.getenv("AVERAGE_STUDENT_LTV", "150000.0"))
TUITION_PER_SEMESTER: float = float(os.getenv("TUITION_PER_SEMESTER", "75000.0"))
INTERVENTION_COST_PER_STUDENT: float = float(os.getenv("INTERVENTION_COST_PER_STUDENT", "500.0"))
TARGET_RETENTION_RATE: float = float(os.getenv("TARGET_RETENTION_RATE", "0.90"))

# ---------------------------------------------------------------------------
# Feature flags (D12-3)
# ---------------------------------------------------------------------------
ENABLE_CALENDAR_SCORER: bool = os.getenv("ENABLE_CALENDAR_SCORER", "true").lower() == "true"
ENABLE_LLM_FEATURES: bool = os.getenv("ENABLE_LLM_FEATURES", "true").lower() == "true"

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

# ---------------------------------------------------------------------------
# Academic calendar (trimester week for feature engineering & risk snapshots)
# ---------------------------------------------------------------------------
# ISO date (YYYY-MM-DD) for the first day (Monday) of week 1.
# Default set for Trimester-2 2026.
TRIMESTER_START_DATE: str = os.getenv("TRIMESTER_START_DATE", "2026-01-05")
CURRENT_SEMESTER_NAME: str = os.getenv("CURRENT_SEMESTER_NAME", "Trimester 2")
_TRIMESTER_START_DATE_DATE: date = date.fromisoformat(TRIMESTER_START_DATE)

# Calendar-based risk blending weight (0.0–1.0)
CALENDAR_RISK_BLEND_WEIGHT: float = float(os.getenv("CALENDAR_RISK_BLEND_WEIGHT", "0.4"))


def trimester_week_number(at: Optional[Union[datetime, date]] = None) -> Optional[int]:
    """
    1-based week index since TRIMESTER_START_DATE.
    Returns None if `at` (or today) is before the trimester start.
    """
    if at is not None:
        ref = at.date() if isinstance(at, datetime) else at
    else:
        ref = date.today()
    delta_days = (ref - _TRIMESTER_START_DATE_DATE).days
    if delta_days < 0:
        return None
    return (delta_days // 7) + 1
