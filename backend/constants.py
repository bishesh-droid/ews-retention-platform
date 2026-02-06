"""
Backend Constants
----------------
Business logic constants and magic numbers.
These are NOT environment-dependent - they are business rules.
"""

# ========== Risk Categories ==========
RISK_CATEGORY_HIGH = "high"
RISK_CATEGORY_MEDIUM = "medium"
RISK_CATEGORY_LOW = "low"

# ========== Signal Names ==========
SIGNAL_ACADEMIC = "academic_signal_score"
SIGNAL_ENGAGEMENT = "engagement_signal_score"
SIGNAL_CONSISTENCY = "consistency_signal_score"
SIGNAL_INTENT = "intent_signal_score"
SIGNAL_RESPONSIVENESS = "responsiveness_signal_score"

ALL_SIGNALS = [
    SIGNAL_ACADEMIC,
    SIGNAL_ENGAGEMENT,
    SIGNAL_CONSISTENCY,
    SIGNAL_INTENT,
    SIGNAL_RESPONSIVENESS,
]

# ========== Model Prediction Labels ==========
PREDICTION_LABEL_RETAINED = 0
PREDICTION_LABEL_AT_RISK = 1

# ========== Intervention Types ==========
INTERVENTION_TYPE_ACADEMIC = "academic_support"
INTERVENTION_TYPE_COUNSELING = "counseling"
INTERVENTION_TYPE_OUTREACH = "outreach"
INTERVENTION_TYPE_MENTORING = "mentoring"
INTERVENTION_TYPE_CUSTOM = "custom"

# ========== LLM Query Types ==========
LLM_QUERY_TYPE_RISK_EXPLANATION = "risk_explanation"
LLM_QUERY_TYPE_STUDENT_ADVICE = "student_advice"
LLM_QUERY_TYPE_FACULTY_SUMMARY = "faculty_summary"
LLM_QUERY_TYPE_INTERVENTION_SUGGESTION = "intervention_suggestion"
LLM_QUERY_TYPE_COHORT_ANALYSIS = "cohort_analysis"
LLM_QUERY_TYPE_WHAT_IF = "what_if_simulation"
LLM_QUERY_TYPE_REPORT_NARRATIVE = "report_narrative"

# ========== Confidence Levels ==========
CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

# ========== Data Quality Thresholds ==========
MIN_DATA_COMPLETENESS = 0.8  # 80% of required fields
MIN_RECORDS_FOR_ANALYSIS = 10

# ========== Pagination ==========
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000

# ========== Time Periods ==========
TIME_PERIOD_RECENT = "recent"
TIME_PERIOD_THIS_WEEK = "this_week"
TIME_PERIOD_THIS_MONTH = "this_month"
TIME_PERIOD_THIS_QUARTER = "this_quarter"

# ========== User Roles ==========
ROLE_STUDENT = "student"
ROLE_FACULTY = "faculty"
ROLE_COUNSELOR = "counselor"
ROLE_ADMIN = "admin"
ROLE_SALES = "sales"
ROLE_MARKETING = "marketing"
