import sys
import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import logging

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.config import DATABASE_URL
except ImportError:
    # Fallback if run directly and config not found
    DATABASE_URL = "sqlite:///../sql_app.db"

logger = logging.getLogger(__name__)

# Canonical feature column list — import this in train_model.py and predict_model.py
FEATURE_COLS = [
    'content_completed', 'content_required', 'quiz_completed',
    'total_quiz_attempts', 'num_logins', 'total_time_spent_seconds',
    'discussion_posts_created', 'discussion_posts_read', 'courses_enrolled',
    'content_completion_rate', 'quiz_completion_rate', 'avg_time_per_course'
]

def load_data_from_db():
    """
    Loads data from SQLite database and merges relevant tables.
    Returns a raw dataframe with student, enrollment, and course data.
    """
    # Hardcode DB path for reliability in script execution
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sql_app.db'))
    db_url = f"sqlite:///{db_path}"
    
    engine = create_engine(db_url)
    
    logger.info(f"Loading data from {db_url}...")
    try:
        # Check table existence first
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='students';"))
            if result.scalar() is None:
                # Fallback to dim_student if students doesn't exist
                logger.warning("'students' table not found. Trying 'dim_student'...")
                students = pd.read_sql("SELECT * FROM dim_student", engine)
                # Helper to standardize ID column
                if 'student_id' in students.columns and 'id' not in students.columns:
                    students.rename(columns={'student_id': 'id'}, inplace=True)
            else:
                 students = pd.read_sql("SELECT * FROM students", engine)

        enrollments = pd.read_sql("SELECT * FROM enrollments", engine)
        courses = pd.read_sql("SELECT * FROM courses", engine)
        
        if enrollments.empty:
             logger.warning("Enrollments table is empty!")
             return pd.DataFrame()

        # Merge Enrollments with Courses
        merged = enrollments.merge(courses, left_on='course_id', right_on='id', suffixes=('', '_course'))
        
        # Merge with Students is optional for features, but good for demographics if needed
        merged = merged.merge(students, left_on='student_id', right_on='id', suffixes=('', '_student'))
        
        return merged
    except Exception as e:
        logger.error(f"Error loading data from DB: {e}")
        return pd.DataFrame()

def engineer_features(raw_df, semester=None):
    """
    Aggregates raw enrollment data into student-level features.
    Creates target variable 'is_dropout'.
    Optionally filters by semester (e.g., 'Trimester 1', 'Trimester 2').
    """
    if raw_df.empty:
        return pd.DataFrame()

    # --- 0. Filter by Semester ---
    if semester:
        # Check column name for semester
        sem_col = 'semester_name'
        if sem_col not in raw_df.columns:
            # Maybe it's 'semester_name_course' due to merge
             if 'semester_name_course' in raw_df.columns:
                 sem_col = 'semester_name_course'
             else:
                 logger.warning(f"Semester column not found! Available: {raw_df.columns}")
                 return pd.DataFrame()
        
        raw_df = raw_df[raw_df[sem_col] == semester].copy()
        if raw_df.empty:
            logger.warning(f"No data for semester: {semester}")
            return pd.DataFrame()

    # --- 1. Filter / Cleanup ---
    # Convert numeric columns
    numeric_cols = [
        'content_completed', 'content_required', 'quiz_completed', 
        'total_quiz_attempts', 'num_logins', 'total_time_spent_seconds',
        'discussion_posts_created', 'discussion_posts_read'
    ]
    for col in numeric_cols:
        if col in raw_df.columns:
            raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce').fillna(0)

    # --- 2. Feature Engineering (Student Level Aggregation) ---
    # We want to predict risk for a student based on their aggregate performance
    
    # Group by Student ID
    student_features = raw_df.groupby('student_id').agg({
        'content_completed': 'sum',
        'content_required': 'sum',
        'quiz_completed': 'sum',
        'total_quiz_attempts': 'sum',
        'num_logins': 'sum',
        'total_time_spent_seconds': 'sum',
        'discussion_posts_created': 'sum',
        'discussion_posts_read': 'sum',
        'id_course': 'count' # Number of courses enrolled
    }).reset_index()
    
    student_features.rename(columns={'id_course': 'courses_enrolled'}, inplace=True)

    # Derived Ratios
    student_features['content_completion_rate'] = student_features['content_completed'] / student_features['content_required'].replace(0, 1)
    student_features['quiz_completion_rate'] = student_features['quiz_completed'] / student_features['total_quiz_attempts'].replace(0, 1) # Approximation
    student_features['avg_time_per_course'] = student_features['total_time_spent_seconds'] / student_features['courses_enrolled'].replace(0, 1)
    
    # --- 3. Target Variable Creation (Dropout Proxy) ---
    # Proxy: Bottom 20% of content completion or very low login activity
    
    # Calculate dynamic threshold based on distribution (if enough data)
    if len(student_features) > 10:
        completion_threshold = student_features['content_completion_rate'].quantile(0.20)
        time_threshold = student_features['avg_time_per_course'].quantile(0.20)
    else:
        completion_threshold = 0.10
        time_threshold = 600

    def define_target(row):
        # Risk if in bottom 20% of cohort for completion OR time
        if row['content_completion_rate'] <= completion_threshold:
            return 1
        if row['avg_time_per_course'] <= time_threshold:
             return 1
        if row['num_logins'] < 5:
            return 1
        return 0

    student_features['is_dropout'] = student_features.apply(define_target, axis=1)

    # Warn if target distribution is degenerate — do NOT inject random labels,
    # as that would corrupt model training. Caller should handle this case.
    if student_features['is_dropout'].nunique() == 1:
        logger.error(
            "Target variable 'is_dropout' has only one class in the dataset. "
            "All students map to the same label. Check thresholds or get more data."
        )
    elif student_features['is_dropout'].mean() > 0.9 or student_features['is_dropout'].mean() < 0.1:
        logger.warning(
            f"Target variable is heavily imbalanced "
            f"(dropout rate={student_features['is_dropout'].mean():.1%}). "
            "Consider adjusting thresholds or collecting more representative data."
        )

    # --- 4. Handle Missing Values ---
    student_features.fillna(0, inplace=True)
    
    return student_features

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = load_data_from_db()
    print(f"Loaded raw data: {df.shape}")
    features = engineer_features(df)
    print(f"Engineered features: {features.shape}")
    print(features.head())
    print("Target distribution:")
    print(features['is_dropout'].value_counts())
