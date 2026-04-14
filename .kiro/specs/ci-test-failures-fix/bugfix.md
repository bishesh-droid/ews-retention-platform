# Bugfix Requirements Document

## Introduction

This bugfix addresses 4 distinct issues causing 24 test failures in the CI/CD pipeline:
1. Import error affecting 21 tests (incorrect module path for GradedComponent)
2. Ghost detection logic error in consistency feature extractor
3. Engagement pattern boundary condition error in intent feature extractor  
4. Null field handling error in cohort risk profiles endpoint

These bugs prevent the test suite from passing and indicate potential runtime issues in production.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN tests import `from backend.database.models.graded_component import GradedComponent` THEN the system raises `ModuleNotFoundError: No module named 'backend.database.models.graded_component'`

1.2 WHEN ConsistencyFeatureExtractor.extract() is called with empty enrollments list and total_login_count=0 THEN the system returns is_ghost=True

1.3 WHEN IntentFeatureExtractor classifies a student with exactly 5% content completion and fewer than 5 logins THEN the system returns engagement_pattern="disengaged"

1.4 WHEN the cohort-risk-profiles endpoint receives a request and a student has null first_name, last_name, and parent_department_name fields THEN the system returns 500 Internal Server Error

### Expected Behavior (Correct)

2.1 WHEN tests import GradedComponent THEN the system SHALL successfully import from `backend.database.models.academic` where the model is actually defined

2.2 WHEN ConsistencyFeatureExtractor.extract() is called with empty enrollments list and total_login_count=0 THEN the system SHALL return is_ghost=False (no courses means not a ghost student)

2.3 WHEN IntentFeatureExtractor classifies a student with exactly 5% content completion (boundary value) and fewer than 5 logins THEN the system SHALL NOT return engagement_pattern="disengaged" (the condition requires < 5% completion, not <= 5%)

2.4 WHEN the cohort-risk-profiles endpoint receives a request and a student has null first_name, last_name, and parent_department_name fields THEN the system SHALL return 200 OK with gracefully handled null values

### Unchanged Behavior (Regression Prevention)

3.1 WHEN tests import ExamRecord from backend.database.models.academic THEN the system SHALL CONTINUE TO import successfully

3.2 WHEN ConsistencyFeatureExtractor.extract() is called with enrollments containing courses with zero progress THEN the system SHALL CONTINUE TO correctly count zero_progress_course_count

3.3 WHEN IntentFeatureExtractor classifies a student with less than 5% completion and fewer than 5 logins THEN the system SHALL CONTINUE TO return engagement_pattern="disengaged"

3.4 WHEN the cohort-risk-profiles endpoint receives a request for students with valid non-null fields THEN the system SHALL CONTINUE TO return 200 OK with correct profile data

3.5 WHEN ConsistencyFeatureExtractor detects ghost students with zero logins and zero progress THEN the system SHALL CONTINUE TO return is_ghost=True with ghost_type="never_logged_in"

3.6 WHEN IntentFeatureExtractor classifies students with high login, low completion, and poor quiz scores THEN the system SHALL CONTINUE TO return engagement_pattern="struggling"
