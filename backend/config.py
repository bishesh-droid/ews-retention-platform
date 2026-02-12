"""
Backend Configuration
--------------------
Centralized configuration for the EWS Retention Platform.
All environment-based settings and path configurations.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ========== Paths ==========
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
DATA_DIR = BACKEND_DIR / "data"
ML_MODELS_DIR = BACKEND_DIR / "ml" / "models" / "saved"
PROMPTS_DIR = BASE_DIR / "docs" / "prompts"

# ========== Database ==========
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/sql_app.db")

# ========== ML Configuration ==========
DEFAULT_MODEL_TYPE = os.getenv("MODEL_TYPE", "xgboost")
MODEL_VERSION = os.getenv("MODEL_VERSION", "v1.0")

# Risk thresholds (for UI categorization)
RISK_THRESHOLD_HIGH = float(os.getenv("RISK_THRESHOLD_HIGH", "0.7"))
RISK_THRESHOLD_MEDIUM = float(os.getenv("RISK_THRESHOLD_MEDIUM", "0.4"))
RISK_THRESHOLD_LOW = float(os.getenv("RISK_THRESHOLD_LOW", "0.0"))

# ========== Intervention Decision Thresholds ==========
# These thresholds determine which intervention action is triggered
# All values are probabilities in [0.0, 1.0] range
INTERVENTION_THRESHOLDS = {
    'no_action': float(os.getenv("THRESHOLD_NO_ACTION", "0.30")),      # < 30%: No intervention
    'gentle_reminder': float(os.getenv("THRESHOLD_GENTLE", "0.60")),  # 30-60%: Automated email
    'mentor_outreach': float(os.getenv("THRESHOLD_MENTOR", "0.80")),  # 60-80%: Faculty + email
    'urgent': float(os.getenv("THRESHOLD_URGENT", "0.80")),           # >= 80%: Sales + WhatsApp
}

# Intervention cooldown (minimum days between interventions per student)
INTERVENTION_COOLDOWN_DAYS = int(os.getenv("INTERVENTION_COOLDOWN_DAYS", "7"))

# Risk change threshold that triggers intervention even during cooldown
RISK_SPIKE_THRESHOLD = float(os.getenv("RISK_SPIKE_THRESHOLD", "0.15"))

# ========== Signal Weights for Risk Calculation ==========
# These weights determine contribution of each signal to final risk score
# Must sum to 1.0
SIGNAL_WEIGHTS = {
    'academic': float(os.getenv("WEIGHT_ACADEMIC", "0.30")),
    'engagement': float(os.getenv("WEIGHT_ENGAGEMENT", "0.25")),
    'consistency': float(os.getenv("WEIGHT_CONSISTENCY", "0.20")),
    'intent': float(os.getenv("WEIGHT_INTENT", "0.15")),
    'responsiveness': float(os.getenv("WEIGHT_RESPONSIVENESS", "0.10")),
}

# ========== Business Metrics Configuration ==========
AVERAGE_STUDENT_LTV = float(os.getenv("AVERAGE_STUDENT_LTV", "12500.0"))
TUITION_PER_SEMESTER = float(os.getenv("TUITION_PER_SEMESTER", "6250.0"))
INTERVENTION_COST_PER_STUDENT = float(os.getenv("INTERVENTION_COST", "350.0"))
TARGET_RETENTION_RATE = float(os.getenv("TARGET_RETENTION_RATE", "0.95"))

# ========== LLM Configuration ==========
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))

# ========== API Configuration ==========
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8000",
]

# Additional CORS origins from environment
additional_origins = os.getenv("CORS_ORIGINS", "")
if additional_origins:
    CORS_ORIGINS.extend([origin.strip() for origin in additional_origins.split(",")])

# ========== Data Ingestion ==========
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
ENGAGEMENT_DATA_PATH = RAW_DATA_DIR / "Engagement_Analysis.xlsx"
QUIZ_EXAM_DATA_PATH = RAW_DATA_DIR / "_Trimester-1 2025 Attendance Quiz-Assignment-Exam 5Jan2025.xlsx"
LIVE_ATTENDANCE_DATA_PATH = RAW_DATA_DIR / "B.S and M.Sc Live Summary Data C-1, Trimester 1.xlsx"
LABELS_DATA_PATH = DATA_DIR / "labels.csv"
WEEK3_USAGE_PATH = RAW_DATA_DIR / "Learner usage week 3.xlsx"
GRADED_QUIZ_COMPLETE_PATH = RAW_DATA_DIR / "graded quiz 1 10 feb complete.xlsx"
LIVE_T1_PATH = RAW_DATA_DIR / "B.S and M.Sc Live Summary Data C-1, Trimester 1.xlsx"
LIVE_T2_PATH = RAW_DATA_DIR / "B.S and M.Sc Summary Data Trimester 2.xlsx"

# ========== Logging ==========
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BACKEND_DIR / "backend.log"

# ========== Feature Engineering ==========
FEATURE_COLUMNS_REQUIRED = [
    'content_completed', 'content_required', 'quiz_completed', 'num_logins'
]

# ========== Scheduler ==========
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
PREDICTION_UPDATE_INTERVAL = int(os.getenv("PREDICTION_UPDATE_INTERVAL", "3600"))  # seconds
