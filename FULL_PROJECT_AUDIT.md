# Meridian EWS Retention Platform — Full Project Audit Report

**Audit Date:** 2026-04-07  
**Auditor:** Principal Engineer Review  
**Repository:** `ews-retention-platform`  
**Git Branch:** `main` (HEAD: `d1f4eb9`)

---

## Table of Contents

1. [Project Structure Overview](#1-project-structure-overview)
2. [Tech Stack](#2-tech-stack)
3. [Architectural Pattern](#3-architectural-pattern)
4. [Data Flow Diagram](#4-data-flow-diagram)
5. [File-by-File Audit](#5-file-by-file-audit)
6. [Folder-Level Issues](#6-folder-level-issues)
7. [Cross-Layer Issues](#7-cross-layer-issues)
8. [Risk Summary](#8-risk-summary)
9. [Refactor Strategy](#9-refactor-strategy)

---

## 1. Project Structure Overview

```
ews-retention-platform/
├── alembic/                        # DB migrations (3 versions)
├── backend/
│   ├── api/                        # Dependency injection (deps.py)
│   ├── config/                     # Central config (__init__.py)
│   ├── controllers/                # students_controller.py
│   ├── core/                       # auth.py, logger.py, redis_cache.py, security.py
│   ├── data/                       # Raw XLSX data + labels.csv + sql_app.db
│   ├── database/
│   │   ├── connection.py           # SQLAlchemy engine + Base
│   │   ├── session.py              # SessionLocal + get_db
│   │   ├── models/                 # 14 model files (Student, Prediction, Canonical…)
│   │   └── queries.py
│   ├── ingestion/                  # Separate validated ingestion pipeline (UNUSED)
│   ├── jobs/                       # feature_store_job.py
│   ├── middleware/                 # request_validation.py, security_logging.py
│   ├── ml/
│   │   ├── config.py
│   │   ├── inference/              # risk_formula.py (explainability module)
│   │   ├── models/saved/           # XGBoost + LogReg .joblib models
│   │   └── training/               # evaluate.py
│   ├── routes/                     # 21 route modules
│   ├── schemas/                    # Pydantic schemas
│   ├── services/
│   │   ├── ai/                     # LLMOrchestrator, RAGEngine, HallucinationGuard
│   │   ├── analytics/              # intervention_intel.py, pattern_discovery.py
│   │   ├── core/                   # data_ingestion.py, decision_engine.py, ews_engine.py
│   │   ├── infrastructure/         # audit_logger.py, recommender.py, scheduler.py
│   │   ├── analytics_service.py
│   │   ├── feature_engineering.py  # FeatureEngineer class
│   │   ├── ml_service.py           # MLService singleton
│   │   ├── risk_scoring.py         # RiskScorer class
│   │   └── student_service.py      # StudentService class
│   ├── tests/                      # 8 test files
│   └── utils/api.py
├── data/
│   ├── raw/                        # 11 XLSX source files
│   ├── processed/                  # clean_master_dataset.csv
│   └── archive/                    # older quiz XLSX snapshots
├── data_ingestion/                 # ROOT-LEVEL orphaned ingestion module
│   ├── loader.py, merger.py, normalizer.py, schema_mapper.py, validator.py …
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── Dockerfile.scheduler
│   └── .env.example
├── docs/                           # API contracts, architecture docs
├── documentation/                  # Text-format documentation
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/             # ~40 components
│       ├── context/                # AuthContext.js, StudentContext.js
│       ├── hooks/                  # useDebounce, useIntervention, useStudentRisk
│       ├── pages/                  # 14 pages
│       ├── services/               # api.js (central), businessService.js, studentService.js
│       └── utils/                  # csvParser, riskScoreValidator, etc.
├── .env.example                    # Root env template
├── requirements.txt
└── ARCHITECTURE.md
```

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | FastAPI 0.118.0 + Uvicorn 0.38.0 |
| **Language** | Python 3.12 |
| **Database** | SQLite (via SQLAlchemy 2.0.45) |
| **Cache / Rate Limit** | Redis 4.6.0 + SlowAPI 0.1.9 |
| **Auth** | JWT (python-jose) + bcrypt (passlib) |
| **ML** | Rule-based RiskScorer + XGBoost/LogReg joblib models (disabled) |
| **LLM / AI** | Google Gemini API + Anthropic Claude API (optional, via try/except) |
| **Frontend** | React 18.2 (CRA), Bootstrap 5, Chart.js v4, Recharts v3 |
| **State Management** | React Context (StudentContext, AuthContext) |
| **HTTP Client** | Axios 1.6.8 |
| **Scheduling** | Custom asyncio SchedulerService |
| **Containerisation** | Docker multi-stage + Docker Compose |
| **Migrations** | Alembic 1.18.4 (partially in use) |
| **Testing** | pytest 9.0.2 |

---

## 3. Architectural Pattern

The backend follows a **Layered MVC + Service** pattern:

```
Routes (HTTP) → Service Layer → DB Models / Feature Engineering → SQLite
                     ↕
            ML Pipeline (RiskScorer → FeatureEngineer)
                     ↕
            LLM Orchestrator (optional, Gemini/Claude)
```

The frontend is a **Single-Page Application** with centralized API access through `services/api.js` and global state via React Context.

The system is **NOT microservices** — it is a monolith with a scheduler sidecar. The scheduler is deployed as a separate Docker container but shares the same SQLite file via a volume mount.

---

## 4. Data Flow Diagram

```
XLSX Files (raw/data/*.xlsx)
        │
        ▼
data_ingestion.py (backend/services/core)
  - Reads openpyxl
  - Upserts: Student, Course, Enrollment, GradedComponent, ExamRecord
        │
        ▼
SQLite DB (backend/data/sql_app.db)
  ┌─────────────────────────────────────┐
  │ students                            │
  │ courses                             │
  │ enrollments                         │
  │ graded_components                   │
  │ exam_records                        │
  │ predictions (risk_score 0-1)        │
  │ risk_snapshots                      │
  │ interventions                       │
  │ users                               │
  │ audit_logs                          │
  │ [dim_* / fact_* — EMPTY]            │
  └─────────────────────────────────────┘
        │
        ▼
FeatureEngineer.calculate_all_features()
  → RiskScorer.calculate_risk_score()   ← Rule-based, 0-100 scale
  → MLService.predict_student()         ← Wraps above, persists to DB
        │
        ▼
StudentService.get_all_students() / get_student_by_id()
  → Returns dict with risk_score 0-100
        │
        ▼
FastAPI Routes (/api/v1/…)
  → success_response() envelope { success, message, data, meta }
        │
        ▼
React Frontend (axios)
  → StudentContext / AuthContext
  → Pages / Charts
```

---

## 5. File-by-File Audit

---

### File: `backend/middleware/request_validation.py`

- **Purpose:** Enforces `application/json` content-type for POST/PUT/PATCH requests.
- **Dependencies:** FastAPI `Request`, `JSONResponse`
- **Problems Found:**
  - **[CRITICAL]** The OAuth2 login endpoint (`POST /api/v1/auth/login`) sends `application/x-www-form-urlencoded` (required by the OAuth2 spec and `OAuth2PasswordRequestForm`). This middleware will return **HTTP 415** for any login attempt with a non-zero body, breaking authentication entirely.
  - The check `request.headers.get("content-length") not in (None, "0")` evaluates the `content-length` header. OAuth2 login will have a non-zero body, so it falls into the rejection branch.
- **Severity:** Critical
- **Why:** Every user trying to log in will get a 415 error before the auth handler runs.
- **Suggested Fix:** Add an exemption for `application/x-www-form-urlencoded`, or specifically exempt the `/auth/login` path.

---

### File: `frontend/src/context/StudentContext.js`

- **Purpose:** Global student data provider. Fetches all students on mount.
- **Dependencies:** `getStudentList` API call, `validateRiskScore` utility
- **Problems Found:**
  - **[Critical]** Line 21: `if (!response.success || !Array.isArray(response.data?.items))` — the frontend expects `response.data.items` but the backend controller (`GET /students/students`) returns `{ students: [...], total, page, page_size }`. There is no `items` key. This means `response.data?.items` is always `undefined`, the condition throws, and the students array is **always empty** in every page that consumes this context.
  - **[High]** `getStudentList(1, 2000, ...)` — fetches 2000 students on every page load. This is a full dataset load into the browser on every navigation, blocking the UI. For a growing institution this will cause performance degradation.
  - No error boundary or fallback UI for the throw path.
- **Severity:** Critical (missing key), High (over-fetching)
- **Suggested Fix:** Either rename backend response key from `students` to `items`, or update the frontend to read `response.data?.students`. Implement pagination rather than bulk loading 2000 records.

---

### File: `docker/docker-compose.yml`

- **Purpose:** Orchestrates Redis, backend API, scheduler, and frontend containers.
- **Problems Found:**
  - **[Critical]** The `scheduler` service uses `command: python -m backend.services.scheduler` but the actual scheduler module path is `backend.services.infrastructure.scheduler`. This causes a `ModuleNotFoundError` on container start — **the scheduler container never runs**.
  - **[High]** The `backend` service sets `DATABASE_URL=sqlite:///./backend/ews_platform.db` — different filename (`ews_platform.db`) from the default in `backend/config/__init__.py` (`sql_app.db`). Data written by the API container goes to a different file than what the scheduler container would use if it could start.
  - **[Medium]** The `scheduler` service `environment` does not set `DATABASE_URL`. It inherits no database path and defaults to `sqlite:///./backend/data/sql_app.db` (the config default). This means API and scheduler containers could target different SQLite files.
  - **[Medium]** No `healthcheck` for the `backend` service at the compose level (only in the Dockerfile). The `frontend` service has `depends_on: backend` but no condition on backend health.
  - **[Low]** SQLite is being used in a multi-container deployment sharing a file over a volume. SQLite WAL supports only one writer at a time. Concurrent writes from API + scheduler containers will cause lock contention and potential corruption.
- **Severity:** Critical (wrong module), High (DB path mismatch)

---

### File: `backend/core/redis_cache.py`

- **Purpose:** Redis-backed response caching with a `@cache_response` decorator.
- **Problems Found:**
  - **[High]** The `cache_response` decorator's inner `wrapper` is `async def` and calls `await func(*args, **kwargs)`. If the decorated function is synchronous (most FastAPI route functions are), this will fail silently or raise a `TypeError`.
  - **[High]** `json.dumps(kwargs, sort_keys=True)` is called on route kwargs which typically include a SQLAlchemy `Session` object (passed via `Depends(get_db)`). SQLAlchemy sessions are **not JSON-serializable** — this will raise a `TypeError` on the first cache miss.
  - **[Medium]** The decorator is defined but **never used** in any route file. It is dead infrastructure code.
  - **[Low]** The `RedisCache` class is instantiated at module import time as a module-level singleton (`cache = RedisCache()`). If Redis is unavailable at import time, it silently disables itself — acceptable, but this masks configuration errors.
- **Severity:** High (broken if used), Medium (dead code)

---

### File: `backend/core/security.py`

- **Purpose:** `SecurityManager` class with `sanitize_input`, `enforce_role`, `validate_pagination`.
- **Problems Found:**
  - **[High]** `SecurityManager` is **never imported or called anywhere** in the codebase. RBAC is handled correctly by `deps.py::require_role()`. This class is dead code.
  - **[Medium]** `sanitize_input` uses a regex to strip HTML tags (`re.sub(r'<[^>]*>', '', data)`). This is insufficient as an XSS defense; it can be bypassed with malformed tags and does not handle JavaScript event handlers, SVG injection, or encoded payloads.
  - **[Low]** The `enforce_role` method raises `HTTPException` directly — mixing security concerns with HTTP concerns in a utility class.
- **Severity:** High (dead code creating a false sense of security), Medium (weak sanitization logic if ever used)

---

### File: `backend/config/__init__.py`

- **Purpose:** Central application configuration loaded from environment variables.
- **Problems Found:**
  - **[High]** `SIGNAL_WEIGHTS` in config has keys `attendance`, `grades`, `engagement`, `submissions`. However, `FeatureEngineer` and `RiskScorer` use completely different feature keys (`content_completion_score`, `login_consistency_score`, etc.). The `risk_formula.py` maps `academic_signal_score`, `engagement_signal_score`, etc. There are **three different weight schemas** in the system that are mutually incompatible.
  - **[Medium]** `RISK_THRESHOLD_HIGH` defaults to `70.0` (0-100 scale), but `.env.example` sets `RISK_THRESHOLD_HIGH=0.7` (0-1 scale). If `.env` is used directly from the template, the threshold is misinterpreted — all students would be classified as "high risk".
  - **[Medium]** `INTERVENTION_THRESHOLDS` uses different scale ranges (30.0, 40.0, 60.0, 80.0 in config) vs `.env.example` (0.30, 0.60, 0.80 — 0-1 scale). The `business.py` route uses these thresholds as 0-100 scale values, creating potential misclassification if env vars are set from the example file.
  - **[Low]** `datetime.utcnow` is a deprecated Python 3.12 function and appears through indirect imports in models.
  - **[Low]** `AVERAGE_STUDENT_LTV=150000.0` in config defaults vs `12500.0` in `.env.example` — 12x discrepancy. Revenue-at-risk calculations will differ dramatically depending on whether `.env` is used.
- **Severity:** High (scale inconsistency = silent wrong calculations)

---

### File: `backend/services/ml_service.py`

- **Purpose:** ML prediction service; wraps FeatureEngineer + RiskScorer, persists predictions.
- **Problems Found:**
  - **[High]** `_JOBLIB_MODEL` is set to `None` intentionally because the trained XGBoost model (32 absrate/mpa features) is incompatible with DB-derived features. The comment acknowledges this. However, `model_used: False` is returned in every prediction — **the system has always used rule-based scoring only**. There is no timeline or mechanism to retrain on DB features.
  - **[High]** `self._cache` is an unbounded in-memory dictionary. With 500+ students and daily prediction jobs, this dict grows without limit, is never evicted, and is lost on every restart. Not shared across multiple Uvicorn workers.
  - **[Medium]** `persist_prediction` calls `db.rollback()` on exception and then returns silently. This rolls back **any other pending changes** in the same session (not just the prediction insert), potentially losing data from the calling context.
  - **[Medium]** `_error_prediction` returns `risk_score: 50.0` as a default on failure. A failed prediction silently presents as "medium risk" — there is no way for callers to distinguish a real 50% score from an error fallback.
  - **[Low]** `_persist_prediction = persist_prediction` is a backward-compatibility alias that is never needed since the old name was never public.
- **Severity:** High

---

### File: `backend/services/feature_engineering.py`

- **Purpose:** Derives engagement features from enrollment/graded/exam dictionaries.
- **Problems Found:**
  - **[High]** All normalization denominators are hardcoded magic numbers with no basis in actual data:
    - `20 quizzes per course is excellent` (line 109)
    - `100 logins per course is very active` (line 164)
    - `20 hours per course is good engagement` (line 187)
    - `30 weighted discussion activity points per course is good` (line 141)
    - `5 assignment submissions per course is good` (line 208)
    These are institution-agnostic guesses that will produce meaningless scores for any specific institution.
  - **[Medium]** `get_engagement_trend()` classifies trend as "active/declining/inactive" based on absolute thresholds (`< 10 logins`, `< 5 content completed`) — not a temporal trend. This is a static snapshot label, not a trend.
  - **[Medium]** `calculate_content_completion_score` returns `0.0` when `total_required == 0`. A student enrolled in courses with no required content (config issue) would always score 0%, appearing at-risk.
  - **[Low]** `_parse_timestamp()` handles `Z` suffix by replacing with `+00:00`, but many other date fields in Enrollment are stored as `String` in the DB, making this unused for DB-backed calculations.
- **Severity:** High (arbitrary normalization = unreliable risk scores)

---

### File: `backend/services/student_service.py`

- **Purpose:** Business logic for all student data retrieval and risk computation.
- **Problems Found:**
  - **[High]** `get_intervention_effectiveness()` (in `students_controller.py`) calls `StudentService.get_all_students(db, skip=0, limit=2000, ...)` — this loads up to 2000 students into Python memory to compute intervention effectiveness. This is O(n) memory for an analytics query.
  - **[Medium]** `_derive_risk_fields` falls back to live `RiskScorer.calculate_risk_score()` when no stored `Prediction` row exists. For the first request before predictions are stored, this means every student's risk is computed on every API call — no caching.
  - **[Medium]** `build_prediction_payload()` converts `risk_score` back to 0-1 scale (`risk / 100.0`) for the `/predictions/batch` response. The frontend `api.js` receives 0-1 values from `/predictions` but expects 0-100 from `/students`. This dual-scale is a persistent source of confusion and bugs.
  - **[Low]** `get_student_weekly_summary()` always returns `missedAssignments: 0` and `lowEngagementDays: 0` — hardcoded, never computed.
  - **[Low]** `get_student_weekly_summary()` always returns `facultyInteractions: 0` — not queried from the interventions table.
- **Severity:** High (memory), Medium (scale confusion)

---

### File: `backend/routes/business.py`

- **Purpose:** Business Intelligence endpoints (retention metrics, ROI, revenue at risk).
- **Problems Found:**
  - **[High]** All major endpoints (`get_retention_metrics`, `get_revenue_at_risk`, `get_intervention_roi`, `get_retention_funnel`, `get_executive_summary`, `get_cohort_heatmap`) call `StudentService.get_all_students(db, 0, 5000)` — loading ALL students for every request. No aggregation is done at the DB layer.
  - **[High]** `get_intervention_roi()` uses a hardcoded 60% intervention rate and 35% recovery rate. These are fabricated constants, not derived from actual intervention data. The financial numbers presented to leadership are fictional.
  - **[High]** `get_retention_forecast()` calls `get_retention_metrics()` inline (same process, same request). `get_retention_metrics()` returns a `dict` (the `success_response` envelope), then `get_retention_forecast()` calls `.get("data")` on that dict. This tight coupling means the forecast breaks if the retention response shape changes.
  - **[Medium]** `get_executive_summary()` trends are hardcoded strings: `"retention_trend": "+2.1%"`, `"risk_trend": "-3.5%"`, `"intervention_effectiveness": "+8%"`. These are **fabricated numbers** in the executive dashboard.
  - **[Medium]** `datetime.now().isoformat()` (naive datetime) is used for `calculated_at` fields — no timezone info.
  - **[Low]** `AVERAGE_STUDENT_LTV` default of 150,000 in config vs 12,500 in `.env.example` means revenue-at-risk shown to executives could be off by 12x depending on deployment.
- **Severity:** High (all fabricated business metrics)

---

### File: `backend/routes/llm.py`

- **Purpose:** LLM-powered endpoints for risk explanation, student advice, faculty summaries, what-if simulation.
- **Problems Found:**
  - **[High]** The file comment explicitly says: _"Provides mock responses for LLM-powered features. Real LLM integration can be added later."_ Every endpoint returns **hardcoded template strings**, not actual LLM output. Despite the system having a full `LLMOrchestrator`, `RAGEngine`, `HallucinationGuard` architecture in `backend/services/ai/`, none of it is connected to these routes.
  - **[High]** The `what_if_simulation` uses nonsensical heuristics: `attendance_change * 5`, `content_change * 3`. These have no basis in the risk model and will produce misleading projections.
  - **[Medium]** `/revenue-risk-translation` hardcodes `12500 * 0.25` as LTV — inconsistent with the configurable `AVERAGE_STUDENT_LTV`.
  - **[Low]** Duplicate `from fastapi import Depends` import (lines 7 and 14).
- **Severity:** High (users believe AI is active when it is not)

---

### File: `backend/routes/advisor.py`

- **Purpose:** AI Academic Advisor routes (study plan, faculty summary, motivational messages).
- **Problems Found:**
  - **[High]** All responses are template-based rule logic — not connected to `LLMOrchestrator` or any AI model. The "AI advisor" is a rule-based string generator.
  - **[Medium]** `get_advisor_context()` returns `"total_interventions": 0` hardcoded — never queries the interventions table for the student.
  - **[Medium]** Duplicate `from fastapi import Depends` import.
  - **[Low]** `datetime.now().isoformat()` used throughout — naive datetime without timezone.
- **Severity:** High (AI label is misleading)

---

### File: `backend/database/connection.py`

- **Purpose:** SQLAlchemy engine creation and `init_db`.
- **Problems Found:**
  - **[High]** `connect_args={"check_same_thread": False}` is used with SQLite. While the session factory creates new sessions per thread (correct), `check_same_thread: False` can mask accidental session sharing bugs. In production, the scheduler and API share the same SQLite file, and concurrent writes will serialize under WAL, with risk of `SQLITE_BUSY` errors under load.
  - **[Medium]** `init_db()` uses `Base.metadata.create_all()`. With Alembic also present (`alembic/` folder), the schema may diverge — `create_all()` does not apply Alembic migrations, so the alembic version table will be out of sync.
  - **[Low]** No connection pool configuration (connection limits, overflow). SQLite doesn't benefit from pooling, but documenting this intentional choice would help.
- **Severity:** High (production DB file contention)

---

### File: `backend/database/models/canonical.py`

- **Purpose:** Star-schema dimensional tables (`dim_students`, `fact_engagement`, `fact_academic_performance`, etc.).
- **Problems Found:**
  - **[High]** These tables are created by `init_db()` and registered in `__init__.py`, but **no ETL pipeline writes to them**. `data_ingestion.py` writes to the operational tables (`students`, `enrollments`, etc.), not the canonical tables. All fact and dimension tables are permanently empty.
  - **[High]** `FactIntentResponsiveness` tracks email open rates, response times, welcome email reads — data that is **never collected** anywhere in the system (no email provider integration).
  - **[Medium]** `DataLineage` is intended as an ETL audit trail, but `data_ingestion.py` never writes a `DataLineage` record. All ingestion runs are untracked.
  - **[Low]** Mixed naive/aware datetime defaults: `default=datetime.utcnow` (deprecated in Python 3.12).
- **Severity:** High (dead schema consuming DB space and creating a misleading data model)

---

### File: `backend/database/models/enrollment.py`

- **Purpose:** Student-course enrollment with engagement metrics.
- **Problems Found:**
  - **[Medium]** All date/timestamp fields (`last_quiz_attempt_date`, `last_system_login`, `last_visited_date`, `last_scorm_completion_date`, `last_assignment_submission_date`, `last_discussion_post_date`, `last_scorm_visit_date`) are typed as `String` instead of `DateTime`. This means:
    - No SQL-level date comparisons (can't filter "active in last 7 days")
    - No proper sorting by date
    - Format inconsistency between different source XLSX files is silently swallowed
  - **[Low]** No unique constraint on `(student_id, course_id)`. The `alembic/versions/001_add_enrollment_unique_constraint_and_index.py` migration adds this, but `create_all()` bypasses it.
- **Severity:** Medium

---

### File: `backend/database/models/prediction.py`

- **Purpose:** Stores ML prediction outputs.
- **Problems Found:**
  - **[Medium]** `risk_score` column comment says `# 0-1 probability of dropout`, but `retention_likelihood` is a `String` (`'high'`, `'medium'`, `'low'`). The system stores risk at 0-1 scale in DB but returns 0-100 at API. Every consumer must remember to scale — this is a perpetual error surface.
  - **[Medium]** `top_risk_factors` is stored as a JSON String, not a JSON column. If the DB were Postgres, a `JSON` column would be more appropriate and queryable.
  - **[Low]** `prediction_timestamp` uses `default=lambda: datetime.now(timezone.utc)` which creates a timezone-aware datetime. However, many query comparisons use `datetime.utcnow()` (naive) — comparing aware and naive datetimes causes runtime errors in Python 3.12 strict mode.
- **Severity:** Medium

---

### File: `backend/database/models/user.py`

- **Purpose:** System user accounts with RBAC.
- **Problems Found:**
  - **[Medium]** `created_at = Column(DateTime, default=datetime.utcnow)` stores a naive UTC datetime. `audit_logs` use `datetime.now(timezone.utc)` (aware). Mixing aware/naive datetimes in the same database causes comparison issues.
  - **[Low]** `role` column has no enum constraint or validation at the DB level. Any string is accepted. Role enforcement is done in application code only.
  - **[Low]** `preferences = Column(JSON, default=dict)` — uses SQLAlchemy JSON type. For SQLite this is stored as a JSON string (SQLite has no native JSON type). This is acceptable but worth documenting.
- **Severity:** Low-Medium

---

### File: `backend/services/core/data_ingestion.py`

- **Purpose:** ETL pipeline reading XLSX files into the operational DB tables.
- **Problems Found:**
  - **[High]** `_ingest_graded_sheet()` loads ALL `GradedComponent` rows into a dict: `graded_map = { ... for g in db.query(GradedComponent).all() }`. With thousands of students and multiple graded components each, this is a full-table scan into memory on every ingestion run.
  - **[High]** `_ingest_exam_attendance()` similarly loads ALL `ExamRecord` rows. Both are repeated per sheet — meaning 4 full-table loads of `ExamRecord` during one ingestion run.
  - **[Medium]** The `_assert_session_thread()` check verifies the current thread matches the session-owner thread. However, `ingest_all_data()` is called from `asyncio.to_thread()` in `main.py:lifespan` — the `owner_thread_id` is captured inside the `_run_ingestion_in_thread` function, so the checks are always comparing the same thread. This makes the guard a no-op for cross-thread safety.
  - **[Medium]** `_ingest_exam_defaulters()` creates `ExamRecord(course_code="EXAM_DEFAULT", slot="all")` rows — synthetic records that mix real exam data with a defaulter flag. This contaminates the `ExamRecord` table with non-exam rows.
  - **[Low]** `_update_enrollments_from_latest()` silently warns "No rows merged" for snapshot sources. There is no alert, no retry, and no visibility into which snapshots succeeded.
- **Severity:** High (memory), Medium (data contamination)

---

### File: `backend/services/infrastructure/scheduler.py`

- **Purpose:** Background async scheduler for daily predictions and weekly retraining.
- **Problems Found:**
  - **[High]** `generate_daily_predictions()` loads ALL enrollments, graded components, and exam records into Python dicts before processing students. With 500 students × 6 courses × 20 engagement metrics, this is potentially millions of Python objects loaded into RAM for each daily run.
  - **[Medium]** `generate_daily_predictions()` does not deduplicate predictions. It creates one `Prediction` row per student per run — the `predictions` table will grow unboundedly (one row per student per day). There is no pruning or archiving.
  - **[Medium]** `retrain_model_weekly()` is a stub that just logs "skipped". The weekly scheduler slot is occupied but does nothing.
  - **[Medium]** `now_utc = datetime.now(timezone.utc).replace(tzinfo=None)` — strips timezone info before storing. This means `Prediction.prediction_timestamp` stores naive UTC datetimes, while `Prediction.prediction_timestamp` default lambda creates aware datetimes. Inconsistent within the same table.
  - **[Low]** `_seconds_until()` computes delay to next 03:00 UTC. If the server restarts just after 03:00, the first run is ~24 hours later. For first-run predictions, there is no "run immediately on startup" option.
- **Severity:** High (unbounded DB growth and RAM), Medium

---

### File: `backend/routes/interventions.py`

- **Purpose:** CRUD for intervention tracking.
- **Problems Found:**
  - **[Medium]** No role restriction on `list_interventions` or `create_intervention`. Only `get_current_user` (any authenticated user) is required. A student-role user can view all interventions for all students.
  - **[Medium]** `create_intervention()` accepts `body.user` as a plain string — no validation that this matches the authenticated user. Any user can impersonate another by setting `user: "admin@institution.edu"`.
  - **[Medium]** `channels` is stored as a JSON string in the DB. `_safe_parse_channels()` silently returns `[]` on malformed JSON — no error surfaced to the caller.
  - **[Low]** Duplicate `from fastapi import Depends` import (lines 22 and 26).
- **Severity:** Medium (authorization gap)

---

### File: `backend/routes/predictions.py`

- **Purpose:** Prediction batch and per-student endpoints.
- **Problems Found:**
  - **[Medium]** `build_prediction_payload()` returns `risk_score: risk / 100.0` (0-1 scale), but `getStudentDetails()` on the frontend (`/students/students/{id}`) returns risk in 0-100. Frontend components that mix data from both endpoints will compare incompatible scales.
  - **[Low]** Duplicate `from fastapi import Depends` import (lines 8 and 14).
- **Severity:** Medium

---

### File: `backend/ml/inference/risk_formula.py`

- **Purpose:** Explainability module for audit-friendly risk score breakdown.
- **Problems Found:**
  - **[High]** This module uses `SIGNAL_WEIGHTS` from config (keys: `attendance`, `grades`, `engagement`, `submissions`) but maps them to `academic`, `engagement`, `consistency`, `intent`, `responsiveness`. The `attendance` weight is mapped to `engagement_signal_score`, `grades` to `academic_signal_score`, etc. This mapping is undocumented and misaligns with `RiskScorer.FEATURE_WEIGHTS` which uses entirely different keys. **Three incompatible weight schemas exist in the system.**
  - **[Medium]** The module is described as "for EXPLAINABILITY and AUDITING" but is called by neither the primary risk pipeline nor the API routes. It appears to be dead code in the current flow.
  - **[Low]** `signal_value = signals.get(signal_key, 0.5)` — defaults missing signals to neutral (0.5). This means an explanation generated for a student with no data shows equal contributions across all factors, which is misleading.
- **Severity:** High (conflicting weight definitions)

---

### File: `backend/services/ai/llm_orchestrator.py`

- **Purpose:** Multi-provider LLM integration (Gemini and Claude) with RAG-based context grounding.
- **Problems Found:**
  - **[High]** This entire service is **never called from any route**. The `LLMOrchestrator`, `RAGEngine`, and `HallucinationGuard` architecture exists in `backend/services/ai/` but is disconnected from the API layer. The `/llm` and `/advisor` routes use separate stub implementations.
  - **[Medium]** `LLMOrchestrator.__init__` creates database-backed retrievers (`StudentDataRetriever(db)`, etc.) at construction time. For a request-scoped instantiation, this ties object lifetime to a DB session, which is correct. But if instantiated globally, this would cause session lifetime issues.
  - **[Medium]** `_invoke_llm()` raises `RuntimeError` on LLM failure, which will surface as HTTP 500 to clients without a user-friendly message.
  - **[Low]** Gemini is configured globally via `genai.configure(api_key=GEMINI_API_KEY)` at module import time. If the API key changes, a restart is required.
- **Severity:** High (dead code)

---

### File: `backend/core/auth.py`

- **Purpose:** JWT creation and password hashing.
- **Problems Found:**
  - **[Medium]** `datetime.utcnow()` is deprecated in Python 3.12. Should use `datetime.now(timezone.utc)`.
  - **[Low]** `expires_delta or timedelta(minutes=15)` defaults to 15 minutes when no delta is provided, but `ACCESS_TOKEN_EXPIRE_MINUTES` defaults to 60 in config. This inconsistency means direct calls to `create_access_token()` without a delta get a shorter expiry than expected.
- **Severity:** Low-Medium

---

### File: `backend/api/deps.py`

- **Purpose:** FastAPI dependency injection — authentication + authorization.
- **Problems Found:**
  - **[Low]** `get_db_async()` is a standard sync generator marked as `async`. FastAPI will run it in a thread pool, but since it's an `async def` generator it should use `AsyncGenerator` properly. The current implementation works but is semantically misleading.
  - **[Low]** The `__all__` export list includes `get_db_async` which is somewhat redundant since it's exposed through the module namespace anyway.
- **Severity:** Low (functionally correct)

---

### File: `frontend/src/services/api.js`

- **Purpose:** Central Axios API client with request/response interceptors.
- **Problems Found:**
  - **[High]** `getStudentList` calls `GET /students/students` with `skip/limit/sort_by/order` params. The backend response shape is `{ students: [...], total, page, page_size }`. But `StudentContext.js` reads `response.data?.items` — this is a **critical shape mismatch**.
  - **[Medium]** `showGlobalToast()` is a DOM-manipulation function inside the API module. This mixes concerns and bypasses React's rendering lifecycle. The toast uses `container._hideTimer` — attaching properties directly to DOM elements is not a standard pattern.
  - **[Medium]** The 401 handler redirects to `/login` using `window.location.href`. This causes a full page reload, losing all React state. In SPA apps, `useNavigate` should be used instead.
  - **[Low]** `API_BASE_URL` is defined independently in both `api.js` and `AuthContext.js`. If one is updated without the other, login will target a different base URL than all other requests.
- **Severity:** High (shape mismatch)

---

### File: `frontend/src/context/AuthContext.js`

- **Purpose:** Authentication state provider with login/logout logic.
- **Problems Found:**
  - **[Medium]** JWT stored in `sessionStorage` instead of `localStorage`. While this prevents persistence across browser sessions (a minor security benefit), it also means the user must re-login after every tab close. For a staff-facing platform used throughout the day, this is a poor UX choice.
  - **[Medium]** Duplicate `API_BASE_URL` definition — see `api.js`. Both must be kept in sync manually.
  - **[Low]** `login()` does not validate the JWT structure before storing it. A corrupted or non-JWT response would be stored and then fail silently on the next request.
- **Severity:** Medium

---

### File: `data_ingestion/` (root-level module)

- **Purpose:** Appears to be an older, parallel data ingestion pipeline.
- **Files:** `loader.py`, `merger.py`, `normalizer.py`, `schema_mapper.py`, `validator.py`, `master_builder.py`, `dataset_cache.py`, `ingestion_logger.py`
- **Problems Found:**
  - **[High]** This module is **not imported or called from anywhere in the backend**. It is orphaned code at the project root, likely a predecessor to `backend/services/core/data_ingestion.py`. It creates confusion about which pipeline is authoritative.
  - **[Medium]** The module has its own `dataset_cache.py` — a file-based cache. If someone runs this module, it will create cache files in the working directory.
  - **[Low]** No `__init__.py` configuration makes it importable as a package — could clash with `backend/ingestion/` (another separately-named ingestion module that is ALSO unused).
- **Severity:** High (confusion over authoritative pipeline)

---

### File: `backend/ingestion/` (backend sub-module)

- **Purpose:** A third data ingestion system with `pipeline.py`, `validated_pipeline.py`, `file_validator.py`, etc.
- **Problems Found:**
  - **[High]** This is yet another ingestion pipeline that is **never imported or called**. The actual ingestion is in `backend/services/core/data_ingestion.py`. Three ingestion systems exist in the same repository, none of which are clearly labeled as the authoritative one.
- **Severity:** High (code confusion)

---

### File: `backend/routes/analytics.py`

- **Purpose:** Analytics endpoints (risk trends, KPI cards, drill-down).
- **Problems Found:**
  - **[Medium]** Role check uses `require_role(["Faculty", "Retention Team", "Admin"])` — title-case strings. The `require_role()` function lowercases comparison, so this works, but it is inconsistent with `_STAFF_ROLES = ["faculty", "admin", "retention team"]` used elsewhere.
  - **[Medium]** `AnalyticsService.get_risk_trends()`, `.get_kpi_cards()`, `.get_drill_down()` are called but `analytics_service.py` is a separate file — if those methods don't exist or throw, there's no fallback.
- **Severity:** Medium

---

### File: `backend/services/analytics_service.py`

- **Purpose:** Aggregate analytics queries.
- **Not read in detail, but from imports and usage:**
  - `AnalyticsService.get_risk_trends()`, `get_top_risk_velocity()`, `get_kpi_cards()`, `get_drill_down()` are called from routes but implementation quality not fully audited.
- **Severity:** TBD (needs separate deeper audit)

---

### File: `backend/middleware/security_logging.py`

- **Purpose:** Request/response access logging middleware.
- **Problems Found:**
  - **[Medium]** `client_ip = request.client.host` — if the application is behind a reverse proxy (Nginx, AWS ALB), `request.client.host` will be the proxy IP, not the real client IP. There is no `X-Forwarded-For` extraction.
  - **[Medium]** The middleware catches all unhandled exceptions and returns `{"detail": "Internal server error"}` (non-standard envelope) instead of the app's standard `{"success": false, "message": "..."}` format. The unhandled exception handler in `main.py` uses `error_response()` for the same case — **two different 500 response shapes** can be returned depending on where in the middleware stack the exception is raised.
  - **[Low]** Logs contain full URL paths. Since student IDs are email addresses, all student-facing URLs will log PII (email addresses) to the log file.
- **Severity:** Medium

---

### File: `backend/routes/auth.py`

- **Purpose:** Login, registration, profile management, admin user management.
- **Problems Found:**
  - **[Low]** `admin_update_user()` has `dependencies=[Depends(deps.require_role(["admin"]))]` AND `current_user: User = Depends(deps.require_role(["admin"]))` — the role check runs twice per request. Functionally harmless but wasteful.
  - **[Low]** The best-effort audit log uses a separate `db.commit()` after the user update commits. If this second commit fails (e.g., disk full), the audit entry is lost silently, which is documented but worth noting.
- **Severity:** Low (correct behavior, minor inefficiency)

---

### File: `docker/Dockerfile` and `docker/Dockerfile.scheduler`

- **Purpose:** Multi-stage production builds.
- **Problems Found:**
  - **[Medium]** The `Dockerfile` does not copy the `data/` folder. The backend relies on XLSX files in `backend/data/` for ETL. These files are not bundled into the image — the container will fail ETL at startup unless the data is mounted or pre-baked.
  - **[Medium]** The scheduler `CMD` uses Python inline code (`python -c "import asyncio..."`) — this is fragile, bypasses error reporting, and is difficult to debug.
  - **[Low]** `libpq-dev` is installed in the builder stage (Postgres client library), but the application uses SQLite. This is an unnecessary dependency.
  - **[Low]** Health check in `Dockerfile.scheduler` uses `pgrep -f "scheduler"` — this requires the `procps` package which is not installed in `python:3.12-slim-bookworm`.
- **Severity:** Medium (data files not in image = startup failure)

---

### File: `frontend/src/constants/riskThresholds.js`

- **Purpose:** Frontend risk threshold constants.
- **Problems Found:**
  - **[Medium]** `INTERVENTION_THRESHOLDS.GENTLE_REMINDER = 60` and `INTERVENTION_THRESHOLDS.MENTOR_OUTREACH = 80` — both map to the same category boundary (60-80 = mentor_outreach, then 80+ = urgent). The URGENT threshold is also 80, making `MENTOR_OUTREACH` and `URGENT` identical. Frontend intervention categorization at `risk >= 60` would jump directly from "gentle_reminder" to the 60-80 gap, with no label for that range.
  - **[Low]** These threshold values are duplicated from `backend/config/__init__.py` with no shared source of truth. If backend thresholds change, the frontend will silently categorize risk differently.
- **Severity:** Medium

---

## 6. Folder-Level Issues

### Backend Architecture

| Issue | Severity |
|---|---|
| Three separate ingestion systems (`backend/services/core/data_ingestion.py`, `backend/ingestion/`, `data_ingestion/`) — only one is used | High |
| `LLMOrchestrator` + `RAGEngine` architecture fully built but never wired to any route | High |
| `ml/models/saved/*.joblib` models exist but are intentionally disabled due to feature schema mismatch | High |
| Canonical star-schema tables (`dim_*`, `fact_*`) created but never populated | High |
| `DataLineage` table exists but ETL never writes to it | Medium |
| Two risk scoring systems: `RiskScorer` (0-100, feature-based) and `risk_formula.py` (0-1, signal-based) are incompatible and not reconciled | High |

### Frontend Architecture

| Issue | Severity |
|---|---|
| `StudentContext.js` expects `items` key; backend returns `students` key — entire frontend student data pipeline is broken | Critical |
| `AuthContext.js` and `api.js` both define `API_BASE_URL` independently | Medium |
| JWT stored in `sessionStorage` — lost on tab close, forcing re-login | Medium |
| Some pages (`BusinessAnalytics`, `Insights`) may rely on `StudentContext` which is empty due to the shape mismatch | Critical |

### Data Layer

| Issue | Severity |
|---|---|
| SQLite used in a multi-container deployment — not suitable for production concurrency | High |
| Date fields stored as `String` in `Enrollment` model — no temporal analytics possible | Medium |
| Prediction scale duality (0-1 in DB, 0-100 in API) creates ongoing conversion bugs | High |
| Unbounded growth of `predictions` and `risk_snapshots` tables — no pruning strategy | Medium |

### Config & Environment

| Issue | Severity |
|---|---|
| `RISK_THRESHOLD_HIGH=0.7` in `.env.example` vs `70.0` default in config — 100x scale discrepancy | High |
| `AVERAGE_STUDENT_LTV=12500` in `.env.example` vs `150000` in config — 12x discrepancy | High |
| `GEMINI_MODEL=gemini-pro` in `.env.example` is deprecated by Google (should be `gemini-1.5-pro` or later) | Medium |
| `CLAUDE_MODEL=claude-3-opus-20240229` is outdated | Low |
| `LLM_TEMPERATURE=0.7` in `.env.example` vs `0.3` default in config | Low |

---

## 7. Cross-Layer Issues

### Frontend ↔ Backend Response Shape Mismatch

| Contract | Backend Returns | Frontend Expects | Impact |
|---|---|---|---|
| `GET /students/students` | `{ students: [...], total, page, page_size }` | `response.data?.items` | **Critical** — students array always empty |
| `GET /predictions/batch` | `risk_score: 0-1` | Components display as 0-100 | **High** — all predictions show as < 1% risk |
| `GET /students/students/{id}` | `risk_score: 0-100` | Used directly | Correct |

### Prediction Scale Confusion (Cross-Service)

```
RiskScorer.calculate_risk_score()  → 0-100
MLService.predict_student()        → stores 0-100 internally
MLService.persist_prediction()     → divides by 100 → stores 0-1 in DB
StudentService._prediction_risk_to_0_100() → multiplies by 100 → 0-100 for API
StudentService.build_prediction_payload()  → divides by 100 → 0-1 for /predictions
```
Any step in this chain that skips the conversion produces a wrong value with no error.

### ML Model ↔ DB Feature Schema

The trained XGBoost model in `ml/models/saved/retention_model_xgboost.joblib` expects 32 features (absrate, mpa, nsusp, mobility schema). The DB-derived features are completely different (content_completion_score, quiz_engagement_score, login_consistency_score, etc.). **The ML model has never been used and cannot be used without full retraining on DB features.**

### Risk Weight Schema Triple Conflict

| Location | Weight Keys | Scale |
|---|---|---|
| `config.py::SIGNAL_WEIGHTS` | attendance, grades, engagement, submissions | Sum = 1.0 |
| `RiskScorer.FEATURE_WEIGHTS` | content_completion_score, login_consistency_score, quiz_engagement_score, assignment_score, time_investment_score, discussion_engagement_score | Sum = 1.0 |
| `risk_formula.py` | academic, engagement, consistency, intent, responsiveness | Mapped from SIGNAL_WEIGHTS |

These three systems produce different risk scores and none are reconciled.

### ETL ↔ DB Schema

- `data_ingestion.py` never writes to `dim_students`, `dim_courses`, `fact_academic_performance`, `fact_engagement`, `fact_consistency`, `fact_intent_responsiveness`, or `data_lineage`.
- `GradedComponent.course_code` is set from the XLSX header but `ExamRecord` creates a synthetic `course_code="EXAM_DEFAULT"` for defaulters, polluting the table with non-exam records.

### Auth ↔ Middleware Conflict

- `POST /auth/login` sends `application/x-www-form-urlencoded`
- `request_validation_middleware` rejects non-JSON bodies with content-length > 0
- **Result:** No user can log in via the standard OAuth2 flow

### Docker DB Path Mismatch

| Container | `DATABASE_URL` | DB File |
|---|---|---|
| `backend` (docker-compose) | `sqlite:///./backend/ews_platform.db` | `ews_platform.db` |
| `scheduler` (docker-compose) | (not set) → config default | `backend/data/sql_app.db` |
| `backend` (Dockerfile default) | `backend/data/sql_app.db` | `sql_app.db` |

Three different possible DB file targets. All containers may write to different files.

---

## 8. Risk Summary

### 🔴 Critical Issues (Must Fix Immediately)

1. **`request_validation_middleware` blocks all logins** (`backend/middleware/request_validation.py`) — OAuth2 form-encoded requests receive HTTP 415. Zero users can authenticate.

2. **`StudentContext.js` expects `items` key; API returns `students` key** — all student lists in the frontend are empty arrays. The entire platform UI is non-functional.

3. **Docker-compose scheduler uses wrong module path** (`docker/docker-compose.yml`) — `python -m backend.services.scheduler` does not exist. Scheduler container crashes on start; no daily predictions are generated.

4. **Docker DB path mismatch** — backend and scheduler containers potentially target different SQLite files, causing data inconsistency.

---

### 🟠 High Priority Issues

5. **Three incompatible ingestion modules** (`data_ingestion/`, `backend/ingestion/`, `backend/services/core/`) — authoritative pipeline is ambiguous.

6. **Risk weight schemas triple conflict** — `config.py`, `RiskScorer`, and `risk_formula.py` use three different weight schemas that cannot produce consistent risk scores.

7. **ML model permanently disabled** — XGBoost model was trained on a different feature schema and cannot be used. The system is rule-based-only with no ML roadmap.

8. **LLM routes are stubs** — `/llm/*` and `/advisor/*` routes return hardcoded mock text. `LLMOrchestrator` is built but disconnected. Users believe AI is active.

9. **Canonical star-schema tables permanently empty** — 7 tables created, never populated, consuming DB space and creating misleading architecture documentation.

10. **`business.py` fabricated metrics** — executive dashboard shows hardcoded trend strings (`"+2.1%"`, `"-3.5%"`) and ROI calculations based on fictional recovery rates (35%).

11. **`business.py` loads all 5000 students per request** — no DB-level aggregation; entire student corpus loaded into Python memory for every BI dashboard request.

12. **`redis_cache.py` `@cache_response` decorator is broken** — JSON-serialization of SQLAlchemy sessions will always raise `TypeError`.

13. **`AVERAGE_STUDENT_LTV` 12x discrepancy** between config default and `.env.example` — revenue-at-risk figures could be off by 12x.

14. **`RISK_THRESHOLD_HIGH` scale discrepancy** — `0.7` in `.env.example` vs `70.0` in config — if deployed from the example file, all thresholds are wrong.

---

### 🟡 Medium Issues

15. **Prediction scale duality (0-1 DB, 0-100 API)** — multiple silent conversion points; any missed conversion produces wrong values with no error.

16. **`Enrollment` date fields stored as `String`** — no temporal analytics, no "last active" queries, no date-based sorting at DB level.

17. **`DataLineage` table never written to** — ETL runs are completely untracked; no audit trail of data ingestion.

18. **`predictions` and `risk_snapshots` tables grow unboundedly** — no retention policy or pruning; will eventually impact query performance.

19. **`MLService._cache` unbounded in-memory dict** — grows without eviction; lost on restart; not shared across workers.

20. **`mlservice.persist_prediction` rolls back session on failure** — may cancel unrelated pending changes in the same session.

21. **`datetime.utcnow()` used throughout** — deprecated in Python 3.12; mixed naive/aware datetimes cause comparison errors.

22. **`AuthContext.js` and `api.js` duplicate `API_BASE_URL`** — divergence risk.

23. **`get_student_weekly_summary()` returns hardcoded zeros** for `missedAssignments`, `lowEngagementDays`, `facultyInteractions`.

24. **`data_ingestion.py` loads entire `GradedComponent` and `ExamRecord` tables** into memory per ingestion run — O(n) RAM for each ETL execution.

25. **`Intervention` list/create endpoints require no role** — any authenticated user (including student-role) can see all interventions.

26. **`create_intervention()` accepts arbitrary `user` string** — no validation against authenticated user.

27. **Middleware 500 response uses non-standard envelope** — `{"detail": "..."}` instead of `{"success": false, "message": "..."}`.

28. **`client_ip` logged from `request.client.host`** — behind proxy, logs proxy IP not real client.

---

### 🟢 Low Priority Issues

29. **`SecurityManager` class is dead code** — never imported or called.
30. **`APScheduler` in requirements.txt but not used** — the scheduler uses raw asyncio, not APScheduler.
31. **Duplicate `from fastapi import Depends`** in `interventions.py`, `predictions.py`, `advisor.py`.
32. **`Dockerfile.scheduler` health check uses `pgrep`** — `procps` not installed in slim image.
33. **`libpq-dev` in Dockerfile** — Postgres client library included but only SQLite is used.
34. **`GEMINI_MODEL=gemini-pro`** in `.env.example` — deprecated model name.
35. **`CLAUDE_MODEL=claude-3-opus-20240229`** in `.env.example` — outdated model version.
36. **`LLM_TEMPERATURE` inconsistency** between `.env.example` (0.7) and config default (0.3).
37. **Alembic and `create_all()` coexist** — schema may diverge; migrations unreliable.
38. **`admin_update_user()` runs role check twice** — `dependencies=` and `Depends()` both call `require_role(["admin"])`.
39. **`advisor.py` `get_advisor_context()`** always returns `total_interventions: 0` — never queries DB.
40. **`_error_prediction()` returns `risk_score: 50.0`** — silent "medium" fallback on prediction failure; undetectable by callers.

---

### 🧱 Architectural Risks

1. **SQLite in multi-container production** — WAL mode allows one writer. Concurrent writes from API + scheduler will serialize, causing latency spikes. Any data volume growth will require a full migration to PostgreSQL.

2. **No real-time data pipeline** — data is ingested from XLSX snapshots at startup. There is no mechanism to receive updated engagement data without a server restart. The platform is essentially operating on stale snapshots.

3. **Three parallel ingestion codebases** with no clear ownership create a maintenance burden and risk of conflicting logic being reintroduced.

4. **`StudentService.get_all_students(db, 0, 5000)`** called from multiple business routes — this is an anti-pattern that will not scale. As enrollment grows, every BI dashboard request becomes a full-table scan.

5. **No pagination or streaming in ML batch endpoints** — `POST /ml/predict-batch` processes all requested IDs sequentially in a single request, with no chunking or background job queue.

---

### 🔐 Security Risks

1. **Authentication is broken** (request_validation_middleware blocks login) — no user can authenticate in the standard flow.

2. **Intervention data exposed to all authenticated users** — student-role users can list all interventions via `GET /interventions`.

3. **`create_intervention()` user field not validated** against JWT identity — impersonation possible.

4. **Student PII (email addresses) in URL paths and logs** — `GET /students/students/user@domain.com`, logged in plaintext.

5. **`SecurityManager.sanitize_input()` is dead code** — despite being in `core/security.py`, it is never called. No input sanitization is applied.

6. **LLM prompts include full student data context** (`LLMOrchestrator`) — if the real LLM integration were activated, full student profiles including risk scores, engagement data, and names are sent to external AI providers without explicit data-sharing consent workflow.

7. **Sensitive data in XLSX files is not encrypted at rest** — `backend/data/*.xlsx` contains student records. The Docker volume mounting these files has no encryption.

---

### 📉 Performance Risks

1. **`StudentContext.js` fetches 2000 students on every page load** — blocks UI rendering until full response received. No pagination, no lazy loading.

2. **Multiple business endpoints load all 5000 students per request** — no DB aggregation; O(n) Python memory per API call.

3. **`get_intervention_effectiveness()` fetches 2000 students** to compute risk-now values.

4. **Scheduler loads all DB rows into RAM** every daily run — 3 full table scans before per-student processing.

5. **`predictions` table grows by n_students per day** with no pruning — after 1 year with 500 students, the table has 182,500 rows. Queries scanning this table will degrade.

6. **No index on `Prediction.prediction_timestamp`** — the many queries filtering/ordering by timestamp (trend analysis, scheduler) will do full table scans as the table grows.

---

### 🧠 ML/Data Risks

1. **The XGBoost model is permanently disabled** and has never produced a prediction. All risk scores are rule-based heuristics.

2. **Normalization denominators in `FeatureEngineer` are arbitrary magic numbers** (20 quizzes, 100 logins, 20 hours) — not calibrated to actual institution data. Risk scores may be systematically biased.

3. **No ground truth labels for model validation** — `backend/data/labels.csv` exists but the training pipeline is disconnected. There is no mechanism to measure prediction accuracy against actual dropout outcomes.

4. **`DataLineage` table is empty** — no audit trail of which XLSX snapshots contributed to which student risk scores.

5. **`ExamRecord` table contaminated** with synthetic `course_code="EXAM_DEFAULT"` rows — exam score calculations may include these non-exam records if not filtered.

6. **`RiskSnapshot` stores `engagement_score`** as `content_completion * 0.6 + attendance * 0.4`. This formula is not documented, not configurable, and inconsistent with `MLService`'s engagement calculation.

---

## 9. Refactor Strategy

### Priority 1 — Immediate Stabilization (Fix before any user testing)

1. **Fix `request_validation_middleware`** to exempt `application/x-www-form-urlencoded` for `/auth/login`, or explicitly whitelist the login path.

2. **Fix the `StudentContext.js` response key mismatch** — change `response.data?.items` to `response.data?.students`, or rename the backend controller response key to `items` and update total/pagination fields consistently.

3. **Fix docker-compose scheduler command** — change `python -m backend.services.scheduler` to `python -m backend.services.infrastructure.scheduler`, or better, use a proper `CMD` in `Dockerfile.scheduler`.

4. **Fix docker-compose DATABASE_URL** — ensure all containers use the same database path, and align `docker-compose.yml` with the config defaults.

---

### Priority 2 — Backend Refactor Plan

1. **Resolve the triple weight schema conflict** — choose one weight system. Deprecate `risk_formula.py` (explainability) or align it with `RiskScorer.FEATURE_WEIGHTS`. Remove `SIGNAL_WEIGHTS` from config or map them explicitly.

2. **Standardize risk score scale** — choose 0-100 as the single in-flight scale throughout all services. Store as 0-1 in DB (for ML probability semantics), but add a model layer that handles scale consistently, not scattered conversions.

3. **Remove dead code** — delete `backend/ingestion/`, `data_ingestion/` (root), `backend/core/security.py`'s `SecurityManager` class, the `@cache_response` decorator, and the `APScheduler` dependency.

4. **Wire LLM routes to `LLMOrchestrator`** — replace stub responses in `/llm` and `/advisor` with real `LLMOrchestrator` calls, or clearly mark them as "demo mode" in the UI.

5. **Add role restriction to Intervention endpoints** — restrict `list_interventions` and `create_intervention` to staff roles. Validate `body.user` against `current_user.username`.

---

### Priority 3 — Data Layer Fix Plan

1. **Normalize `Enrollment` date fields** from `String` to `DateTime` — allows proper date arithmetic, recency filtering, and "last active" queries.

2. **Add `Prediction` table pruning** — keep only the last N predictions per student (e.g., 90 days) to prevent unbounded growth.

3. **Add a `PredictionIndex`** on `(student_id, prediction_timestamp DESC)` — the scheduler and trend endpoints query this pattern heavily.

4. **Populate or drop canonical tables** — either wire the ETL to populate `dim_students`, `fact_engagement`, etc., or remove them to reduce schema confusion.

5. **Write ETL runs to `DataLineage`** — every ingestion call should create a `DataLineage` record with file path, row counts, and timestamp.

---

### Priority 4 — ML Fix Plan

1. **Calibrate `FeatureEngineer` normalization denominators** against actual institution data — compute percentile-based normalization instead of hardcoded values. P90 of `num_logins` across all students is a more defensible denominator than `100`.

2. **Build a model retraining pipeline** — once `labels.csv` has sufficient dropout outcomes, create a training script that uses DB-derived features (not the old absrate/mpa schema). Target the DB feature schema that `FeatureEngineer` already produces.

3. **Add model validation infrastructure** — before enabling a new model, validate it on a holdout set and log precision/recall to `DataLineage`.

4. **Fix `MLService._cache`** — replace with TTL-based Redis caching keyed by `(student_id, prediction_date)`. Evict entries older than 24 hours.

---

### Priority 5 — Testing Plan

Current test files exist but their coverage and pass/fail status is unknown. Minimum test coverage needed:

1. **Authentication flow** — integration test for login → JWT → protected route.
2. **`StudentContext` integration** — mock API, verify `items` key handling.
3. **Risk score pipeline** — unit test `FeatureEngineer` → `RiskScorer` with known inputs and expected outputs.
4. **ETL idempotency** — run `ingest_all_data()` twice on the same data; verify row counts don't double.
5. **Scale conversion** — property-based tests verifying 0-1 ↔ 0-100 conversions are consistent across all service boundaries.

---

### Priority 6 — CI/CD Hardening Plan

1. **Add `pytest` to the Docker build** — run tests during CI before pushing image.
2. **Add a `docker-compose.override.yml`** for local development with correct database paths.
3. **Add `bandit` security linter** to CI to detect secrets in code.
4. **Pin `Dockerfile` base image digest** — `python:3.12-slim-bookworm@sha256:...` for reproducibility.
5. **Add a pre-commit hook** that runs `mypy` or at least checks for `datetime.utcnow()` usage.

---

### Priority 7 — Production Readiness Checklist

- [ ] **Authentication works end-to-end** (fix middleware)
- [ ] **Frontend students list is non-empty** (fix response key)
- [ ] **Scheduler runs correctly** (fix module path + DB path)
- [ ] **All containers target the same database** (align DATABASE_URL)
- [ ] **Replace SQLite with PostgreSQL** before going beyond ~100 concurrent users
- [ ] **LLM routes clearly labeled** as "demo" or wired to real LLM
- [ ] **Business dashboard KPIs** sourced from real data, not hardcoded strings
- [ ] **XLSX data files mounted into containers** (not missing from Docker image)
- [ ] **Prediction table pruning** scheduled to prevent unbounded growth
- [ ] **Rate limiting per-endpoint** for sensitive routes (login, LLM calls)
- [ ] **PII logging review** — remove email addresses from URL-path log entries
- [ ] **Timezone standardization** — all datetimes stored as UTC-aware
- [ ] **ML model retrained** on DB-derived features before `model_used: true` is surfaced in UI
- [ ] **Intervention RBAC** — restrict to staff roles only
- [ ] **`DataLineage` ETL tracking** enabled
- [ ] **Secret rotation** documented and tested

---

*End of Audit Report — `FULL_PROJECT_AUDIT.md`*
