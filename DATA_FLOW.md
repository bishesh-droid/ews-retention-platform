# Data Flow Specification

## Scope

This file documents the implemented end-to-end data movement from source files to API responses. All behavior is derived from the actual source code.

---

## 1. Source Data

Data originates from Microsoft Excel (XLSX) exports from the Brightspace LMS. Files are placed manually in `backend/data/`. The application reads them at startup via openpyxl.

| Config Key | Default Filename | Required |
|---|---|---|
| `ENGAGEMENT_DATA_PATH` | `Engagement_Analysis.xlsx` | **Yes** — startup aborts if missing |
| `QUIZ_EXAM_DATA_PATH` | `_Trimester-1 2025 Attendance Quiz-Assignment-Exam 5Jan2025.xlsx` | No |
| `WEEK12_ENGAGEMENT_PATH` | `Week 1-2 Student Engagement Analysis.xlsx` | No |
| `QUIZ_STATUS_9FEB_PATH` | `Graded Quiz 1 Status 9 Feb.xlsx` | No |
| `GRADED_QUIZ_10FEB_ORIG_PATH` | `graded quiz 1 10 feb complete.xlsx` | No |
| `GRADED_QUIZ_10FEB_1115AM_PATH` | `graded quiz 1 10 feb 11 15 AM.xlsx` | No |
| `GRADED_QUIZ_10FEB_451PM_PATH` | `graded quiz 1 10 feb 4 51 PM.xlsx` | No |
| `WEEK3_USAGE_PATH` | `Learner usage week 3.xlsx` | No |
| `WEEK5_USAGE_PATH` | `Learner usage week 5.xlsx` | No |

---

## 2. Ingestion Pipeline (Startup)

Called from `main.py` lifespan as a non-blocking `asyncio.create_task`. Runs in a thread via `asyncio.to_thread`. If ingestion fails, the server remains running with an empty database.

### 2.1 Student and Enrollment Ingestion

Source: `Engagement_Analysis.xlsx` → sheet `"Learner Usage main dump"`

```
For each row in sheet:
    Student (upsert by username):
        id                = username (email address, PK)
        first_name        = First Name column
        last_name         = Last Name column
        org_defined_id    = Org Defined ID column
        old_new_student   = Old/New Student column
        parent_department_name  = Parent Org Unit Name
        parent_department_code  = Parent Org Unit Code
        is_active         = True (default)

    Course (upsert by course_id):
        id     = Course ID column
        name   = Course Name column

    Enrollment (upsert by student_id + course_id):
        COUNTER_FIELDS are accumulated, not replaced.
        Non-counter fields (dates) are overwritten.

COUNTER_FIELDS = {
    content_completed, content_required, checklist_completed,
    quiz_completed, total_quiz_attempts,
    discussion_posts_created, discussion_post_replies, discussion_posts_read,
    num_assignment_submissions, total_time_spent_seconds, num_logins
}
```

### 2.2 Quiz and Exam Ingestion

Source: `QUIZ_EXAM_DATA_PATH`

```
GradedComponent (upsert per student per component):
    student_id        = from row
    component_type    = "quiz" | "assignment"
    component_number  = sequence number
    score             = raw score
    max_score         = maximum possible score
    missed            = True if not submitted
    course_code, course_name = from row

ExamRecord (upsert per student per exam slot):
    student_id    = from row
    course_code   = from row
    slot          = exam slot identifier
    marks_obtained = score
    marks_total   = maximum marks
    present       = True/False attendance flag
```

### 2.3 Weekly Snapshot Updates

Sources: `WEEK12_ENGAGEMENT_PATH`, `WEEK3_USAGE_PATH`, `WEEK5_USAGE_PATH`

These update existing `Enrollment` rows with more recent counter values and SCORM completion dates. They do not create new students or courses.

### 2.4 Idempotency

Running `ingest_all_data()` multiple times produces the same result as running it once (for counter fields: totals are accumulated, so running twice would double them if the same source file is re-read — this is a known limitation).

---

## 3. Feature Engineering Pipeline

Called by: `StudentService.get_all_students()` (per request) and `SchedulerService.generate_daily_predictions()` (daily batch).

Input: Python dicts loaded from `Enrollment`, `GradedComponent`, `ExamRecord` rows.

### 3.1 Feature Calculations

