# Architecture Deep Dive

## Scope

This document describes the architecture as implemented in the current codebase. It covers active runtime paths, dead/parallel code paths, and the relationship between all major modules. All behavior described is verified from the source code — not from documentation, comments, or stated intent.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Application Startup Sequence](#2-application-startup-sequence)
3. [Layer Breakdown](#3-layer-breakdown)
4. [Module Dependency Graph](#4-module-dependency-graph)
5. [Database Architecture](#5-database-architecture)
6. [Request Lifecycle](#6-request-lifecycle)
7. [Scheduler Architecture](#7-scheduler-architecture)
8. [LLM Integration Architecture](#8-llm-integration-architecture)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Dead Code and Parallel Paths](#10-dead-code-and-parallel-paths)
11. [Configuration Architecture](#11-configuration-architecture)

---

## 1. System Overview

Meridian is a monolithic FastAPI application backed by SQLite, deployed as a single uvicorn process. It has no microservices, no message queues, and no external state stores beyond optional Redis caching.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Deployment Topology                           │
│                                                                     │
│  Browser → React SPA (localhost:3000, CRA dev server)              │
│                    │                                                │
│              HTTP requests (no auth token in current state)        │
│                    │                                                │
│              FastAPI (localhost:8000, single uvicorn worker)       │
│                    │                                                │
│         ┌──────────┼──────────────────┐                           │
│         │          │                  │                            │
│      SQLite     XLSX files        LLM APIs                        │
│    sql_app.db  backend/data/    (Gemini/Claude)                   │
│                                 optional, graceful fallback        │
└─────────────────────────────────────────────────────────────────────┘
```

**Key architectural constraints:**
- SQLite with `check_same_thread=False` means the application assumes single-writer access. Multiple uvicorn workers would cause write contention.
- All in-memory state (rate limiter, student cache in frontend `api.js`) is per-process.
- The async scheduler runs as asyncio tasks within the same uvicorn event loop.
- Data ingestion runs in a thread via `asyncio.to_thread` to avoid blocking the event loop.

---

## 2. Application Startup Sequence

Startup is managed by FastAPI's `lifespan()` async context manager in `backend/main.py`:

```
uvicorn starts
    │
    ├── FastAPI app object created
    │     CORSMiddleware registered
    │     security_and_logging_middleware registered
    │     request_validation_middleware registered
    │     Exception handlers registered
    │     api_router mounted at /api/v1
    │
    └── lifespan() enters
          │
          Step 1: init_db()   [synchronous, fast]
          │   Import all ORM models to register with Base.metadata
          │   Base.metadata.create_all(engine)
          │   → SQLite file created or verified
          │   → All 25+ tables created if not existing
          │   → No-op if tables already exist (idempotent)
          │
          Step 2: asyncio.create_task(_run_ingestion())   [non-blocking]
          │   Task runs concurrently with server startup
          │   → asyncio.to_thread(_run_ingestion_in_thread)
          │     → SessionLocal() → db session
          │     → ingest_all_data(db)
          │       → XLSX ETL pipeline
          │       → db.commit()
          │     If exception: db.rollback(), log error (non-fatal)
          │   Server accepts requests while this runs
          │
          Step 3: await scheduler_service.start()
          │   Creates asyncio.Task for _run_daily_loop()
          │   Creates asyncio.Task for _run_weekly_loop()
          │   Tasks sleep until 03:00 UTC / Sunday 04:00 UTC
          │   If exception: logged, non-fatal
          │
          yield  ← server is live, accepting requests
          │
    [Application runs...]
          │
    lifespan() exits (shutdown)
          │
          await scheduler_service.stop()
          Task.cancel() for both scheduler tasks
          await asyncio.gather(*tasks, return_exceptions=True)
```

---

## 3. Layer Breakdown

### Layer 1: HTTP / Transport

**FastAPI** handles HTTP parsing, routing, dependency injection, and response serialization.

**Middleware stack** (applied outermost to innermost in registration order):
```
Request arrives
    │
    ▼
security_and_logging_middleware
    Rate limit: 100 req/60s per client IP (in-memory dict)
    Log: "Incoming request: METHOD /path from IP"
    │
    ▼
request_validation_middleware
    For POST/PUT/PATCH with non-empty body:
        Requires Content-Type: application/json
        Returns 415 if violated
    │
    ▼
CORSMiddleware
    allow_origins: configurable (default: localhost:3000, 5173, 127.0.0.1:3000)
    allow_methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
    allow_headers: *
    allow_credentials: True
    │
    ▼
Route handler + dependency injection
```

### Layer 2: Authentication / Authorization

Handled by FastAPI's dependency injection system via `backend/api/deps.py`.

```
Protected route called
    │
    ├── reusable_oauth2 (OAuth2PasswordBearer)
    │     Extracts Bearer token from Authorization header
    │     auto_error=True → automatic 401 if header missing
    │
    ├── get_current_user(db, token)
    │     jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    │     Extracts payload.sub (user ID)
    │     db.query(User).filter(User.id == uid).first()
    │     Checks user.is_active
    │     Returns User ORM object
    │
    └── require_role(["admin", "faculty"])  [optional, additional layer]
          Checks user.role (case-insensitive) against allowed set
          is_superuser=True bypasses role check
          Returns User ORM object if authorized
```

### Layer 3: Route Handlers

22 route modules in `backend/routes/`. Each module creates an `APIRouter` and defines endpoint functions. Route handlers are thin — they:

1. Declare dependencies (db session, current user).
2. Validate path/query parameters via FastAPI.
3. Delegate to a service or controller.
4. Return data or raise `HTTPException`.

Route handlers do NOT contain business logic beyond parameter extraction and response shaping.

### Layer 4: Controllers

`backend/controllers/students_controller.py` — The only controller currently. Handles complex multi-endpoint student data scenarios that would overcrowd a route file. Contains the `_normalize_0_100()` helper and `_bucket_key()` time-series bucketing utility.

### Layer 5: Services

`backend/services/` — All business logic lives here. Key services:

| Service | Responsibility |
|---|---|
| `StudentService` | Student data aggregation, feature computation, risk scoring |
| `FeatureEngineer` | Engagement feature calculation from enrollment data |
| `RiskScorer` | Rule-based risk score computation |
| `LLMOrchestrator` | LLM routing, prompt construction, response handling |
| `SchedulerService` | Async background job management |
| `AuditService` | Audit log creation and retrieval |
| `AnalyticsService` | Aggregated cohort analytics |
| `GoalsService` | Student goal lifecycle |
| `ExportService` | Report/export generation |
| `FeatureStoreService` | Pre-computed feature storage |
| `DecisionEngine` | Intervention decision logic |

### Layer 6: Data Access

`backend/database/` — SQLAlchemy ORM. All database access uses ORM models and sessions. No raw SQL. Session lifecycle managed by `get_db()` generator dependency — session is opened per request, closed after response, with rollback on exception.

---

## 4. Module Dependency Graph

```
backend/main.py
    ├── backend/config/__init__.py  ← all modules import from here
    ├── backend/database/connection.py → engine, Base
    ├── backend/database/session.py → SessionLocal, get_db
    ├── backend/routes/__init__.py → api_router
    │       ├── routes/auth.py
    │       │     ├── database/models/user.py
    │       │     ├── api/deps.py
    │       │     ├── core/auth.py
    │       │     └── schemas/auth.py
    │       │
    │       ├── routes/students.py → controllers/students_controller.py
    │       │     ├── api/deps.py
    │       │     ├── services/student_service.py
    │       │     │     ├── services/feature_engineering.py
    │       │     │     ├── services/risk_scoring.py
    │       │     │     └── database/models/* (Student, Enrollment, ...)
    │       │     └── database/models/prediction.py
    │       │
    │       ├── routes/ml_routes.py
    │       │     ├── services/ml_service.py
    │       │     │     ├── services/feature_engineering.py
    │       │     │     └── services/risk_scoring.py
    │       │     └── database/models/prediction.py
    │       │
    │       ├── routes/llm.py → services/student_service.py
    │       ├── routes/interventions.py → database/models/intervention.py
    │       ├── routes/business.py → services/student_service.py
    │       └── ... (other routes)
    │
    ├── core/logger.py
    ├── middleware/security_logging.py
    ├── middleware/request_validation.py
    └── services/infrastructure/scheduler.py
          ├── services/feature_engineering.py
          ├── services/risk_scoring.py
          └── database/models/* (Student, Enrollment, Prediction, RiskSnapshot, ...)
```

```
services/core/data_ingestion.py  [startup, not in request path]
    ├── config/* (file paths)
    └── database/models/student.py, course.py, enrollment.py, academic.py
```

---

## 5. Database Architecture

### Engine Configuration

```python
engine = create_engine(
    DATABASE_URL,                           # SQLite path from config
    connect_args={"check_same_thread": False}  # Required for SQLite in FastAPI
)
```

`check_same_thread=False` allows the engine to be used from multiple threads (FastAPI's thread pool for sync endpoints). It does NOT make SQLite safe for concurrent writers — SQLite handles this internally via file-level locking, which is adequate for single-server deployments with mostly-read workloads.

### Table Inventory

**Core student data:**
```
students          — One row per unique student (email = PK)
courses           — LMS course catalog
enrollments       — Per-student-per-course engagement counters
graded_components — Quiz/assignment scores per student
exam_records      — Exam attendance and marks per student
```

**Predictions and risk tracking:**
```
predictions       — Risk scores (stored 0-1), model version, signal breakdown
risk_snapshots    — Historical risk time series (stored 0-1), velocity, acceleration
```

**Intervention management:**
```
interventions     — Intervention records with AI flag, effectiveness, channels (JSON string)
student_responses — Student responses to interventions
```

**Goals:**
```
goals             — Student progress goals with target/current values
```

**Users and auth:**
```
users             — System users with bcrypt passwords, role, preferences (JSON)
audit_logs        — Action audit trail (user_id, action, resource, details, timestamp)
```

**LLM and AI:**
```
llm_queries       — LLM request/response history
llm_insights      — Generated insights
ai_explanations   — Risk explanation records
pattern_discoveries — Pattern detection results
```

**Events and features:**
```
raw_events        — Raw LMS event ingestion
engineered_features — Pre-computed feature vectors (feature store)
```

**Data warehouse (star schema):**
```
dim_students          — Student dimension
dim_courses           — Course dimension
fact_academic_performance — Academic fact table
fact_engagement       — Engagement fact table
fact_consistency      — Consistency fact table
fact_intent_responsiveness — Behavioral fact table
data_lineage          — ETL lineage tracking
```

### Key Relationships

```
students ─── enrollments ─── courses
     │
     ├── predictions
     ├── interventions ─── student_responses
     ├── risk_snapshots
     ├── goals
     ├── graded_components
     ├── exam_records
     ├── raw_events
     └── engineered_features

users ─── audit_logs
```

### Storage Anomalies

**Risk score dual representation:**
- `Prediction.risk_score`: stored as `0.0–1.0` (scheduler stores `rule_score / 100.0`)
- `RiskSnapshot.risk_score`: stored as `0.0–1.0`
- API responses use `0–100` scale (service layer converts)
- Runtime scorers output `0–100` directly

**Date columns as strings:**
- `Enrollment.last_visited_date`, `last_system_login`, `last_quiz_attempt_date`, etc.
- `Column(String)` instead of `Column(DateTime)`
- SCORM date fields similarly
- Cannot be sorted or filtered with date arithmetic without parsing

**Channels as JSON string:**
- `Intervention.channels` stores `'["email", "whatsapp"]'` as a String column
- Parsed/serialized in route handlers with `json.loads`/`json.dumps`
- A JSON column (SQLAlchemy JSON type) would be cleaner

---

## 6. Request Lifecycle

### Sync Endpoint Example: GET /api/v1/students/students

```
1. uvicorn receives HTTP GET
2. security_and_logging_middleware: rate check, log request
3. request_validation_middleware: GET, skip body check
4. CORSMiddleware: check Origin header
5. FastAPI router matches /api/v1/students/students
6. Dependency resolution:
   a. get_db() → SessionLocal() → yields db session
   b. require_role(["faculty","admin","retention team"])
        → reusable_oauth2 extracts Bearer token
        → get_current_user(db, token)
             → jwt.decode(token)
             → db.query(User).filter(User.id == uid).first()
             → check is_active
             → return user
        → check user.role in required_roles
        → return user
7. get_students() handler called with db, _user
8. StudentService.get_all_students(db, skip, limit, sort_by, order, risk_min, risk_max)
   → Multi-table JOIN (Student, Enrollment, Course, Prediction)
   → For each student: FeatureEngineer.calculate_all_features()
   → For each student: RiskScorer.calculate_risk_score()
9. Return { students: [...], total: N, page: N, page_size: N }
10. FastAPI serializes to JSON
11. security_and_logging_middleware: log response status + time
12. HTTP 200 response sent
13. get_db() finally block: db.close()
```

### Async Endpoint Example: POST /api/v1/ml/predict/{student_id}

```
1-6. Same as above (async execution context)
7. predict_student_risk() async handler called
8. await asyncio.wait_for(
       asyncio.to_thread(ml_service.predict_student, db, student_id),
       timeout=10.0
   )
   → Thread pool: ml_service.predict_student()
        → FeatureEngineer + RiskScorer
        → db.add(Prediction(...))
        → db.commit()
9. Return prediction payload
```

---

## 7. Scheduler Architecture

```
SchedulerService (singleton: scheduler_service)
    │
    ├── _run_daily_loop() — asyncio.Task
    │     while True:
    │       await asyncio.sleep(seconds_until(03:00 UTC))
    │       await asyncio.to_thread(generate_daily_predictions)
    │
    └── _run_weekly_loop() — asyncio.Task
          while True:
            await asyncio.sleep(seconds_until(Sunday 04:00 UTC))
            await asyncio.to_thread(retrain_model_weekly)
```

Both tasks run within the main uvicorn event loop. They are CPU-bound only in `asyncio.to_thread` calls, which run in the default thread pool executor. This is correct architecture — CPU-bound work should not block the event loop.

**`generate_daily_predictions()` execution flow:**

```
1. db_session_scope() context manager opens SessionLocal
2. Load all Student rows
3. Load all Enrollment rows with Course names (LEFT JOIN, single query)
4. Load all GradedComponent rows
5. Load all ExamRecord rows
6. Build in-memory maps: enrollment_map, graded_map, exam_map
7. For each student (loop):
   a. FeatureEngineer.calculate_all_features(enrollments, graded, exams)
   b. RiskScorer.calculate_risk_score(features)
   c. db.add(Prediction(risk_score=score/100.0, ...))
   d. db.add(RiskSnapshot(risk_score=score/100.0, ...))
   e. Exceptions per student are caught and logged — one failure doesn't abort others
8. db.commit() (via context manager)
9. Log: students processed, predictions created, snapshots created
```

**Critical behavior:** If the scheduler task raises an unhandled exception, the exception is caught in the while loop's `except` block, logged, and the loop continues. The next sleep begins immediately after logging. This means one bad run does not kill the scheduler — but it also means errors may silently accumulate.

---

## 8. LLM Integration Architecture

```
Route handler (routes/llm.py or routes/advisor.py)
    │
    ├── StudentService.get_student_by_id(db, student_id)
    │     Get structured student data for grounding
    │
    └── LLMOrchestrator(db)
          │
          ├── StudentDataRetriever(db)
          │     Query student, enrollments, predictions, interventions
          │     Return structured context dict
          │
          ├── CohortDataRetriever(db)
          │     Query cohort statistics for comparison
          │
          ├── InstitutionalDataRetriever(db)
          │     Query program-level metrics
          │
          ├── ContextAssembler
          │     Combine student + cohort + institutional context
          │     Format into prompt-ready string
          │
          ├── GuardrailValidator
          │     Validate inputs (PII, scope limits)
          │     Validate outputs (hallucination checks)
          │
          └── LLM call:
                If provider == "gemini" and GENAI_AVAILABLE and GEMINI_API_KEY:
                    genai.GenerativeModel(GEMINI_MODEL).generate_content(prompt)
                elif provider == "claude" and ANTHROPIC_AVAILABLE and CLAUDE_API_KEY:
                    Anthropic(CLAUDE_API_KEY).messages.create(...)
                else:
                    Return mock/template-based response
```

**Fallback behavior:** When no LLM API key is configured, `_check_llm_available()` returns a mock response object. Routes return structured responses that are indistinguishable in format from real LLM responses but contain rule-based template text derived from student data.

---

## 9. Frontend Architecture

### State Management

No Redux or Zustand. State is managed at two levels:

1. **Global context** — `AuthContext` (auth state) and `StudentContext` (student list). Both use React Context + `useState`.
2. **Local component state** — All other state (selected student, filter values, modal open/closed) is `useState` within components.

### Data Fetching Pattern

```
StudentContext.loadStudents()   [on mount, via useCallback]
    │
    └── api.js.getStudents(2000)
          │
          ├── In-memory cache: if cachedStudents exists, return slice
          │
          └── fetch('/api/v1/students/students?limit=2000&sort_by=risk_score&order=desc')
                No Authorization header
                No error retry
                Single in-memory cache (invalidated on explicit refresh only)
```

All other API calls are made directly from pages or components without caching. The `services/api.js` service module provides domain-specific wrappers but no shared state.

### Component Hierarchy

```
App (BrowserRouter)
    │
    ├── AuthProvider
    │     └── StudentProvider
    │           │
    │           ├── /login → Login
    │           │             └── AuthContext.login() (local check, no API)
    │           │
    │           ├── /signup → Signup
    │           │
    │           └── ProtectedRoute (checks AuthContext.isAuthenticated)
    │                 └── Layout (Header + Sidebar + main content area)
    │                       │
    │                       ├── / → Dashboard
    │                       │       ├── KpiCard × 4 (from StudentContext)
    │                       │       ├── RiskTable (top at-risk students)
    │                       │       └── Charts (risk trend, distribution)
    │                       │
    │                       ├── /students → Students
    │                       │       ├── Filter/sort controls
    │                       │       └── StudentDrawer (slide-in detail panel)
    │                       │
    │                       ├── /students/:id → StudentProfile
    │                       │       ├── SignalBreakdown
    │                       │       ├── SignalRadarChart
    │                       │       ├── RiskBreakdownChart
    │                       │       ├── InterventionCard × N
    │                       │       └── AI components (WhatIfSimulator, etc.)
    │                       │
    │                       ├── /insights → Analytics
    │                       │       ├── KPI cards (from StudentContext)
    │                       │       ├── Doughnut: risk distribution
    │                       │       ├── HBar: top risk factors
    │                       │       ├── Cohort comparison BarChart
    │                       │       ├── Intervention effectiveness
    │                       │       └── Risk profile RadarChart
    │                       │
    │                       ├── /interventions → Interventions
    │                       ├── /business-analytics → BusinessAnalytics
    │                       ├── /reports → Reports
    │                       ├── /faculty-tools → FacultyTools
    │                       ├── /student-portal → StudentPortal
    │                       └── /settings → Settings
```

### Chart Libraries

- **Chart.js v4 + react-chartjs-2 v5** — Used for Line (risk trends), Scatter (engagement scatter), Doughnut (risk distribution), Bar (top risk factors). Components registered globally in `chartConfig.js`.
- **Recharts v3** — Used for: BarChart (cohort comparison, intervention effectiveness), RadarChart (risk profile), ResponsiveContainer wrappers.
- Both libraries coexist without conflict.

### Design System

- CSS variables: `--bg: #130D23`, `--panel: glass-panel class`
- Primary purple: `#7C3AED` / `#8B5CF6`
- Accent red: `#EF4444`, warning: `#F59E0B`, success: `#10B981`
- Text: `#EDE9FE` (primary), `#B8AADA` (secondary)
- Recharts tooltip: `{ background: '#1E1535', border: '1px solid rgba(139,92,246,0.3)', borderRadius: 10 }`

---

## 10. Dead Code and Parallel Paths

### Confirmed Dead Code

| Location | Status | Reason |
|---|---|---|
| `backend/ingestion/` (entire package) | Dead — alternative pipeline | Runtime uses `services/core/data_ingestion.py` |
| `backend/features/` (entire package) | Dead — not called in main flow | Queried via DB signals but not integrated into scoring |
| `backend/ml/models/saved/*.joblib` | Dead — schema mismatch | 4-feature schema incompatible with 6-feature runtime |
| `backend/ml/training/evaluate.py` | Dead — training script deleted | No invocation path |
| `backend/ml/inference/risk_formula.py` weight mapping | Partially dead | consistency/intent/responsiveness weights resolve to 0.0 |
| `backend/jobs/feature_store_job.py` | Semi-dead — standalone only | Not integrated with main scheduler |

### Deleted Files (visible in git status)

These files were removed but their dependencies or references may persist:
- `backend/ml/inference/predictor.py` — Deleted (inference was here)
- `backend/ml/models/model_registry.py` — Deleted
- `backend/ml/training/train.py` — Deleted
- `backend/app/` package — Deleted (older structure)
- `backend/data_ingestion/` package — Deleted (older ingestion)
- `backend/ml/features/feature_engineering.py` — Deleted
- `backend/database.py` — Deleted (top-level, replaced by `database/` package)

### Duplicate Implementations

| Component | Instance 1 | Instance 2 | Active |
|---|---|---|---|
| RiskScorer | `services/risk_scoring.py` | `features/risk_scorer.py` | Instance 1 |
| Ingestion pipeline | `services/core/data_ingestion.py` | `backend/ingestion/` | Instance 1 |
| Risk formula | `services/risk_scoring.py` | `ml/inference/risk_formula.py` | Instance 1 (scoring), Instance 2 (explainability) |

---

## 11. Configuration Architecture

All configuration lives in `backend/config/__init__.py` and is read at import time. There is no lazy loading or runtime reconfiguration.

**Import chain:**
```
Any module that imports from backend.config
    → backend/config/__init__.py executes at import
    → os.getenv() called for each setting
    → Production guard: if ENVIRONMENT=="production" and SECRET_KEY==default: raise RuntimeError
```

**Configuration groups:**

```python
# Server
API_HOST, API_PORT, CORS_ORIGINS

# Database
DATABASE_URL                          # defaults to sqlite:///backend/data/sql_app.db

# Security
SECRET_KEY                            # JWT signing (insecure default exists)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# LLM
LLM_PROVIDER = "gemini"               # or "claude"
GEMINI_API_KEY, GEMINI_MODEL
CLAUDE_API_KEY, CLAUDE_MODEL
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 1024

# ML / Risk
RISK_THRESHOLD_HIGH = 70.0            # 0-100 scale
RISK_THRESHOLD_MEDIUM = 40.0
SIGNAL_WEIGHTS = { attendance:0.35, grades:0.30, engagement:0.20, submissions:0.15 }

# Business
AVERAGE_STUDENT_LTV = 150000.0
TUITION_PER_SEMESTER = 75000.0
INTERVENTION_COST_PER_STUDENT = 500.0
TARGET_RETENTION_RATE = 0.90

# Data files (9 paths)
ENGAGEMENT_DATA_PATH
QUIZ_EXAM_DATA_PATH
WEEK12_ENGAGEMENT_PATH
# ... 6 more paths
```

**Important discrepancy:** `SIGNAL_WEIGHTS` in config uses keys `attendance`, `grades`, `engagement`, `submissions` — but this dict is consumed by `ml/inference/risk_formula.py` which maps signals to keys `academic`, `engagement`, `consistency`, `intent`, `responsiveness`. The mapping resolves `consistency`, `intent`, and `responsiveness` to weight `0.0` because those keys don't exist in `SIGNAL_WEIGHTS`. This is a silent bug.

The primary `RiskScorer` in `services/risk_scoring.py` does NOT use `SIGNAL_WEIGHTS` — it has its own hardcoded weights dict. The config values are only consumed by the explainability module.
