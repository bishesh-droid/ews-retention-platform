# Meridian — EWS Retention Platform

**Version:** 2.1.0  
**Status:** Production-grade prototype. Operational with active data. Several architectural issues documented below must be resolved before genuine production deployment.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Folder-by-Folder Breakdown](#3-folder-by-folder-breakdown)
4. [Data Flow — Step by Step](#4-data-flow--step-by-step)
5. [API Documentation](#5-api-documentation)
6. [Authentication and Security Model](#6-authentication-and-security-model)
7. [ML System Explanation](#7-ml-system-explanation)
8. [Setup Instructions](#8-setup-instructions)
9. [Known Issues and Risks](#9-known-issues-and-risks)
10. [Improvement Roadmap](#10-improvement-roadmap)

---

## 1. Project Overview

Meridian is an Early Warning System (EWS) for student retention at a data science / AI graduate program. It ingests LMS engagement data from Microsoft Excel exports, engineers behavioral and academic features, computes dropout risk scores, and surfaces those scores to advisors and faculty through a React dashboard.

### What the system actually does

- Reads student engagement data from XLSX files (Brightspace LMS exports) on startup and loads it into a local SQLite database.
- Derives six engagement features per student (content completion, login consistency, quiz engagement, assignment submissions, time investment, discussion engagement).
- Runs a rule-based dropout risk scorer that produces a 0–100 risk score where higher = higher dropout risk.
- Schedules a daily job (03:00 UTC) that recomputes risk scores for every student and persists predictions and risk snapshots to the database.
- Exposes a FastAPI REST API with 20+ route modules covering students, predictions, interventions, analytics, LLM queries, business intelligence, and more.
- Serves a React SPA that displays student risk tables, trend charts, cohort analytics, intervention management, and AI-generated narratives.
- Optionally invokes Google Gemini or Anthropic Claude for natural-language risk explanations and advisor recommendations (requires API keys).

### What the system does NOT do

- Does NOT use the saved XGBoost or LogReg joblib models in live scoring. There is a confirmed schema mismatch between training data features and runtime features. The inference pipeline was deleted.
- Does NOT automatically retrain models. The weekly retraining scheduler job is a logged no-op placeholder.
- Does NOT have a real-time LMS data feed. Data is ingested from static XLSX snapshots that must be manually exported and placed in `backend/data/`.
- The frontend does NOT authenticate against the backend JWT system. It performs a client-side credential check against hardcoded values and does not send Authorization headers to the backend. This is a critical security gap.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  React SPA (localhost:3000)                                          │
│  Create React App + Bootstrap 5 + Chart.js v4 + Recharts             │ 
│                                                                      │
│  AuthContext ── hardcoded "admin"/"admin123" check                   │
│               ── no backend call, no JWT obtained                    │
│                                                                      │
│  StudentContext → api.js → fetch() → NO Authorization header         │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ HTTP requests (unauthenticated)
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI Application (localhost:8000)  — backend/main.py             │
│                                                                      │
│  Middleware (outermost → innermost):                                 │
│    security_and_logging_middleware  — 100 req/min rate limit + logs  │
│    request_validation_middleware    — JSON Content-Type enforcement  │
│    CORSMiddleware                   — configurable origins           │
│                                                                      │
│  Exception handlers: AppError, HTTPException, Exception              │
│                                                                      │
│  /api/v1/* ─── api_router (22 sub-routers)                           │
│                                                                      │
│  Lifespan startup:                                                   │
│    1. init_db()         → SQLite schema creation                     │
│    2. ingest_all_data() → ETL from XLSX (non-blocking task)          │
│    3. scheduler.start() → daily prediction + weekly retrain tasks    │
└──────────┬──────────────────────────────────────────┬───────────────┘
           │                                          │
           ▼                                          ▼
  ┌────────────────┐                      ┌─────────────────────┐
  │  SQLite DB     │                      │  LLM Providers      │
  │  sql_app.db    │                      │                     │
  │  25+ tables    │                      │  Gemini (default)   │
  │                │                      │  Claude (alt)       │
  └────────────────┘                      │  Both optional      │
           ▲                              └─────────────────────┘
           │
  ┌────────────────────────┐
  │  XLSX Source Files     │
  │  backend/data/         │
  │  9 files configured    │
  │  1 required at startup │
  └────────────────────────┘
```

### Backend Service Layer Relationships

```
HTTP Request
     │
     ▼
Routes (backend/routes/)
     │
     ├── Simple CRUD → DB models (direct SQLAlchemy queries)
     │
     └── Complex logic → Services (backend/services/)
                              │
                              ├── StudentService
                              │       → FeatureEngineer (feature_engineering.py)
                              │       → RiskScorer (risk_scoring.py)
                              │       → DB queries (Student, Enrollment, Prediction, ...)
                              │
                              ├── LLMOrchestrator (services/ai/)
                              │       → RAG engine (rag_engine.py)
                              │       → Gemini / Claude
                              │
                              ├── SchedulerService (services/infrastructure/)
                              │       → FeatureEngineer + RiskScorer (daily job)
                              │
                              └── Supporting services
                                      analytics_service, audit_service,
                                      goals_service, export_service, etc.
```

---

## 3. Folder-by-Folder Breakdown

### Root Level

| Path | Purpose |
|---|---|
| `backend/` | FastAPI application |
| `frontend/` | React SPA |
| `backend/data/` | SQLite DB and XLSX source files |
| `docs/` | Supplementary documentation |
| `requirements.txt` | Python dependencies |
| `.env.example` | Configuration template |
| `ARCHITECTURE.md` | Deep system design |
| `DATA_FLOW.md` | Pipeline specification |
| `ML_PIPELINE.md` | ML scoring breakdown |
| `SECURITY.md` | Vulnerability analysis |

---

### `backend/`

**`main.py`** — Application entry point. Defines `lifespan()` async context manager for startup/shutdown. Creates the FastAPI instance with title, description, version. Registers middleware (CORS, security logging, request validation). Registers global exception handlers. Mounts all routes at `/api/v1`. Exposes `/` and `/health` without authentication.

**`config/__init__.py`** — Central configuration. All settings read from environment variables with safe defaults. Groups: API/server, database, security/auth, LLM, logging, Redis, ML thresholds, intervention thresholds, business metrics, XLSX file paths. Contains a production fail-fast guard: if `ENVIRONMENT=production` and `SECRET_KEY` is still the insecure default, the application raises `RuntimeError` at startup.

**`__init__.py`** — Package marker.

---

### `backend/routes/`

22 route modules, all mounted under `/api/v1`. The `__init__.py` constructs the master `api_router` and includes each sub-router with its prefix and tags.

**`auth.py`** — Authentication and user management. Login (OAuth2 form), registration (role forced to "student"), profile view/update, admin-only user management. Token expiry matches `ACCESS_TOKEN_EXPIRE_MINUTES` config.

**`students.py`** — Thin wrapper that imports from `controllers/students_controller.py`. Preserved for backward import compatibility.

**`predictions.py`** — Batch predictions endpoint and per-student prediction. Delegates to `StudentService`. Supports `include_decisions=true` to append intervention recommendations.

**`ml_routes.py`** — ML-specific prediction endpoints. Runs inference in a thread via `asyncio.to_thread` with a 10-second timeout. Returns prediction metadata including whether the ML model or rule-based scorer was used. Persists results to the `predictions` table.

**`llm.py`** — Six LLM endpoints (risk explanation, student advice, faculty summary, intervention recommendation, what-if, report narrative). When no LLM API key is configured, returns structured mock responses built from student data.

**`interventions.py`** — Full CRUD for `interventions` table. Supports bulk creation (list of `student_ids`). Channels stored as JSON string in DB, parsed on read.

**`business.py`** — Business intelligence calculations. Revenue at risk, retention metrics, intervention ROI, retention funnel, cohort analysis. Uses configurable financial constants from config (student LTV, tuition, intervention cost).

**`analytics.py`** — Aggregated analytics summary and risk distribution.

**`advisor.py`** — AI academic advisor endpoint. Wraps `LLMOrchestrator` with student context retrieval.

**`events.py`** — Raw event ingestion and retrieval endpoints.

**`features.py`** — Feature store retrieval endpoints. Surfaces pre-computed `EngineeredFeatures` rows.

**`decisions.py`** — Decision engine endpoints. Routes to `decision_engine.py` service for intervention decision logic.

**`feedback.py`** — Student response/feedback CRUD.

**`recommendations.py`** — Recommendation retrieval endpoints.

**`goals.py`** — Goal creation, update, and retrieval per student.

**`reports.py`** — Report generation endpoints. Supports student-level and cohort-level reports with export capabilities.

**`student_v1.py`** — Student-facing portal endpoints (own data only).

**`faculty_v1.py`** — Faculty-facing endpoints (student lists, summary dashboards). Requires faculty or admin role.

**`admin_v1.py`** — Admin-only endpoints (system management, user listing).

**`retention_v1.py`** — Retention team endpoints.

**`integration.py`** — External system integration endpoints. Uses `INTEGRATION_API_KEY` for additional authentication.

**`monitoring.py`** — Health check and system metrics endpoints.

---

### `backend/controllers/`

**`students_controller.py`** — The most substantial controller in the codebase (412 lines). Provides all student-facing endpoints delegated from `routes/students.py`. Endpoints:

- `GET /overview` — Dashboard KPIs
- `GET /courses` — Course catalog
- `GET /students` — Paginated list with risk/sort/filter
- `GET /students/{id}` — Full student profile
- `GET /students/{id}/interventions` — Intervention history
- `GET /students/{id}/weekly-summary` — Lightweight portal summary
- `GET /students/{id}/risk-trend` — Risk time series from `predictions` table
- `GET /at-risk` — Students above threshold
- `GET /risk-distribution` — Risk score distribution
- `GET /analytics/trends` — Department/course analytics
- `GET /analytics/risk-trends` — Cohort risk time series (ISO week buckets)
- `GET /analytics/engagement-trends` — Cohort engagement time series
- `GET /analytics/performance-trends` — Cohort grade performance
- `GET /analytics/intervention-effectiveness` — Before/after risk comparison

The `_normalize_0_100()` helper in this file is the defensive normalization for the 0–1/0–100 storage ambiguity.

---

### `backend/services/`

**`student_service.py`** — Core orchestration service. `get_all_students()` executes a multi-table JOIN, then for each student computes features and risk score live from enrollment data, supplemented by the latest stored prediction if available. `build_prediction_payload()` and `build_intervention_recommendation()` are used by the predictions routes. `get_overview_stats()` returns KPI counts.

**`feature_engineering.py`** — `FeatureEngineer` static class with 9 calculation methods:
- `calculate_content_completion_score()` — content_completed / content_required × 100
- `calculate_w1w2_completion_score()` — W1-W2 content progress specifically
- `calculate_quiz_engagement_score()` — derived from quiz_completed and total_quiz_attempts
- `calculate_discussion_engagement_score()` — posts created, replies, reads
- `calculate_assignment_score()` — num_assignment_submissions relative to expected
- `calculate_time_investment_score()` — log-scaled seconds on platform
- `calculate_login_consistency_score()` — logins + recency
- `calculate_zero_progress_ratio()` — fraction of enrollments with zero content completion
- `calculate_all_features()` — calls all sub-methods and returns unified dict

**`risk_scoring.py`** — `RiskScorer` static class. Primary runtime risk scorer. Six feature weights summing to 1.0. Handles missing features by partial normalization. Adds zero-progress penalty. Returns 0–100. Also provides category labels, retention likelihood strings, dominant factor identification, and feature-level breakdown dicts.

**`services/core/data_ingestion.py`** — Idempotent ETL. Called at startup from `main.py` lifespan. Opens XLSX files with openpyxl. Implements upsert (get-or-create) for all entities. Only `Engagement_Analysis.xlsx` is required; all others are optional. Accumulates counter fields (content_completed, quiz_completed, etc.) across multiple source files using a defined `COUNTER_FIELDS` set.

**`services/core/ews_engine.py`** — EWS orchestration engine. Coordinates feature computation, risk scoring, and decision rules.

**`services/core/decision_engine.py`** — Maps risk scores to intervention decisions using configurable thresholds from config.

**`services/core/feature_service.py`** — Feature store read/write service.

**`services/infrastructure/scheduler.py`** — `SchedulerService` using asyncio tasks. `generate_daily_predictions()` runs at 03:00 UTC: loads all students, their enrollments, graded components, and exam records; computes features and risk; persists `Prediction` (risk_score/100) and `RiskSnapshot` (risk_score/100) rows; logs counts. `retrain_model_weekly()` at Sunday 04:00 UTC is a no-op. Both jobs are wrapped with exception handlers so a crash in one job does not stop the scheduler loop.

**`services/infrastructure/audit_logger.py`** — Writes `AuditLog` rows for significant user actions.

**`services/infrastructure/recommender.py`** — Rule-based recommendation engine for intervention suggestions.

**`services/ai/llm_orchestrator.py`** — Routes LLM requests to Gemini or Claude. Falls back to mock responses when no API key is configured or when libraries are absent. Uses conditional imports to avoid hard failures.

**`services/ai/rag_engine.py`** — Retrieval-augmented generation engine. Contains `StudentDataRetriever`, `CohortDataRetriever`, `InstitutionalDataRetriever`, `ContextAssembler`, `GuardrailValidator`. Grounds LLM prompts in real student data from the database.

**`services/ai/advisor.py`**, **`advisor_context.py`** — AI advisor service and context builder.

**`services/ai/faculty_summary.py`** — Faculty-facing AI summary generation.

**`services/ai/hallucination_guard.py`** — Input/output validation to reduce LLM hallucination.

**`services/ai/study_plan_generator.py`** — LLM-driven study plan generation.

**`services/analytics/intervention_intel.py`**, **`pattern_discovery.py`** — Deeper analytics services.

**`analytics_service.py`** — Aggregated analytics queries.

**`audit_service.py`** — Audit log retrieval.

**`export_service.py`** — CSV and PDF export generation.

**`feature_engineering.py`** (root services) — See above.

**`feature_store_service.py`** — Pre-computation and storage of `EngineeredFeatures` rows.

**`goals_service.py`** — Goal lifecycle management.

**`ml_service.py`** — Documents the three incompatible ML schemas. Attempts joblib model loading but logs schema mismatch warnings. Final scoring always falls back to `FeatureEngineer → RiskScorer`.

**`risk_consistency.py`** — Risk score validation and consistency checking utilities.

**`risk_scoring.py`** — See above (primary scorer).

---

### `backend/database/`

**`connection.py`** — SQLAlchemy engine creation (`check_same_thread=False` for SQLite), declarative `Base`, and `init_db()` which imports all models and runs `create_all`.

**`session.py`** — `SessionLocal` factory. `get_db()` and `get_db_async()` dependency generators with rollback-on-exception and guaranteed close.

**`models/`** — 25+ ORM model files:

| File | Models | Key Fields |
|---|---|---|
| `student.py` | `Student` | id (String PK = email/username), first_name, last_name, old_new_student, parent_department_name |
| `course.py` | `Course` | id (String PK), name, section_code, content_required |
| `enrollment.py` | `Enrollment` | student_id FK, course_id FK, 20+ engagement counter/date fields |
| `prediction.py` | `Prediction` | student_id FK, risk_score (Float, stored 0–1), engagement_score, signal breakdown scores, model_version |
| `intervention.py` | `Intervention` | student_id FK, date, action, status, ai_suggested, effectiveness_score, risk_score_at_trigger, channels (JSON string) |
| `goals_and_risks.py` | `RiskSnapshot`, `Goal` | RiskSnapshot: risk_score (0–1), velocity, acceleration, timestamp |
| `user.py` | `User` | username, email, hashed_password, role, is_active, is_superuser, preferences (JSON) |
| `academic.py` | `GradedComponent`, `ExamRecord` | Component: score, max_score, missed. Exam: marks_obtained, marks_total, present |
| `audit.py` | `AuditLog` | user_id FK, action, resource, details, timestamp |
| `llm.py` | `LLMQuery`, `LLMInsight`, `AIExplanation`, `PatternDiscovery` | LLM interaction history |
| `event.py` | `RawEvent`, `EngineeredFeatures` | Raw LMS events and pre-computed feature vectors |
| `feature.py` | `StudentResponse` | Student responses to interventions |
| `canonical.py` | `DimStudent`, `DimCourse`, `FactAcademicPerformance`, `FactEngagement`, `FactConsistency`, `FactIntentResponsiveness`, `DataLineage` | Data warehouse star schema tables |

---

### `backend/api/`

**`deps.py`** — FastAPI dependency injection. `reusable_oauth2` is an `OAuth2PasswordBearer` pointing to `/api/v1/auth/login` with `auto_error=True`. `get_current_user()` decodes JWT, fetches `User` row, checks `is_active`. `require_role()` is a factory that returns a checker dependency enforcing role membership (case-insensitive, superusers exempt). The file header documents a previously removed vulnerability where `X-User-Role` header was trusted and defaulted to admin.

---

### `backend/core/`

**`auth.py`** — JWT creation and bcrypt password operations. `create_access_token()` embeds `sub` (user ID), `role`, and `exp` in the token payload.

**`security.py`** — `SecurityManager` utility class. HTML tag stripping for basic input sanitization. `enforce_role()` and `validate_pagination()` helpers. Lightly used — primary enforcement is in `deps.py`.

**`redis_cache.py`** — Redis client wrapper that degrades gracefully to no-op when Redis is unavailable. `cache_response` decorator for route handlers.

**`logger.py`** — Structured logging configuration. Writes to console and `backend/backend.log`.

---

### `backend/middleware/`

**`security_logging.py`** — Combined rate limiting and access logging. Rate limit: 100 requests/minute per IP using an in-memory dict. Logs request method/path/IP on entry, adds status code and processing time on exit. **Limitation:** In-memory state is per-process and per-restart. No protection in multi-worker or multi-instance deployments.

**`request_validation.py`** — Validates Content-Type for POST/PUT/PATCH. Returns HTTP 415 if body is present and Content-Type is not `application/json`.

---

### `backend/ml/`

**`config.py`** — ML-specific constants. `REQUIRED_STUDENT_FEATURES = ['absrate7', 'q4mpa7', 'nsusp7', 'mobility7']` — the 4-feature schema of the saved models. Also imports risk thresholds from main config and converts to 0–1 scale.

**`models/saved/`** — Trained model artifacts:
- `retention_model_xgboost.joblib` — XGBoost classifier
- `retention_model_logreg.joblib` — Logistic Regression classifier
- `feature_importance.csv` — Feature importances from training

These models were trained on a different feature schema than what the live database contains. There is no code path to bridge the gap. They are preserved but functionally inert.

**`inference/risk_formula.py`** — Explainability-focused rule-based scorer. Accepts 5 signal scores (0–1). Returns 0–1. Uses `SIGNAL_WEIGHTS` from config. Provides `explain_risk_score()` (contribution breakdown) and `simulate_what_if()` (scenario simulation). **Important limitation:** The config `SIGNAL_WEIGHTS` keys are `attendance`, `grades`, `engagement`, `submissions` — but this module expects `academic`, `engagement`, `consistency`, `intent`, `responsiveness` as weight keys. The mapping in `get_signal_weights()` only covers 4 of the 5 signals; `consistency`, `intent`, and `responsiveness` receive weight 0.0 from `SIGNAL_WEIGHTS.get()`.

**`training/evaluate.py`** — Standalone evaluation utility (classification report, confusion matrix, seaborn heatmap). Called from a training script that no longer exists.

**`ml/utils/validation_utils.py`** — Input validation helpers for ML pipelines.

**`ml/features/__init__.py`**, **`ml/models/__init__.py`**, **`ml/inference/__init__.py`**, **`ml/training/__init__.py`** — Package markers. Empty or near-empty.

---

### `backend/features/`

A secondary feature engineering and scoring pipeline. Distinct from `backend/services/`. Queries the database directly. **Not called in the main prediction path.**

**`risk_scorer.py`** — `RiskScorer` class (different from `services/risk_scoring.py`). Queries `AcademicPerformanceSignal` and `EngagementSignal` with weights 0.45/0.55. Risk levels: Critical ≥75, High ≥50, Medium ≥25, Low <25.

**`academic_signals.py`** — Queries `GradedComponent` and `ExamRecord` tables to compute academic performance signal.

**`engagement_signals.py`** — Queries `Enrollment` table for engagement signal computation.

**`composite_indices.py`** — Multi-signal composite index calculations.

**`behavioral_features.py`** — Behavioral feature derivations.

**`temporal_features.py`** — Time-series-based features.

**`advanced_engagement_features.py`** — Advanced LMS engagement metrics.

**`signal_computer.py`** — Signal computation coordinator.

**`advanced_orchestrator.py`** — Orchestration for the secondary pipeline.

---

### `backend/ingestion/`

An alternative, more sophisticated ETL pipeline. **Not called at runtime.** Contains row-level validation, quarantine for bad records, schema management, and transformation logic. Architecturally more robust than the active `services/core/data_ingestion.py` but abandoned as the runtime path.

Key files: `pipeline.py`, `validated_pipeline.py`, `schema_manager.py`, `row_validators.py`, `transformers.py`, `validators.py`, `quarantine.py`, `file_validator.py`, `defaults.py`, `error_logger.py`.

---

### `backend/jobs/`

**`feature_store_job.py`** — Standalone script using the `schedule` library. Runs `FeatureStoreService.precompute_all_features()` once on startup, then hourly. Executed with `python -m backend.jobs.feature_store_job`. Not integrated with the main async scheduler.

---

### `backend/schemas/`

Pydantic v2 schemas for request/response validation.

- `auth.py` — `Token`, `UserOut`, `UserCreate`, `UserUpdate`, `AdminUserUpdate`
- `intervention.py` — `Intervention` response schema
- Additional schemas for students, predictions, features, goals, etc.

---

### `backend/utils/`

**`api.py`** — `AppError` exception class, `success_response()` and `error_response()` helpers for consistent API response envelopes.

---

### `frontend/src/`

**`index.js`** — React entry point. Wraps `App` in `AuthProvider`, `StudentProvider`, `BrowserRouter`.

**`App.js`** — Route definitions. `ProtectedRoute` wrapper checks `AuthContext.isAuthenticated`. Routes: `/login`, `/signup` (public), all others protected.

**`api.js`** — Root-level API client with in-memory student cache. No Authorization headers. Note: calls `/students/students` which requires staff role auth on the backend.

**`chartConfig.js`** — Globally registers Chart.js components (ArcElement, CategoryScale, LinearScale, BarElement, LineElement, PointElement, Legend, Tooltip).

**`context/AuthContext.js`** — **Critical security gap.** Hardcoded credentials `{ username: 'admin', password: 'admin123' }`. No backend interaction. Stores `'ews_auth': 'true'` in sessionStorage on success.

**`context/StudentContext.js`** — Fetches up to 2000 students via `api.js`. Validates risk scores with `validateRiskScore()`. Provides `students`, `loading`, `error`, `totalStudents`, `refreshStudents` via context.

**`services/api.js`** — Service-layer API client. More structured than root `api.js`. Also lacks auth headers.

**`services/studentService.js`**, **`businessService.js`** — Domain-specific API service modules.

**`pages/`**:
- `Dashboard.jsx` — KPI cards, at-risk table, risk distribution chart, recent interventions
- `Students.jsx` — Paginated student table with search, filter, and sort
- `StudentProfile.jsx` — Detailed per-student view with signal radar, trend chart, interventions
- `Analytics.jsx` — KPI cards, doughnut chart, horizontal bar, cohort comparison, intervention effectiveness, radar chart
- `Interventions.jsx` — Intervention management table and creation UI
- `BusinessAnalytics.jsx` — Revenue at risk, retention funnel, ROI timeline
- `BusinessIntelligence.jsx` — Executive-level business metrics
- `Reports.jsx` — Report generation and export
- `FacultyTools.jsx` — Faculty-specific views
- `StudentPortal.jsx` — Student self-service view
- `RiskFactors.jsx` — Risk factor detail view
- `Settings.jsx` — User preferences
- `Login.jsx` — Login form (calls `AuthContext.login`, not the backend)
- `Signup.jsx` — Animated registration form (framer-motion)
- `Insights.jsx`, `InstitutionalInsights.jsx` — Analytics views

**`components/`** — 60+ components organized into:
- `ai/` — AI narrative cards (ExplainableRiskNarrative, WhatIfSimulator, WeeklyProgressBrief, etc.)
- `analytics/` — CohortChurnDiagnostics, CourseRiskAnalysis, DropoutProbabilityFunnel
- `business/` — Revenue/retention charts (RevenueAtRisk, InterventionROITimeline, RetentionFunnel, etc.)
- `common/` — Layout, Header, Sidebar, Logo (MeridianMark SVG), Spinner, Skeleton, TimeFilter, etc.
- `dashboard/` — KpiCard, RiskTable, Charts, HighestRiskStudentsTable, PriorityQueuePanel
- `interventions/` — InterventionCard, InterventionEffectiveness, MicroGoalsSuggester, etc.
- `quality/` — BiasIndicators, DataQualityPanel, SystemPatternDetector
- `student/` — StudentDrawer, SignalBreakdown, SignalRadarChart, RiskBreakdownChart, etc.

**`utils/`**:
- `riskScoreValidator.js` — Validates 0–100 range, defaults invalid to 50
- `riskNarrativeGenerator.js` — Template-based risk explanations (client-side)
- `recommendationEngine.js` — Client-side intervention recommendation logic
- `dataQualityCalculator.js` — Data completeness scoring
- `trendCalculator.js` — Trend computation utilities
- `studentUtils.js` — Student data helper functions
- `motionConfig.js` — Framer Motion variants (container/item stagger)
- `timelineDataGenerator.js` — Synthetic timeline data generation
- `csvParser.js` — Client-side CSV parsing

**`constants/riskThresholds.js`** — Frontend risk threshold constants. Must be kept in sync with backend config thresholds.

**`hooks/`** — `useStudentRisk.js`, `useIntervention.js`, `useDebounce.js`

---

### `backend/data/`

- `sql_app.db` — SQLite database. Created by `init_db()` at startup. May not exist before first run.
- `Engagement_Analysis.xlsx` — Required primary data file. Must be present in this directory.
- `labels.csv` — Sample training labels (historical, used for offline ML training).
- Additional XLSX snapshots (optional, configurable via env vars).

---

## 4. Data Flow — Step by Step

### Phase 1: Startup Ingestion

```
Server Start
    │
    ├── init_db()
    │     Import all 25+ ORM models
    │     Base.metadata.create_all(engine)
    │     → All tables created in sql_app.db if not existing
    │
    └── asyncio.create_task(_run_ingestion())    ← non-blocking
          Thread via asyncio.to_thread():
              SessionLocal() → db session
              ingest_all_data(db)
              │
              ├── _build_file_map()
              │     9 configured file paths from config
              │
              ├── _validate_required_files()
              │     Engagement_Analysis.xlsx must exist
              │     FileNotFoundError → logged, server continues
              │
              ├── _ingest_engagement_data()
              │     openpyxl → reads "Learner Usage main dump" sheet
              │     For each row:
              │       Student: get-or-create by username (PK)
              │       Course:  get-or-create by course_id
              │       Enrollment: get-or-create by (student_id, course_id)
              │         COUNTER_FIELDS accumulated (not replaced)
              │
              ├── _ingest_quiz_assignment_exam()
              │     GradedComponent: quiz scores, assignment grades
              │     ExamRecord: exam marks, attendance (present=True/False)
              │
              ├── _update_enrollments_from_latest()
              │     Week 3/5 snapshots update SCORM fields
              │     and per-enrollment counters
              │
              └── db.commit()    ← single transaction commit
```

### Phase 2: Feature Engineering (per student, per request or per job)

```
Input: List[Dict] enrollments, List[Dict] graded_components, List[Dict] exam_records
    │
    ├── content_completion_score
    │     = (Σ content_completed / Σ content_required) × 100
    │     Clamp [0, 100]
    │
    ├── w1w2_completion_score
    │     = (Σ min(completed, required_w1w2) / Σ required_w1w2) × 100
    │
    ├── quiz_engagement_score
    │     If total_quiz_attempts > 0:
    │       raw = (quiz_completed / total_quiz_attempts) × 100
    │     Boost for high attempt counts, cap at 100
    │
    ├── discussion_engagement_score
    │     Weighted sum of posts_created, replies, reads
    │     Log-scaled to avoid outlier dominance
    │
    ├── assignment_score
    │     = num_assignment_submissions relative to course count × 100
    │
    ├── time_investment_score
    │     = log10(total_seconds + 1) / log10(max_expected) × 100
    │
    ├── login_consistency_score
    │     = f(num_logins, days_since_last_login)
    │     Penalized heavily for no logins or stale login dates
    │
    └── zero_progress_ratio
          = courses_with_zero_content / total_courses
          (used as penalty in risk scorer)
Output: Dict[str, float] — 10+ features, all [0,100] or [0,1]
```

### Phase 3: Risk Scoring

```
Input: features dict (from Phase 2)
    │
    ├── For each of 6 weighted features (if present):
    │     clamped_score = max(0, min(100, feature_value))
    │     weighted_sum += weight × clamped_score
    │     observed_weight += weight
    │
    ├── If observed_weight == 0:
    │     Return NEUTRAL_RISK_SCORE = 50.0
    │
    ├── weighted_engagement = weighted_sum / observed_weight
    │
    ├── base_risk = 100 − weighted_engagement
    │
    ├── coverage = observed_weight / sum(all_weights)
    │     # shrinks toward neutral when few features are present
    │
    ├── risk_score = (base_risk × coverage) + (50.0 × (1 − coverage))
    │
    ├── zero_progress_penalty = min(15.0, zero_progress_ratio × 15.0)
    │     risk_score += zero_progress_penalty
    │
    └── Final: clamp [0, 100], round to 2 decimal places
Output: float [0, 100], higher = more likely to drop out
```

### Phase 4: Daily Scheduler Prediction Persistence (03:00 UTC)

```
generate_daily_predictions()
    │
    └── For each Student in DB:
          features = FeatureEngineer.calculate_all_features(
              enrollment_map[student.id],
              graded_map[student.id],
              exam_map[student.id]
          )
          risk_score = RiskScorer.calculate_risk_score(features)
          # risk_score is [0, 100]
          │
          ├── Prediction(
          │     risk_score = risk_score / 100.0,       ← stored as 0–1
          │     engagement_score = (100 - risk_score) / 100.0,
          │     retention_likelihood = RiskScorer.get_retention_likelihood(risk_score),
          │     model_version = "rule-based-v1"
          │   )
          │
          └── RiskSnapshot(
                risk_score = risk_score / 100.0,       ← stored as 0–1
                engagement_score = (100 - risk_score) / 100.0,
                timestamp = now_utc
              )
```

### Phase 5: API Response Generation

```
GET /api/v1/students/students
    │
    ├── StudentService.get_all_students(db, skip, limit, sort_by, order, risk_min, risk_max)
    │
    │   For each student:
    │     enrollments = load from DB (JOIN with courses)
    │     graded_components = load from DB
    │     exam_records = load from DB
    │     features = FeatureEngineer.calculate_all_features(...)    ← computed live
    │     live_risk = RiskScorer.calculate_risk_score(features)     ← [0, 100]
    │     latest_pred = latest Prediction row for student
    │     stored_risk = latest_pred.risk_score × 100               ← [0, 100] after conversion
    │     final_risk = live_risk (primary) or stored_risk (fallback)
    │
    └── Return: { students: [...], total: N, page: N, page_size: N }
```

### Phase 6: Frontend Rendering

```
React App Mount
    │
    └── StudentContext.loadStudents()
          api.js.getStudents(2000)
          fetch('GET /api/v1/students/students?limit=2000&sort_by=risk_score&order=desc')
              ← No Authorization header
              ← Backend requires Bearer JWT → HTTP 401 Unauthorized
          [If backend auth is not enforced or bypassed:]
              data.students → map to add name/email/program display fields
              validateRiskScore() → clamp to [0,100], default null to 50
              setStudents(validated)
              → Dashboard, Students, Analytics pages render
```

---

## 5. API Documentation

**Base URL:** `http://localhost:8000/api/v1`  
**Authentication:** `Authorization: Bearer <jwt_token>` (except public endpoints)  
**Content-Type:** `application/json` required for all POST/PUT/PATCH requests

### 5.1 System (No Auth)

| Method | Path | Response |
|---|---|---|
| GET | `/` | `{ docs_url, redoc_url }` |
| GET | `/health` | `{ status: "healthy", timestamp }` |

### 5.2 Auth

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/auth/login` | Public | Form body: `username`, `password`. Returns `{ access_token, token_type }` |
| POST | `/auth/register` | Public | JSON body: `username`, `email`, `password`. Role forced to `student` |
| GET | `/auth/me` | JWT | Returns own `UserOut` |
| PUT | `/auth/me` | JWT | Update `username`, `email`, `password` only |
| PATCH | `/auth/users/{id}` | Admin | Update `role`, `is_active`, `is_superuser` |

**Login request:**
```
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=myuser&password=mypassword
```

**Login response:**
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### 5.3 Students (Staff Role Required)

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/students/overview` | JWT | KPI stats; no role restriction |
| GET | `/students/courses` | JWT | Course catalog; no role restriction |
| GET | `/students/students` | Staff | Paginated list. Params: skip, limit(1-2000), sort_by, order(asc/desc), risk_min, risk_max |
| GET | `/students/students/{id}` | Staff | Full student profile |
| GET | `/students/students/{id}/interventions` | Staff | Intervention history |
| GET | `/students/students/{id}/weekly-summary` | Staff | Portal-style summary |
| GET | `/students/students/{id}/risk-trend` | Staff | Params: limit(2-52 weeks) |
| GET | `/students/at-risk` | Staff | Params: threshold(0-100), limit(1-500) |
| GET | `/students/risk-distribution` | Staff | Percentile and bucket stats |
| GET | `/students/analytics/trends` | Staff | Department/course analytics |
| GET | `/students/analytics/risk-trends` | Staff | Params: weeks(1-52) |
| GET | `/students/analytics/engagement-trends` | Staff | Params: weeks(1-52) |
| GET | `/students/analytics/performance-trends` | Staff | Params: weeks(1-52) |
| GET | `/students/analytics/intervention-effectiveness` | Staff | Params: weeks(1-104) |

**Student object schema:**
```json
{
  "id": "user@institution.edu",
  "first_name": "Jane",
  "last_name": "Doe",
  "department": "BS - Data Science & AI",
  "old_new_student": "new",
  "risk_score": 67.4,
  "risk_level": "medium",
  "engagement_score": 32.6,
  "content_completion_score": 45.0,
  "quiz_engagement_score": 30.0,
  "assignment_score": 55.0,
  "login_consistency_score": 20.0,
  "time_investment_score": 35.0,
  "discussion_engagement_score": 10.0,
  "zero_progress_ratio": 0.2,
  "dominant_risk_factor": "Login Consistency",
  "exam_attendance_rate": 75.0,
  "enrollments": [{ "course_id": "...", "course_name": "..." }]
}
```

### 5.4 Predictions

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/predictions/batch` | JWT | Params: include_decisions, limit(1-2000) |
| GET | `/predictions/{student_id}` | JWT | Params: include_decisions(default true) |

### 5.5 ML

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/ml/predict/{student_id}` | Staff | Compute + persist prediction |
| POST | `/ml/predict-batch` | Staff | Body: `{ student_ids: [...] }` |
| GET | `/ml/model-info` | Staff | Model metadata |
| GET | `/ml/history/{student_id}` | Staff | Historical predictions |

### 5.6 Interventions

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/interventions` | JWT | Params: skip, limit, status filter |
| POST | `/interventions` | JWT | Body: InterventionCreateRequest. Supports `student_ids` array for bulk |
| GET | `/interventions/{id}` | JWT | Single intervention |
| PATCH | `/interventions/{id}` | JWT | Update status, faculty, effectiveness |
| DELETE | `/interventions/{id}` | JWT | Hard delete |

**InterventionCreateRequest:**
```json
{
  "student_id": "user@email.com",
  "date": "2025-04-06",
  "user": "advisor@institution.edu",
  "action": "Email sent re: attendance",
  "status": "Pending",
  "assigned_faculty": "Dr. Smith",
  "risk_score_at_trigger": 72.5,
  "threshold_category": "urgent",
  "channels": ["email", "whatsapp"],
  "assigned_team": "faculty"
}
```

### 5.7 LLM

All endpoints require JWT. Return mock data when LLM API keys absent.

| Method | Path | Body |
|---|---|---|
| POST | `/llm/explain-risk-change` | `{ student_id, time_period }` |
| POST | `/llm/student-advice` | `{ student_id, question }` |
| POST | `/llm/faculty-summary` | `{ student_id, for_role }` |
| POST | `/llm/intervention-recommendation` | `{ student_id }` |
| POST | `/llm/what-if` | `{ student_id, scenario }` |
| POST | `/llm/report-narrative` | `{ report_type, data }` |

### 5.8 Business Intelligence

| Method | Path | Auth |
|---|---|---|
| GET | `/business/retention-metrics` | JWT |
| GET | `/business/revenue-at-risk` | JWT |
| GET | `/business/intervention-roi` | JWT |
| GET | `/business/retention-funnel` | JWT |
| GET | `/business/cohort-analysis` | JWT |

### 5.9 Other Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/analytics/summary` | JWT | Aggregated summary |
| GET | `/analytics/risk-distribution` | JWT | Distribution breakdown |
| GET,POST,PUT | `/goals/{student_id}` | JWT | Goal lifecycle |
| GET | `/reports/student/{id}` | Staff | Student report |
| GET | `/reports/cohort` | Staff | Cohort report |
| GET | `/monitoring/health` | JWT | Detailed health |
| GET | `/advisor/...` | JWT | AI advisor endpoints |
| GET | `/integration/...` | JWT + API key | External system integration |

---

## 6. Authentication and Security Model

### 6.1 Backend JWT Auth (How It Works)

1. Client POSTs `username` + `password` form data to `POST /api/v1/auth/login`.
2. Server verifies password against bcrypt hash in `users` table.
3. Server issues JWT with `{ sub: user_id, role: user_role, exp: now + 60min }`.
4. Client includes `Authorization: Bearer <token>` in all subsequent requests.
5. `deps.get_current_user()` decodes JWT with `SECRET_KEY`, fetches User row, validates `is_active`.
6. `deps.require_role(["admin", "faculty"])` checks `user.role` against the allowed set.
7. `is_superuser=True` users bypass role checks entirely.

**Roles and access:**

| Role | Student data | Interventions | Reports | User management |
|---|---|---|---|---|
| student | Own data only | None | None | Own profile |
| faculty | All students | Read/write | Read | None |
| retention team | All students | Read/write | Read | None |
| admin | All | All | All | Full |
| superuser | All | All | All | Full |

### 6.2 Frontend Auth (What Actually Happens)

`AuthContext.js` contains:
```javascript
const CREDENTIALS = { username: 'admin', password: 'admin123' };
```

When the user submits the login form:
1. The frontend checks if username === 'admin' and password === 'admin123'.
2. If true, writes `sessionStorage.setItem('ews_auth', 'true')`.
3. No HTTP call is made to the backend.
4. No JWT is obtained.
5. All subsequent `fetch()` calls in `api.js` and `services/api.js` have no Authorization header.
6. The backend's `get_current_user` dependency will respond with HTTP 401.

**Consequence:** In a correctly running environment, the entire frontend will fail to load any data. The frontend will render loading spinners or error states for all student/analytics data.

### 6.3 Security Vulnerabilities Summary

See `SECURITY.md` for full details. Brief summary:

| Severity | ID | Issue |
|---|---|---|
| Critical | AUTH-01 | Frontend auth disconnected from backend; no JWT in API calls |
| Critical | AUTH-02 | Hardcoded credentials in frontend source bundle |
| High | RATE-01 | In-memory rate limiter, non-distributed |
| High | SECRET-01 | Default SECRET_KEY in source (blocked in prod but exposed in dev) |
| High | CACHE-01 | Student PII potentially in Redis without encryption |
| Medium | REG-01 | Open registration with no email verification |
| Medium | SESSION-01 | sessionStorage flag trivially forgeable |
| Medium | OWNER-01 | No per-student ownership checks on intervention endpoints |

---

## 7. ML System Explanation

### 7.1 The Three Pipelines (All Coexist, Only One Is Active)

**Pipeline 1 — Active Runtime (services/risk_scoring.py)**

Used by: `StudentService`, `SchedulerService`, `ml_service.py` (fallback).

```
Enrollments + GradedComponents + ExamRecords
         ↓
FeatureEngineer.calculate_all_features()
         ↓
6 engagement features [0–100]
         ↓
RiskScorer.calculate_risk_score()
  Weights: content(30%), login(20%), quiz(15%), assignment(15%), time(10%), discussion(10%)
         ↓
risk_score ∈ [0, 100]
```

**Pipeline 2 — Saved Models (ml/models/saved/) — INACTIVE**

Expected input: `[absrate7, q4mpa7, nsusp7, mobility7]`.  
These features do not exist in the live database.  
The inference code (`predictor.py`) was deleted.  
Result: models cannot be invoked. They are dead artifacts.

**Pipeline 3 — Explainability Layer (ml/inference/risk_formula.py)**

Used by: Frontend WhatIfSimulator and ExplainableRiskNarrative components (via API endpoints).  
Input: 5 manually-provided signal scores [0–1].  
Output: 0–1 score + human-readable breakdown.  
Not connected to the runtime prediction pipeline.

### 7.2 Risk Score Interpretation

```
0–39  → Low Risk     — Monitoring only; no urgent action
40–69 → Medium Risk  — Proactive outreach recommended
70–100 → High Risk   — Urgent intervention required
```

Config thresholds: `RISK_THRESHOLD_HIGH=70`, `RISK_THRESHOLD_MEDIUM=40`.

The `features/risk_scorer.py` (secondary pipeline) uses different thresholds: Critical ≥75, High ≥50, Medium ≥25.

### 7.3 Feature Weight Rationale

| Feature | Weight | Why |
|---|---|---|
| Content completion | 30% | Strongest predictor — students who don't engage with material drop out |
| Login consistency | 20% | Absence from the platform precedes withdrawal |
| Quiz engagement | 15% | Formative assessment participation correlates with retention |
| Assignment score | 15% | Summative task completion indicates commitment |
| Time investment | 10% | Supporting signal; high outliers can mislead |
| Discussion | 10% | Social engagement; weaker predictor but valuable |

### 7.4 Missing Data Handling

Missing feature scores are excluded from the weighted average rather than defaulting to 0 (worst) or 100 (best). Coverage is tracked. When fewer than 100% of features are available, the score is shrunk toward 50 (neutral), expressing uncertainty. This prevents students with sparse data from being falsely scored as extremely high or low risk.

### 7.5 Known ML Limitations

- Rule-based scoring is not validated against actual retention outcomes. Its predictive accuracy is unknown.
- Training label data (`labels.csv`) exists but is disconnected from the scoring pipeline.
- The weekly retraining job is a stub and has never executed.
- No model performance monitoring, calibration, or drift detection is implemented.
- The explainability formula (risk_formula.py) has a weight mapping bug where consistency/intent/responsiveness signals receive 0.0 weight due to key mismatches between config and the module's mapping.

---

## 8. Setup Instructions

### 8.1 Prerequisites

- Python 3.11 or higher (tested on 3.13)
- Node.js 18+ and npm 9+
- `backend/data/Engagement_Analysis.xlsx` must exist (LMS data export)

### 8.2 Backend Setup

```bash
# 1. Navigate to the repo
cd /path/to/ews-retention-platform

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure environment (optional but recommended)
cp .env.example .env
# Edit .env:
#   SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
#   GEMINI_API_KEY=<your key if you want AI features>

# 5. Ensure the data file is in place
ls backend/data/Engagement_Analysis.xlsx

# 6. Start the server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# OR:
python -m backend.main
```

On startup, watch the logs:
```
INFO  Database initialised.
INFO  Starting data ingestion from XLSX files...
INFO  Data ingestion complete.
INFO  [SCHEDULER] Started. Daily job: 03:00 UTC. Weekly job: Sunday 04:00 UTC.
```

If ingestion fails, the server still starts but `total_students` will be 0.

### 8.3 Frontend Setup

```bash
cd frontend
npm install
npm start
# Dev server starts at http://localhost:3000
```

### 8.4 Creating an Admin User

There is no seed script. Use curl or the Swagger UI at `http://localhost:8000/docs`:

```bash
# Step 1: Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "email": "admin@example.com", "password": "SecurePass123!"}'

# Step 2: Login to get a token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d 'username=admin&password=SecurePass123!' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])")

# Step 3: Promote to admin
curl -X PATCH http://localhost:8000/api/v1/auth/users/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin", "is_superuser": true}'
```

### 8.5 Environment Variables Reference

| Variable | Default | Required | Description |
|---|---|---|---|
| `SECRET_KEY` | (insecure default) | **Yes in prod** | JWT signing key |
| `ENVIRONMENT` | `development` | No | Set to `production` to enforce SECRET_KEY |
| `DATABASE_URL` | `sqlite:///backend/data/sql_app.db` | No | SQLAlchemy URL |
| `API_HOST` | `0.0.0.0` | No | Bind address |
| `API_PORT` | `8000` | No | Port |
| `CORS_ORIGINS` | `http://localhost:3000,...` | No | Comma-separated origins |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | No | JWT TTL |
| `LLM_PROVIDER` | `gemini` | No | `gemini` or `claude` |
| `GEMINI_API_KEY` | (empty) | No | Enables Gemini LLM features |
| `GEMINI_MODEL` | `gemini-1.5-pro` | No | Gemini model name |
| `CLAUDE_API_KEY` | (empty) | No | Enables Claude LLM features |
| `REDIS_URL` | `redis://localhost:6379/0` | No | Cache (degrades gracefully) |
| `CACHE_EXPIRE_SECONDS` | `300` | No | Redis TTL |
| `RISK_THRESHOLD_HIGH` | `70.0` | No | High risk cutoff (0-100) |
| `RISK_THRESHOLD_MEDIUM` | `40.0` | No | Medium risk cutoff |
| `AVERAGE_STUDENT_LTV` | `150000.0` | No | For revenue calculations |
| `TUITION_PER_SEMESTER` | `75000.0` | No | For revenue calculations |
| `ENGAGEMENT_DATA_FILE` | `Engagement_Analysis.xlsx` | No | Primary data filename |
| `REACT_APP_API_URL` | `http://localhost:8000/api/v1` | No | Frontend API base URL |

### 8.6 Verifying the Installation

```bash
# Backend health
curl http://localhost:8000/health
# → {"success": true, "data": {"status": "healthy"}}

# Student count (after ingestion)
curl http://localhost:8000/api/v1/students/overview \
  -H "Authorization: Bearer <your_token>"
# → {"data": {"total_students": 120, ...}}
```

---

## 9. Known Issues and Risks

### Critical (Production Blockers)

**AUTH-01: Frontend authentication is completely disconnected from the backend.**  
`AuthContext.js` uses hardcoded credentials (`admin/admin123`) and never obtains a JWT. All API calls in `api.js` and `services/api.js` have no Authorization header. The backend's protected endpoints will return HTTP 401 for every request from the frontend. The entire data layer of the UI is non-functional in a correctly deployed environment.  
**Fix required:** Rewrite `AuthContext.js` to call `/api/v1/auth/login`, store the JWT, and inject it as a Bearer token in all fetch calls.

**AUTH-02: Hardcoded credentials are visible in the frontend source bundle.**  
`admin/admin123` is a string literal in `AuthContext.js` and will appear in the compiled JavaScript bundle. Any user who downloads the app source can extract it.  
**Fix required:** Remove the hardcoded credentials. Login must always go through the backend API.

**ML-01: The saved XGBoost and Logistic Regression models have no runtime integration.**  
`backend/ml/models/saved/` contains joblib model files trained on 4 features (`absrate7`, `q4mpa7`, `nsusp7`, `mobility7`) that do not exist in the live database. The inference code was deleted. `ml_service.py` logs a schema mismatch warning and falls back to the rule-based scorer. The models are dead artifacts.

### High Severity

**SCORE-01: Dual representation of risk scores (0-1 in DB, 0-100 in API) is fragile.**  
The scheduler stores `risk_score / 100.0`. The service layer re-multiplies by 100. Multiple defensive normalizations are scattered across `students_controller.py`, `student_service.py`, and `ml_service.py`. Any code that writes a prediction without dividing by 100, or reads without multiplying, silently produces incorrect risk scores.

**RISK-01: Three incompatible risk scoring implementations coexist.**  
`services/risk_scoring.py` (6 features, primary), `features/risk_scorer.py` (2 DB signals, secondary), and `ml/inference/risk_formula.py` (5 signals, explainability) all use different weights, thresholds, and feature schemas. The secondary pipeline is wired but not called. Documentation states three pipelines were "mutually incompatible."

**RATE-01: Rate limiter is in-memory and per-process.**  
`rate_limit_store` in `security_logging.py` is a plain Python dict. It resets on every restart. It provides no protection under multiple uvicorn workers or in a container cluster. A Redis-backed limiter (e.g., `slowapi`) is required for production.

**WEIGHT-01: Signal weight mapping bug in risk_formula.py.**  
`SIGNAL_WEIGHTS` in config contains keys `attendance`, `grades`, `engagement`, `submissions`. `risk_formula.py` maps 5 signal names to weight keys `academic`, `engagement`, `consistency`, `intent`, `responsiveness`. The `consistency`, `intent`, and `responsiveness` signals always receive weight 0.0 because their keys don't exist in `SIGNAL_WEIGHTS`. The explainability formula silently ignores 3 of 5 signals.

### Medium Severity

**DUP-01: Two parallel ingestion pipelines.**  
`backend/ingestion/` (12 files, sophisticated validation and quarantine) is dead code. `backend/services/core/data_ingestion.py` is the active pipeline with less validation. The better pipeline is not used.

**FEAT-01: Secondary feature engineering pipeline (backend/features/) is not integrated.**  
The academic and engagement signal classes have full DB query implementations but are not called in the main scoring flow.

**SCHED-01: Standalone feature store job not integrated with scheduler.**  
`backend/jobs/feature_store_job.py` must be run as a separate process.

**DATE-01: Enrollment date fields stored as strings.**  
`last_visited_date`, `last_system_login`, etc. are `Column(String)` instead of `Column(DateTime)`. Sorting and arithmetic on these require parsing.

**TEST-01: No automated tests.**  
No unit, integration, or API tests exist in the repository.

### Low Severity

**CACHE-01: Redis caching has no effect when Redis is absent.**  
`cache_response` decorator silently degrades to a no-op. All responses are computed fresh.

**LLM-01: LLM endpoints return mock data when keys are absent.**  
Mock responses are structurally correct but may mislead users who don't realize AI analysis is not being performed.

**RETRAIN-01: Weekly retraining job is a no-op.**  
`retrain_model_weekly()` logs "No labelled training data available" and exits. The system cannot improve its predictions over time.

---

## 10. Improvement Roadmap

### Tier 1 — Must Fix Before Real Deployment

1. **Rewrite frontend authentication** to use the backend JWT system. Call `/api/v1/auth/login`, store token in memory (not localStorage), include `Authorization: Bearer` in all `fetch()` calls. Update both `api.js` and `services/api.js`.

2. **Remove hardcoded credentials** from `AuthContext.js`. Delete the `CREDENTIALS` constant entirely.

3. **Consolidate to one risk scoring system.** Choose `services/risk_scoring.py` as canonical. Delete `features/risk_scorer.py` or clearly mark it as experimental/unused. Fix the weight mapping bug in `ml/inference/risk_formula.py`.

4. **Standardize risk score storage.** Pick one representation (recommend 0-100 throughout, including DB storage). Remove all scattered normalization code. Add a DB migration.

### Tier 2 — High Priority

5. **Replace in-memory rate limiter with Redis-based.** Use `slowapi` or implement a custom Redis counter. Required for multi-worker deployment.

6. **Bridge the ML model feature gap.** Either retrain XGBoost/LogReg on the 6 engagement features available in the live DB, or replace with a simple sklearn model trained on `labels.csv` augmented with the engagement features. The rule-based scorer provides a baseline to validate against.

7. **Consolidate ingestion pipelines.** The `backend/ingestion/` pipeline has better validation. Migrate `services/core/data_ingestion.py` to use it and delete the orphaned simpler version.

8. **Write a test suite.** Start with unit tests for `FeatureEngineer` and `RiskScorer` (pure functions, no DB needed). Add integration tests for the ETL pipeline and critical API routes.

### Tier 3 — Quality Improvements

9. **Fix date field types in Enrollment model.** Change string date columns to `DateTime`. Write a SQLAlchemy migration.

10. **Integrate `FeatureStoreService` into the main scheduler.** Pre-compute feature vectors daily so `StudentService` can serve them without recomputing on each request.

11. **Implement training label collection.** Add an advisor workflow to record actual outcomes (retained, transferred, withdrew). Feed these into a retraining pipeline.

12. **Add per-student data isolation.** Faculty should only see students enrolled in their courses.

### Tier 4 — Future Enhancements

13. **Replace SQLite with PostgreSQL** for concurrent write performance and production-grade reliability.
14. **Add HTTPS and HSTS** enforcement for production.
15. **Add email verification** for the registration endpoint.
16. **Add real-time alerts** via WebSocket or SSE when a student's risk exceeds a threshold.
17. **Add observability** — Prometheus metrics, structured JSON logging, distributed tracing.
18. **Add model performance monitoring** — track actual vs predicted outcomes, trigger retraining on drift.
