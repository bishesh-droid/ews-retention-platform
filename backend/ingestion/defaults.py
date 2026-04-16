"""
Safe default values for missing data in ETL pipeline
"""

SAFE_DEFAULTS = {
    # Percentages: NULL if unknown, never negative
    "attendance_percentage": None,
    "quiz_score": None,
    "engagement_score": None,
    # Counts: 0 is valid
    "login_count": 0,
    "sessions_attended": 0,
    "quizzes_submitted": 0,
    "content_items_viewed": 0,
    "discussion_posts": 0,
    # Booleans: False if unknown engagement action
    "submitted": False,
    "email_opened": False,
    "late_submission": False,
    # Risk score: NULL if insufficient data
    "risk_score": None,  # NEVER -1, NEVER negative
}


def apply_safe_defaults(record: dict, schema: dict) -> dict:
    """Apply defaults for missing values"""
    for field, default in SAFE_DEFAULTS.items():
        if field in schema and field not in record:
            record[field] = default
    return record