```
content_completion_score
    numerator   = Σ enrollment.content_completed
    denominator = Σ enrollment.content_required
    score       = (numerator / denominator) × 100
    edge case   = 0.0 if denominator == 0
    range       = [0, 100]

w1w2_completion_score
    numerator   = Σ min(content_completed, content_required_w1w2)
    denominator = Σ content_required_w1w2
    score       = (numerator / denominator) × 100
    range       = [0, 100]

quiz_engagement_score
    quizzes  = Σ quiz_completed
    attempts = Σ total_quiz_attempts
    if attempts == 0: score = 0.0
    else: score = (quizzes / attempts) × 100, boosted for high attempt count
    range = [0, 100]

discussion_engagement_score
    posts   = Σ discussion_posts_created
    replies = Σ discussion_post_replies
    reads   = Σ discussion_posts_read
    weighted sum, log-scaled to reduce outlier influence
    range = [0, 100]

assignment_score
    submissions = Σ num_assignment_submissions
    expected    = number of enrolled courses × expected_submissions_per_course
    score       = (submissions / expected) × 100
    range = [0, 100]

time_investment_score
    total_seconds = Σ total_time_spent_seconds
    log-scaled relative to maximum expected platform time
    range = [0, 100]

login_consistency_score
    logins           = Σ num_logins
    last_login_date  = max(last_system_login) across enrollments
    days_since_login = (now - last_login_date).days
    score = f(logins, days_since_login)
    heavy penalty for no logins or stale last login
    range = [0, 100]

zero_progress_ratio
    courses_with_zero = count of enrollments where content_completed == 0
    total_courses     = len(enrollments)
    ratio = courses_with_zero / total_courses
    range = [0.0, 1.0]
```

### 3.2 Feature Dictionary Output

```python
{
    "content_completion_score":    float,   # [0-100]
    "w1w2_completion_score":       float,   # [0-100]
    "quiz_engagement_score":       float,   # [0-100]
    "discussion_engagement_score": float,   # [0-100]
    "assignment_score":            float,   # [0-100]
    "time_investment_score":       float,   # [0-100]
    "login_consistency_score":     float,   # [0-100]
    "zero_progress_ratio":         float,   # [0-1]
    # Optional (if graded_components present):
    "avg_quiz_score":              float,
    "avg_assignment_score":        float,
    "quiz_completion_rate":        float,
}
```

---

## 4. Risk Scoring Pipeline

Source: `backend/services/risk_scoring.py::RiskScorer`

Input: feature dictionary from FeatureEngineer.

### 4.1 Weighted Engagement Calculation

```
FEATURE_WEIGHTS = {
    "content_completion_score": 0.30,
    "login_consistency_score":  0.20,
    "quiz_engagement_score":    0.15,
    "assignment_score":         0.15,
    "time_investment_score":    0.10,
    "discussion_engagement_score": 0.10
}

weighted_sum    = 0.0
observed_weight = 0.0

for feature, weight in FEATURE_WEIGHTS.items():
    score = feature_dict.get(feature)
    if score is None or not isfinite(score):
        continue                        # skip missing features
    score = clamp(score, 0.0, 100.0)
    weighted_sum    += weight × score
    observed_weight += weight

if observed_weight == 0.0:
    return NEUTRAL_RISK_SCORE (50.0)   # no data available

weighted_engagement = weighted_sum / observed_weight
```

### 4.2 Risk Score Computation

```
base_risk = 100.0 − weighted_engagement

coverage  = observed_weight / sum(FEATURE_WEIGHTS.values())
          = observed_weight / 1.0

risk_score = (base_risk × coverage) + (50.0 × (1.0 − coverage))
# coverage=1.0 → pure base_risk
# coverage=0.5 → 50% shrinkage toward neutral
# coverage→0   → score approaches 50.0

zero_progress_ratio = feature_dict.get("zero_progress_ratio", 0.0)
penalty = min(15.0, (zero_progress_ratio × 15.0))
risk_score += penalty

risk_score = clamp(risk_score, 0.0, 100.0)
risk_score = round(risk_score, 2)
```

### 4.3 Risk Categorization

```
risk_score < 40   → "low"    (Low Risk)
risk_score < 70   → "medium" (Medium Risk)
risk_score >= 70  → "high"   (High Risk)
```

Retention likelihood labels:
```
< 20  → "Very High"
< 40  → "High"
< 60  → "Medium"
< 80  → "Low"
>= 80 → "Very Low"
```

---

## 5. Prediction Persistence (Scheduler)

Source: `backend/services/infrastructure/scheduler.py::generate_daily_predictions()`

Runs daily at 03:00 UTC. For each student:

```
risk_score_0_100 = RiskScorer.calculate_risk_score(features)   # [0, 100]

Prediction row:
    student_id          = student.id
    risk_score          = risk_score_0_100 / 100.0              # stored as [0, 1]
    engagement_score    = (100.0 - risk_score_0_100) / 100.0    # stored as [0, 1]
    retention_likelihood = RiskScorer.get_retention_likelihood(risk_score_0_100)
    model_version       = "rule-based-v1"
    prediction_timestamp = datetime.now(UTC) (timezone stripped to naive)

RiskSnapshot row:
    student_id       = student.id
    risk_score       = risk_score_0_100 / 100.0                 # stored as [0, 1]
    engagement_score = (100.0 - risk_score_0_100) / 100.0
    timestamp        = datetime.now(UTC) (timezone stripped to naive)
    velocity, acceleration = None (not computed in scheduler)
```

**Important:** Both `Prediction.risk_score` and `RiskSnapshot.risk_score` are stored as `0–1` floats, not `0–100`. The API layer converts back to `0–100` before returning responses.

---

## 6. API Response Flow

### 6.1 Student List Endpoint

`GET /api/v1/students/students`

```
StudentService.get_all_students(db, skip, limit, sort_by, order, risk_min, risk_max)
    │
    Step 1: Query students with latest prediction subquery (LEFT JOIN)
    │
    Step 2: For each student row, load:
    │   enrollments    = LEFT JOIN with courses
    │   graded_components = all GradedComponent for student
    │   exam_records   = all ExamRecord for student
    │
    Step 3: FeatureEngineer.calculate_all_features(enrollments, graded, exams)
    │   → fresh feature computation, not cached
    │
    Step 4: RiskScorer.calculate_risk_score(features)
    │   → live risk score [0-100]
    │
    Step 5: Retrieve latest Prediction row (if exists)
    │   → _prediction_risk_to_0_100(pred) converts stored 0-1 back to 0-100
    │
    Step 6: Determine final risk score
    │   Priority: live computed score > stored prediction score
    │
    Step 7: RiskScorer.get_risk_breakdown(features)
    │   → component-level risk contributions
    │
    Step 8: Exam attendance rate
    │   = (exams where present=True / total exams) × 100
    │
    Step 9: Return student dict with all fields
    │
    Apply sort_by, order, risk_min/risk_max filters in Python
    (not pushed to SQL — applied after all features are computed)
    │
Return: { students: List[Dict], total: int, page: int, page_size: int }
```

### 6.2 Risk Trend Endpoint

`GET /api/v1/students/students/{id}/risk-trend`

```
db.query(Prediction)
    .filter(Prediction.student_id == student_id)
    .order_by(desc(Prediction.prediction_timestamp))
    .limit(limit)

For each prediction:
    raw = prediction.risk_score           # stored 0-1
    if raw <= 1.0: raw *= 100.0           # convert to 0-100
    clamp to [0, 100]

Return: { student_id, points: [{ timestamp, risk_score }] }
```

### 6.3 Cohort Risk Trends Endpoint

`GET /api/v1/students/analytics/risk-trends`

```
db.query(RiskSnapshot)
    .filter(RiskSnapshot.timestamp >= (now - weeks×7days))
    .order_by(RiskSnapshot.timestamp.asc())

Group snapshots by ISO calendar week key ("YYYY-WNN")
For each snapshot:
    risk = snapshot.risk_score × 100      # convert 0-1 → 0-100
    bucket["overall"].append(risk)
    if risk >= 60: bucket["high"].append(risk)
    if risk >= 80: bucket["critical"].append(risk)

Return: { labels: [...], series: { overall, high, critical } }
Each value is the average risk score for that week bucket.
```

---

## 7. Score Unit Flow Summary

```
FeatureEngineer output  → [0, 100]   (percent scale)
RiskScorer output       → [0, 100]   (percent scale)
Scheduler stores        → [0, 1]     (divides by 100)
Prediction.risk_score   → [0, 1]     (in database)
RiskSnapshot.risk_score → [0, 1]     (in database)
StudentService reads     → [0, 100]  (multiplies by 100 via helper)
API response             → [0, 100]  (percent scale)
Frontend display         → [0, 100]  (no conversion needed)
```

Any code path that writes a risk score without dividing, or reads without multiplying, produces silently wrong values. There are several defensive `if v <= 1.0: v *= 100.0` checks across `students_controller.py` and `student_service.py` to catch this.

---

## 8. LLM Data Flow

```
POST /api/v1/llm/explain-risk-change
    │
    Body: { student_id, time_period }
    │
    StudentService.get_student_by_id(db, student_id)
        → structured student profile dict
    │
    LLMOrchestrator(db)
    │
    ├── StudentDataRetriever.get_student_context(student_id)
    │     Queries: Student, Enrollment, Prediction, Intervention tables
    │     Returns: structured context dict
    │
    ├── ContextAssembler.build_prompt(student_context, query_type)
    │     Formats context as structured text for LLM input
    │
    ├── GuardrailValidator.validate_input(prompt)
    │     Checks for PII leakage, scope violations
    │
    ├── If LLM available:
    │     LLM API call → raw text response
    │     GuardrailValidator.validate_output(response)
    │
    └── If LLM unavailable:
          Template-based response from student data
    │
Return: { narrative, risk_score, factors, recommendations }
```

---

## 9. Frontend Data Flow

```
Browser Load
    │
    AuthProvider mounts
        sessionStorage.getItem('ews_auth') → isAuthenticated initial state
    │
    StudentProvider mounts
        loadStudents() called via useEffect
        │
        api.js.getStudents(2000)
            fetch('GET /api/v1/students/students?limit=2000&sort_by=risk_score&order=desc')
            ← No Authorization: Bearer header
            ← Backend returns HTTP 401 (if auth enforced)
            ← On error: setError("Failed to fetch student data: ...")
        │
        If success:
            validateRiskScore(s.risk_score, 50)  → clamps to [0,100], defaults null to 50
            setStudents(studentsWithData)
            setTotalStudents(fetchedStudents.length)
    │
    Pages consume StudentContext:
        const { students, loading, error, totalStudents } = useStudentData()
        if loading: show skeleton/spinner
        if error: show error message
        else: render charts and tables
```

The frontend has no explicit caching beyond the module-level `cachedStudents` variable in `api.js`. This cache persists for the browser session and is only cleared on page refresh or explicit `refreshStudents()` call.
