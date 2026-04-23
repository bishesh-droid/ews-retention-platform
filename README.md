# Meridian EWS Retention Platform

A full-stack Early Warning System (EWS) for student retention. The platform ingests engagement and academic data, computes risk scores using a rule-based weighted scoring engine with an optional ML ensemble, surfaces intervention recommendations to faculty and advisors, and exposes AI-generated narrative insights via LLM integration. It is designed for deployment at a single institution but structured to support multi-tenancy extension.

# Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Data Flow Explanation](#data-flow-explanation)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Deployment](#deployment)
- [Logging and Monitoring](#logging-and-monitoring)
- [Security Considerations](#security-considerations)
- [Performance Considerations](#performance-considerations)
- [Limitations](#limitations)
- [Roadmap / Future Improvements](#roadmap--future-improvements)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

# Overview

## Problem

Educational institutions lack automated tooling to identify students at risk of dropping out before the risk becomes irreversible. Faculty and retention teams typically act on intuition or lagging indicators such as exam results. The window for effective intervention is narrow and requires timely, evidence-based signals.

## Who It Is For

- Retention coordinators and advisors at higher education institutions
- Faculty managing at-risk students within a department
- Institutional administrators who need aggregate risk visibility
- Students (read-only, self-service view of their own risk status and goals)
- DevOps and data engineers responsible for deployment and data ingestion

## Core Capabilities

- Ingests structured engagement and academic data from Excel exports of a Learning Management System (LMS)
- Computes per-student risk scores on a 0-100 scale using a weighted rule-based engine across seven feature signals
- Optionally blends rule-based scores with an XGBoost/ensemble ML model at a configurable weight (default 30% ML, 70% rule-based)
- Applies calendar-aware adjustments based on week of semester
- Generates intervention recommendations with priority routing, cooldown logic, and outcome tracking
- Surfaces AI-generated explanations and narrative advice via Google Gemini or Anthropic Claude APIs
- Provides a React-based faculty dashboard with paginated student lists, risk trend charts, cohort comparisons, and intervention logging
- Enforces FERPA-compliant audit logging for all PII access
- Runs background jobs for scheduled re-scoring, weekly snapshots, and batch notifications via APScheduler

## System Boundaries

The system does not integrate directly with any LMS via API. It consumes manually exported Excel files placed into a watched directory. It does not send emails directly to students. LLM calls are outbound only; no student PII is transmitted to external LLM providers in unstructured form. There is no single sign-on (SSO) integration; authentication is local JWT-based.

# Architecture

## High-Level System Architecture

The platform is organized as three independent deployable units: a Python FastAPI backend, a React single-page application frontend served by Nginx, and an optional Redis instance for rate limiting and token revocation. All three can be orchestrated locally via Docker Compose or deployed independently to a cloud environment.

```
Browser (React SPA)
       |
       | HTTPS / HTTP (port 3000 → proxied to 8000 in development)
       v
FastAPI Backend (port 8000)
       |
       |-- SQLite (development) or PostgreSQL (production)
       |-- Redis (rate limiting, token blacklist, cache)
       |-- APScheduler (async background jobs in-process)
       |-- Outbound: Google Gemini API or Anthropic Claude API
```

## Backend Architecture

The backend is a FastAPI application with an async-first design. The application lifecycle is managed via a `lifespan` context manager that initializes the database, verifies Redis connectivity, and starts the scheduler on startup.

Routing is organized into 17 router modules under `backend/routes/`, each mounted with a versioned prefix. Dependency injection via FastAPI's `Depends` pattern is used for database sessions, authenticated user resolution, and rate limit enforcement.

The risk pipeline is a three-stage chain:

1. Feature engineering (`backend/services/feature_engineering.py`) extracts 50+ signals from enrollment and event records into five domain groups: academic, engagement, consistency, intent, and responsiveness.
2. Rule-based scoring (`backend/services/risk_scoring.py`) applies configurable weights to the domain scores and produces a 0-100 risk value.
3. Optional ML blending (`backend/services/ml_service.py`) loads a persisted XGBoost model and blends its prediction with the rule-based score at a configurable ratio.

A calendar scorer (`backend/services/calendar_scorer.py`) applies a time-aware adjustment based on the current week in the semester, with a default 40% blend weight.

## Frontend Architecture

The frontend is a Create React App (CRA) single-page application. State is managed through three React Context providers: `AuthContext` (token lifecycle), `StudentContext` (selected student and risk cache), and `ThemeContext` (dark/light mode). All API calls are made through a centralized Axios wrapper in `frontend/src/services/api.js` that standardizes the response shape and handles global error toasts.

Routing uses React Router v6 with a `ProtectedRoute` wrapper that redirects unauthenticated users to `/login`. The application is served in production from a multi-stage Docker build with Nginx as the static file server and reverse proxy.

## Data Layer

Development uses SQLite stored at `backend/data/sql_app.db`. The schema is defined using SQLAlchemy ORM models under `backend/database/models/` and versioned through 17 Alembic migrations. The schema contains 32 tables spanning student core data, enrollment and engagement metrics, predictions, interventions, LLM query logs, FERPA audit records, and a denormalized star schema for analytical queries.

## Integration Points

- **Outbound LLM API:** The backend calls either the Google Gemini API or the Anthropic Claude API (configurable via `LLM_PROVIDER` environment variable) for student advice, faculty summaries, and what-if simulations. Calls use structured prompt templates; no raw student PII is interpolated as free text.
- **Inbound data:** Excel files are dropped into `backend/data/raw/` and ingested via the validated pipeline, either on demand via the admin API or by triggering the CLI script.
- **Redis:** Used for rate limiting (via SlowAPI), token revocation blacklisting, and optional response caching. Degrades gracefully to in-memory TTLCache if Redis is unavailable.

## Design Patterns

- **Dependency injection:** FastAPI `Depends` for session, auth, and rate limiting
- **Repository pattern:** `StudentRepository` and service-layer classes abstract database access
- **Feature extractor modularity:** Four domain-specific extractor classes (`AcademicFeatureExtractor`, `EngagementFeatureExtractor`, `ConsistencyFeatureExtractor`, `IntentFeatureExtractor`) compose into the main feature engineering pipeline via a backward-compatible public interface
- **Strategy pattern:** `LLM_PROVIDER` setting selects between Gemini and Claude clients at runtime
- **Append-only audit log:** All PII access events are written to `audit_logs`; records are never deleted or updated
- **Refresh Token Rotation (RTR):** Each token refresh invalidates the previous token's JTI; reuse of a superseded token triggers family-wide revocation

# Project Structure

## Root Directory

- `README.md` — Project documentation
- `.env.example` — Template listing all supported environment variables with explanations
- `requirements.txt` — Pinned Python runtime dependencies (68 packages)
- `requirements-dev.txt` — Additional development and test dependencies (pytest, black, mypy, ruff, flake8)
- `setup.sh` — Bash script that creates a virtual environment and installs both requirement files
- `pytest.ini` — Pytest configuration: test discovery paths, markers, coverage settings
- `mypy.ini` — MyPy strict type checking configuration
- `.flake8` — Flake8 linting rules and per-file ignores
- `.python-version` — Python version pin for pyenv
- `docker-compose.yml` — Orchestrates backend, frontend, and Redis containers
- `.dockerignore` — Excludes node_modules, venv, `.env`, and model artifacts from Docker build context
- `test_endpoints.py` — Manual integration test script for quick endpoint smoke testing outside of pytest
- `test_students.json` — JSON fixture with synthetic student records used in tests
- `sql_app.db` — SQLite development database (should not be committed in production environments)
- `SECURITY.md` — Security policy, vulnerability reporting process, FERPA compliance posture
- `SECURITY_AND_COMPLIANCE.md` — Detailed security architecture document
- `CODE_OF_CONDUCT.md` — Contributor conduct guidelines
- `TEST_COVERAGE_IMPROVEMENTS.md` — Notes on test coverage gaps and strategy

## /backend

### backend/main.py

FastAPI application factory. Defines the `lifespan` context manager for startup/shutdown, mounts all route routers, registers middleware (CORS, security headers, security logging, request ID injection, request validation), and sets up global HTTP exception and validation error handlers. Health check on startup verifies database connectivity and Redis reachability.

### backend/config/\_\_init\_\_.py

Single source of truth for all runtime configuration. Reads environment variables and provides typed, validated settings objects consumed across the application. Key sections: database URL construction, JWT parameters, CORS origin parsing, risk threshold values, feature weight mapping, LLM provider and model selection, Redis and cache settings, rate limit parameters, business metric constants (student LTV, tuition, intervention cost), and logging level.

### backend/database/

- `connection.py` — SQLAlchemy engine, `SessionLocal` factory, `get_db` dependency, and `init_db` which calls `Base.metadata.create_all`
- `models/` — One file per model group. All models inherit from `Base = declarative_base()`
- `queries.py` — Reusable ORM query functions for complex joins and aggregations used by multiple routes

### backend/routes/

Each module is a FastAPI `APIRouter` instance. Active routers:

- `auth.py` — Login, registration, token refresh, logout, token revocation
- `student_v1.py` — Student self-service: own profile, goals, risk history
- `admin_v1.py` — Admin operations: user management, audit log access, ingestion run history, course registry, intervention effectiveness report, bulk data export
- `admin_ingest.py` — Async file upload endpoint for data ingestion; returns a task ID for polling job status
- `retention_v1.py` — Retention team views: at-risk student list, risk summary aggregates
- `analytics.py` — KPI calculations, drill-down queries, top risk velocity ranking
- `integration.py` — External integration: signed requests returning student and cohort risk profiles
- `students.py` — Paginated and filtered student list, individual student detail
- `ml_routes.py` — Model metadata, current model status, on-demand batch prediction trigger
- `llm.py` — LLM-backed endpoints: risk change explanation, student advice, faculty summary, what-if simulation, pattern discovery, institutional insights
- `features.py` — Per-student feature extraction results and signal summaries
- `goals.py` — Goal CRUD for student-scoped goal tracking
- `reports.py` — PDF and CSV report generation and download
- `decisions.py` — Intervention decision routing logic
- `recommendations.py` — Personalized intervention recommendations
- `advisor.py` — AI academic advisor conversational interactions
- `audit.py` — Audit log query interface for compliance review
- `monitoring.py` — `/health`, `/ready`, and Prometheus-compatible metrics endpoints

Disabled/placeholder routes (marked for removal):
- `predictions.py` — Legacy route, not called by current frontend
- `events.py` — Stub, no frontend consumers
- `feedback.py` — Partial implementation, not production-ready

### backend/core/

- `auth.py` — JWT token creation, decoding, and expiry validation; bcrypt password hashing
- `security.py` — OAuth2PasswordBearer scheme; `get_current_user` and role-based dependency functions
- `signing.py` — HMAC-SHA256 request signing for the integration API
- `logger.py` — Structured logging setup with PII masking for student IDs and email addresses
- `errors.py` — Custom exception classes and global error handler factories
- `rate_limiting.py` — SlowAPI integration with Redis backend; TTLCache fallback when Redis is unavailable
- `constants.py` — Role enums, risk level labels, system-wide constants
- `redis_cache.py` — Redis connection helper and generic cache get/set/invalidate utilities
- `audit_logger.py` — Writes append-only records to `audit_logs` for every access to PII-tagged resources

### backend/services/

- `feature_engineering.py` (37KB) — Coordinates the four domain feature extractors. Public interface: `extract_features(student_id, db)` returns an `EngineeredFeatures` record. Internally delegates to `AcademicFeatureExtractor`, `EngagementFeatureExtractor`, `ConsistencyFeatureExtractor`, and `IntentFeatureExtractor`.
- `risk_scoring.py` (16KB) — Accepts engineered feature values and applies configurable weights across seven signals. Produces a normalized 0-100 score. Self-directed learning signal is inverted (higher score = lower risk).
- `ml_service.py` (21KB) — Loads an optional XGBoost model from `models/saved_models/`. If the model is present, blends its output with the rule-based score at the configured ratio. Falls back to rule-based-only if the model file is absent or fails to load.
- `calendar_scorer.py` (10KB) — Computes the current semester week from a configurable start date. Applies a time-weighted adjustment to the base risk score; default blend weight is 40%.
- `notification_service.py` (17KB) — Routes intervention notifications to faculty based on intervention type and faculty notification preferences. Implements a 7-day cooldown with override logic for risk spikes exceeding a 15-point threshold.
- `analytics_service.py` — KPI aggregations: total students, at-risk count, critical count, average attendance, cohort comparisons.
- `export_service.py` — Generates PDF risk summaries and CSV data exports using ReportLab and Pandas.
- `audit_service.py` — Query layer for audit log retrieval with filtering and pagination.
- `goals_service.py` — Goal creation, update, and progress tracking.
- `student_repository.py` — Data access layer for student queries, abstracting raw ORM operations.
- `scheduler.py` — APScheduler instance with async jobs: daily prediction run (3:00 AM UTC), weekly risk snapshot aggregation (Saturday), hourly token cleanup, and intervention outcome evaluation.
- `token_cleanup.py` — Removes expired entries from the `revoked_tokens` table.
- `ai/llm_orchestrator.py` — Manages prompt templates and dispatches LLM calls to either the Gemini or Claude client. Includes hallucination guards that validate structured fields in LLM responses before returning them to callers.

### backend/ingestion/

- `validated_pipeline.py` — Production ingestion pipeline. Reads Excel files from `backend/data/raw/`, validates schema, coerces types, normalizes values, validates referential integrity, quarantines invalid rows to `backend/data/quarantine/`, and persists valid records transactionally.
- `schema_manager.py` — Defines expected column names and types for each supported input file format.
- `transformers.py` — Type coercion functions: date parsing, numeric normalization, string cleaning.
- `validators.py` — Field-level validation rules (required, range, enum membership).
- `row_validators.py` — Cross-field validation (e.g., assignment score cannot exceed max points).
- `file_validator.py` — Pre-load checks: file extension, sheet presence, header row validation.
- `error_logger.py` — Writes per-row validation errors to a structured log and the `IngestionRun` record.
- `defaults.py` — Default fill values applied to optional fields when data is absent.
- `pipeline.py` — Deprecated CLI-only orchestrator retained for backward compatibility.

### backend/middleware/

- `security_headers.py` — Injects `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, and `Strict-Transport-Security` headers on every response.
- `security_logging.py` — Logs authentication events, authorization failures, and suspicious request patterns.
- `request_id.py` — Generates a UUID per request and attaches it as `X-Request-ID` in both request context and response headers for distributed tracing.
- `request_validation.py` — Rejects requests with bodies exceeding the configured size limit and enforces `Content-Type` constraints on write endpoints.

### backend/tests/

30 test modules covering:

- Authentication flows: `test_auth.py`
- Critical path integration: `test_critical_paths.py`
- Integration API: `test_integration_api.py`
- Risk calculation accuracy: `test_risk_scoring.py`, `test_risk_validation.py`
- IDOR prevention: `test_idor.py`, `test_recommendations_idor.py`, `test_student_ownership.py`
- LLM integration and hallucination guards: `test_llm_services.py`, `test_hallucination_guard_consolidated.py`
- Prompt injection safety: `test_prompt_injection.py`
- Security headers: `test_security_headers.py`
- Background scheduler: `test_scheduler.py`
- Student list pagination and filtering: `test_student_list.py`
- Cohort analytics: `test_cohort_risk_profiles.py`
- Faculty department scoping: `test_department_assignment.py`
- Database referential integrity: `test_fk_constraints.py`
- Ingestion validation: `test_validation_suite.py`
- Feature extractor correctness: `test_feature_extractors.py`
- Health and monitoring: `test_monitoring.py`
- Encoding-based security bypasses: `test_encoding_bypasses.py`

### backend/data/

- `raw/` — Source Excel files dropped here for ingestion. Not committed to version control.
- `quarantine/` — Rows that failed validation are written here as CSV with error annotations.
- `sql_app.db` — SQLite database file (development only).

## /frontend

### frontend/package.json

Key runtime dependencies:

- `react` 18, `react-dom` 18
- `react-router-dom` v6
- `axios`
- `react-bootstrap`, `bootstrap` 5
- `chart.js` v4, `react-chartjs-2` v5
- `recharts` v3
- `framer-motion`
- `react-icons`

### frontend/nginx.conf

Nginx server block for production. Serves the React build as static files and proxies `/api/` to the backend container at `http://backend:8000`.

### frontend/Dockerfile

Multi-stage build: Node 18 Alpine build stage compiles the React app with `npm run build`; Nginx Alpine serve stage copies the build output and the nginx.conf.

### frontend/src/index.js

Application entry point. Renders `<App />` wrapped in `<AuthProvider>`, `<StudentProvider>`, and `<ThemeProvider>`.

### frontend/src/App.js

Route definitions using React Router v6. Wraps all non-auth routes in `<ProtectedRoute>`. Routes:

- `/` — Dashboard
- `/students` — Student list
- `/students/:id` — Student profile
- `/risk-factors` — Risk signal breakdown
- `/insights` — Analytics
- `/reports` — Reports
- `/settings` — Settings
- `/login` — Login
- `/signup` — Signup

### frontend/src/chartConfig.js

Globally registers Chart.js components required across the application, including `ArcElement` for doughnut charts, `CategoryScale`, `LinearScale`, `BarElement`, `LineElement`, `PointElement`, `Legend`, and `Tooltip`.

### frontend/src/pages/

- `Dashboard.jsx` — Main overview page. Displays risk metric summaries, student snapshot cards, and trend indicators sourced from StudentContext and the analytics API.
- `Students.jsx` — Paginated, filterable, and sortable student list. Supports search by name and filtering by risk level or department.
- `StudentProfile.jsx` — Deep-dive view for a single student. Shows risk history chart (line), intervention log, engineered feature breakdown, goals, and LLM-generated narrative advice.
- `RiskFactors.jsx` — Institution-wide risk signal breakdown and heatmap visualizations.
- `Analytics.jsx` — Four KPI cards (Total Students, At-Risk, Critical, Avg Attendance), Student Risk Distribution doughnut chart, Top Risk Factors horizontal bar chart, Cohort Comparison grouped bar chart, Intervention Effectiveness before/after bar chart with delta metric badges, and Risk Profile RadarChart across six factors by risk group.
- `Reports.jsx` — Interface for generating and downloading PDF and CSV reports.
- `Settings.jsx` — User preferences including notification settings.
- `Login.jsx` — OAuth2 password grant login form.
- `Signup.jsx` — Animated registration form (framer-motion) with password strength meter and success state.

### frontend/src/components/

- `common/` — `Layout`, `Navigation`, `Header`, `Footer`, `Logo.jsx` (exports `MeridianMark` SVG and default `Logo`)
- `dashboard/` — Dashboard widgets, student summary cards, risk indicator badges
- `analytics/` — Recharts-based chart components, heatmap, trend visualizers
- `student/` — Student detail panels, intervention log entries, goal cards
- `ai/` — Components for rendering LLM-generated advice and faculty summaries
- `quality/` — Data quality score display components

### frontend/src/context/

- `AuthContext.js` — Stores the JWT access token in memory, persists the refresh token in an httpOnly cookie pattern, provides `login`, `logout`, and `refreshToken` functions, and registers an Axios interceptor to retry failed requests after a token refresh.
- `StudentContext.js` — Fetches and caches student data from the API. Exports `students`, `loading`, `error`, and `totalStudents` for consumer components.
- `ThemeContext.js` — Dark/light mode toggle state with local storage persistence.

### frontend/src/services/api.js

Centralized Axios instance. Resolves the base URL from `REACT_APP_API_URL` (CRA) or `VITE_API_URL` environment variables, defaulting to `http://localhost:8000`. Attaches the Authorization header from AuthContext on every request. Response interceptor normalizes all API responses to a consistent `{ success, message, data }` shape. Triggers global toast notifications on 4xx and 5xx responses.

### frontend/src/hooks/

- `useStudentRisk.js` — Fetches and caches risk data for a given student ID with loading and error states.
- `useIntervention.js` — Provides `createIntervention`, `updateIntervention`, and `deleteIntervention` mutations with optimistic UI updates.
- `useDebounce.js` — Returns a debounced value, used to throttle search input API calls.

### frontend/src/utils/

- `motionConfig.js` — Framer Motion variant objects (`container`, `item`) for staggered animations
- `riskThresholds.js` — Threshold constants mirroring backend values for client-side risk label rendering
- `riskScoreValidator.js` — Client-side validation that score values are within 0-100
- `riskNarrativeGenerator.js` — Generates human-readable summary text from a numeric risk score
- `timelineDataGenerator.js` — Formats risk snapshot records into chart-ready time series data
- `trendCalculator.js` — Computes trend direction and magnitude from time series arrays
- `csvParser.js` — Parses CSV content for optional client-side import preview
- `dataQualityCalculator.js` — Computes data completeness scores from student records
- `studentUtils.js` — Filtering and sorting helpers for student arrays
- `recommendationEngine.js` — Client-side recommendation text generation from risk signals

## /models

- `train_model.py` — Ten-stage ML training pipeline: data ingestion, feature engineering, preprocessing, class balancing (SMOTE-Tomek), hyperparameter tuning (Optuna, 50 trials, 5-fold CV), training of six classifiers (Random Forest, XGBoost, LightGBM, CatBoost, Gradient Boosting, MLP), evaluation (ROC-AUC, confusion matrix, precision/recall), ensemble construction (weighted voting by validation AUC), and model export.
- `ensemble.py` — Weighted voting ensemble implementation.
- `model_zoo.py` — Factory returning configured sklearn/XGBoost estimator instances.
- `evaluation.py` — Metric computation and report generation.
- `feature_engineering.py` — 28-feature extraction specific to the training data schema.
- `preprocessing.py` — Imputation, standard scaling, and value clamping.
- `hyperparameter_tuning.py` — Optuna study configuration per model type.
- `model_loader.py` — Inference wrapper that loads the persisted model and exposes a `predict(features)` method.
- `predict_model.py` — Batch prediction script for offline scoring.
- `config.yaml` — Model metadata: name, version, feature list, threshold values.
- `saved_models/` — Persisted model artifacts:
  - `random_forest.pkl`
  - `xgboost_model.pkl`
  - `feature_importance.json`
  - `feature_list.json`

## /docs

- `ARCHITECTURE.md` — Architecture Decision Records (ADRs): ADR-001 (rule-based scoring rationale), ADR-002 (SQLite dev / PostgreSQL prod separation), ADR-003 (JWT strategy), ADR-004 (feature engineering modularity)
- `API_REFERENCE.md` — OpenAPI-style endpoint reference with request/response examples
- `DEPLOYMENT.md` — Step-by-step deployment instructions for local, Docker, and cloud targets
- `DATABASE_INTEGRITY_STRATEGY.md` — Data consistency approach, constraint design, and migration strategy
- `ci.md` — CI/CD pipeline documentation

## /.github/workflows/

- `ci.yml` — GitHub Actions CI pipeline (see Deployment section)

# Installation

## System Requirements

- Python 3.11 or 3.12
- Node.js 18.x or 20.x
- npm 9+
- Redis 7+ (optional in development; required in production for rate limiting and token revocation)
- SQLite 3 (development) or PostgreSQL 14+ (production)

## Step-by-Step Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd ews-retention-platform
```

### 2. Set up Python environment

```bash
bash setup.sh
source venv/bin/activate
```

The `setup.sh` script creates a virtual environment at `./venv` and installs both `requirements.txt` and `requirements-dev.txt`.

Manual equivalent:

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```
SECRET_KEY=<random 64-char hex string>
DATABASE_URL=sqlite:///./backend/data/sql_app.db
LLM_PROVIDER=gemini
GEMINI_API_KEY=<your key>
```

See the Configuration section for the full variable reference.

### 4. Initialize the database

The database tables are created automatically on first application startup via SQLAlchemy's `create_all`. No manual migration step is required for fresh development setup. For production with Alembic:

```bash
alembic upgrade head
```

### 5. Set up the frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```
REACT_APP_API_URL=http://localhost:8000
```

### 6. (Optional) Start Redis

```bash
redis-server
```

If Redis is not running, the application starts with an in-memory TTLCache fallback for rate limiting and token revocation. This fallback does not persist across restarts.

# Configuration

## Environment Variables

All variables are read from the process environment or a `.env` file in the project root. The `.env.example` file documents every supported variable. Key variables are listed below.

### Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./backend/data/sql_app.db` | SQLAlchemy connection string. Use `postgresql+asyncpg://user:pass@host/db` for production. |

### API Server

| Variable | Default | Description |
|---|---|---|
| `API_HOST` | `0.0.0.0` | Bind address for uvicorn |
| `API_PORT` | `8000` | Bind port |
| `ENVIRONMENT` | `development` | `development` or `production`. Controls CORS strictness, debug output, and cookie security flags. |

### Authentication

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (required) | HMAC signing key for JWT tokens. Must be set; startup fails if value equals the placeholder. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | JWT access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime in days |

### CORS

| Variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated list of allowed origins. In production, must contain only HTTPS origins. |

### Redis

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string. Used for rate limiting, token blacklist, and response cache. |
| `CACHE_EXPIRE_SECONDS` | `300` | Default TTL for cached responses |

### LLM

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini` or `claude` |
| `GEMINI_API_KEY` | (required if provider=gemini) | Google Gemini API key |
| `ANTHROPIC_API_KEY` | (required if provider=claude) | Anthropic Claude API key |
| `LLM_MODEL` | Provider-specific default | Model identifier string |

### Risk Thresholds

| Variable | Default | Description |
|---|---|---|
| `RISK_THRESHOLD_LOW` | `20` | Score below which a student is considered low risk |
| `RISK_THRESHOLD_MEDIUM` | `40` | Score above which a student is considered medium risk |
| `RISK_THRESHOLD_HIGH` | `70` | Score above which a student is considered high risk |

### Feature Weights

Weights are configured as individual environment variables per signal. Default values:

| Variable | Default | Signal |
|---|---|---|
| `WEIGHT_CONTENT_COMPLETION` | `0.30` | LMS content completion rate |
| `WEIGHT_LOGIN_CONSISTENCY` | `0.20` | Login frequency consistency |
| `WEIGHT_ASSIGNMENT_ADHERENCE` | `0.20` | Assignment submission adherence |
| `WEIGHT_QUIZ_PERFORMANCE` | `0.15` | Quiz score performance |
| `WEIGHT_DISCUSSION_ENGAGEMENT` | `0.05` | Discussion forum participation |
| `WEIGHT_SELF_DIRECTED` | `0.05` | Self-directed learning signal (inverted) |
| `WEIGHT_EXAM_READINESS` | `0.05` | Exam readiness indicator |

### Rate Limiting

| Variable | Default | Description |
|---|---|---|
| `RATE_LIMIT_LOGIN` | `5/minute` | Maximum login attempts per IP |
| `RATE_LIMIT_INGEST` | `10/hour` | Maximum ingestion triggers per user |
| `RATE_LIMIT_DEFAULT` | `200/minute` | Default limit for all other endpoints |

### Ingestion

| Variable | Default | Description |
|---|---|---|
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum accepted file size for data ingestion uploads |
| `DATA_RAW_DIR` | `backend/data/raw` | Directory scanned for Excel ingestion files |
| `DATA_QUARANTINE_DIR` | `backend/data/quarantine` | Directory where invalid rows are written |

## Secrets Handling

The application validates at startup that `SECRET_KEY` and any required LLM API keys are not set to their placeholder values from `.env.example`. If placeholder values are detected and `ENVIRONMENT` is `production`, the application refuses to start. Never commit `.env` to version control.

# Usage

## Starting in Development Mode

### Backend

```bash
source venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables hot reload on file changes.

### Frontend

```bash
cd frontend
npm start
```

The React development server starts on port 3000 and proxies API calls to `localhost:8000`.

### Interactive API documentation

```
http://localhost:8000/docs
```

FastAPI's built-in Swagger UI is available in development. It is disabled when `ENVIRONMENT=production`.

## Starting with Docker Compose

```bash
docker-compose up -d
```

This starts:
- `backend` on port 8000
- `frontend` on port 3000 (Nginx serving the React build)
- `redis` on port 6379

To rebuild after code changes:

```bash
docker-compose up -d --build
```

## Triggering Data Ingestion

Via API (requires admin role):

```bash
curl -X POST http://localhost:8000/api/admin/ingest \
  -H "Authorization: Bearer <token>" \
  -F "file=@/path/to/engagement_export.xlsx"
```

Poll the job status:

```bash
curl http://localhost:8000/api/admin/ingest/status/<task_id> \
  -H "Authorization: Bearer <token>"
```

Via CLI (deprecated, for development only):

```bash
python -m backend.ingestion.pipeline --file backend/data/raw/Engagement_Analysis.xlsx
```

## Running the ML Training Pipeline

```bash
cd models
python train_model.py
```

Outputs to `models/saved_models/`. The backend will use these artifacts on the next startup if present.

# API Documentation

All endpoints require a Bearer token in the `Authorization` header unless noted. Token obtained from the login endpoint.

## Authentication

### POST /api/auth/login

Request:
```json
{ "username": "user@example.com", "password": "secret" }
```

Response 200:
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

A `refresh_token` is set as an httpOnly cookie.

Status codes: 200 OK, 401 Unauthorized (invalid credentials), 429 Too Many Requests (rate limit exceeded)

### POST /api/auth/refresh

No request body. Reads the `refresh_token` cookie.

Response 200: new `access_token` JSON and updated `refresh_token` cookie.

Status codes: 200 OK, 401 Unauthorized (missing/expired/revoked refresh token)

### POST /api/auth/logout

Revokes the current access token JTI and clears the refresh token cookie.

Status codes: 200 OK

## Students

### GET /api/students

Query parameters: `page` (int, default 1), `page_size` (int, default 20, max 100), `department` (string), `risk_level` (low|medium|high|critical), `search` (string, matches name or BITS ID)

Response 200:
```json
{
  "students": [ { "id": "...", "name": "...", "risk_score": 72, "risk_level": "high", ... } ],
  "total": 342,
  "page": 1,
  "page_size": 20
}
```

Roles: admin, retention_team, faculty (faculty sees only their department)

### GET /api/students/{student_id}

Returns full student record including latest risk score, engineered features, intervention count, and goal count.

Status codes: 200 OK, 403 Forbidden (faculty accessing out-of-department student), 404 Not Found

### GET /api/students/{student_id}/risk-history

Returns chronological list of risk snapshots.

Response 200:
```json
{ "history": [ { "week": 3, "risk_score": 65, "recorded_at": "2025-02-10T03:00:00Z" } ] }
```

## Predictions

### POST /api/ml/predict/batch

Triggers an on-demand batch re-scoring of all active students.

Roles: admin, retention_team

Response 202:
```json
{ "task_id": "<uuid>", "status": "queued" }
```

### GET /api/ml/status

Returns current model status (rule-based only vs. ML blended), model version if loaded, and last batch prediction timestamp.

## Analytics

### GET /api/analytics/kpis

Response 200:
```json
{
  "total_students": 342,
  "at_risk_count": 87,
  "critical_count": 23,
  "avg_attendance": 74.2,
  "high_risk_percentage": 25.4
}
```

### GET /api/analytics/drill-down

Query parameters: `dimension` (department|course|risk_level), `value` (string)

Returns aggregated metrics for the specified dimension slice.

### GET /api/analytics/top-risk-velocity

Returns students with the highest rate of risk score increase over the last two weeks.

## LLM Endpoints

All LLM endpoints are rate-limited to 10 requests per minute per authenticated user.

### POST /api/llm/explain/{student_id}

Generates a narrative explanation for a student's recent risk score change.

Response 200:
```json
{ "explanation": "...", "factors": ["low content completion", "missed deadlines"], "generated_at": "..." }
```

### POST /api/llm/advice/{student_id}

Returns personalized academic advice for the student.

### POST /api/llm/faculty-summary/{student_id}

Returns a faculty-facing summary with risk context and suggested intervention actions.

### POST /api/llm/what-if/{student_id}

Request:
```json
{ "scenario": { "content_completion": 0.85, "quiz_performance": 0.70 } }
```

Returns projected risk score change under the hypothetical scenario.

### POST /api/llm/pattern-discovery

Triggers cohort-level pattern analysis. Roles: admin, retention_team.

### GET /api/llm/institutional-insights

Returns institution-level risk patterns and revenue impact estimates.

## Admin

### GET /api/admin/users

Returns paginated list of system users.

### POST /api/admin/users

Creates a new user account.

Request:
```json
{ "email": "...", "username": "...", "password": "...", "role": "faculty", "department": "CS" }
```

### GET /api/admin/audit-logs

Query parameters: `user_id`, `action`, `from_date`, `to_date`, `page`, `page_size`

### GET /api/admin/ingestion-runs

Returns history of data ingestion jobs with status, row counts, and error counts.

## Monitoring

### GET /health

No authentication required. Returns 200 with basic uptime information if the application is running.

### GET /ready

Returns 200 if database and Redis connectivity checks pass. Returns 503 otherwise. Used as a Kubernetes/load balancer readiness probe.

# Data Flow Explanation

## Inbound Data (Ingestion)

1. An administrator uploads an Excel file via `POST /api/admin/ingest` or drops the file into `backend/data/raw/`.
2. `validated_pipeline.py` loads the file into a Pandas DataFrame using openpyxl.
3. The schema manager verifies that required column headers are present.
4. Row-level validators check field types, value ranges, and cross-field consistency.
5. Rows failing validation are written to `backend/data/quarantine/` as CSV with error annotations. The remaining rows proceed.
6. Transformers coerce types and normalize values (e.g., percentage strings to floats, date strings to UTC datetime objects).
7. Records are written transactionally to the SQLite/PostgreSQL database across `students`, `enrollments`, `courses`, `graded_components`, and `raw_events` tables.
8. An `IngestionRun` record is created with row counts and error counts. The `data_lineage` table records the source filename for each batch.

## Risk Scoring

1. The scheduler triggers the daily prediction job at 3:00 AM UTC, or a batch prediction is requested via API.
2. For each active student, `feature_engineering.py` queries enrollment, event, and graded component records and computes values for each of the five feature domains.
3. `risk_scoring.py` applies weights to the domain scores and produces a base risk score.
4. `calendar_scorer.py` reads the current semester week and applies a time-aware adjustment.
5. If a trained model is present in `models/saved_models/`, `ml_service.py` runs inference and blends the model output with the rule-based score at the configured ratio (default 30% ML).
6. The final score is persisted to the `predictions` table and a `RiskSnapshot` record is written for trend tracking.

## Frontend Data Retrieval

1. The React application authenticates via `POST /api/auth/login` and stores the access token in AuthContext memory.
2. On dashboard load, `StudentContext` calls `GET /api/students` and caches the response.
3. Individual student pages call `GET /api/students/{id}`, `GET /api/students/{id}/risk-history`, and optionally `POST /api/llm/explain/{id}`.
4. Analytics page calls `GET /api/analytics/kpis` and additional drill-down endpoints.
5. All responses pass through the Axios interceptor in `api.js`, which normalizes the shape and triggers toasts on errors.
6. Token refresh is handled transparently: if a 401 response is received, the interceptor calls `POST /api/auth/refresh` and retries the original request once.

# Database Schema

## Core Tables

### students

| Column | Type | Constraints |
|---|---|---|
| id | VARCHAR (email) | PRIMARY KEY |
| org_defined_id | VARCHAR | UNIQUE NOT NULL (BITS student ID) |
| name | VARCHAR | NOT NULL |
| department | VARCHAR | |
| is_active | BOOLEAN | DEFAULT TRUE |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### users

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| username | VARCHAR | UNIQUE NOT NULL |
| email | VARCHAR | UNIQUE NOT NULL |
| hashed_password | VARCHAR | NOT NULL |
| role | VARCHAR | NOT NULL (student/faculty/retention_team/admin) |
| department | VARCHAR | |
| is_active | BOOLEAN | DEFAULT TRUE |
| is_superuser | BOOLEAN | DEFAULT FALSE |

### enrollments

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY |
| student_id | VARCHAR | FOREIGN KEY → students.id ON DELETE CASCADE |
| course_id | VARCHAR | FOREIGN KEY → courses.id |
| content_completion | FLOAT | |
| login_count | INTEGER | |
| discussion_posts | INTEGER | |
| assignment_submitted | INTEGER | |
| assignment_total | INTEGER | |
| Composite UNIQUE | (student_id, course_id) | |

### predictions

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY |
| student_id | VARCHAR | FOREIGN KEY → students.id |
| risk_score | FLOAT | NOT NULL, CHECK (0 <= risk_score <= 100) |
| engagement_score | FLOAT | |
| retention_likelihood | FLOAT | |
| academic_signal | FLOAT | |
| engagement_signal | FLOAT | |
| consistency_signal | FLOAT | |
| intent_signal | FLOAT | |
| responsiveness_signal | FLOAT | |
| predicted_at | DATETIME | NOT NULL |
| model_version | VARCHAR | |
| Composite UNIQUE | (student_id, DATE(predicted_at)) | |

### risk_snapshots

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY |
| student_id | VARCHAR | FOREIGN KEY → students.id |
| risk_score | FLOAT | |
| week_number | INTEGER | |
| semester | VARCHAR | |
| snapshot_date | DATETIME | |

### interventions

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY |
| student_id | VARCHAR | FOREIGN KEY → students.id |
| faculty_assigned | INTEGER | FOREIGN KEY → users.id |
| action | TEXT | |
| priority | VARCHAR | (low/medium/high/critical) |
| status | VARCHAR | (pending/in_progress/completed/cancelled) |
| created_at | DATETIME | |
| resolved_at | DATETIME | |

### audit_logs

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PRIMARY KEY |
| user_id | INTEGER | FOREIGN KEY → users.id |
| action | VARCHAR | NOT NULL |
| resource | VARCHAR | NOT NULL |
| resource_id | VARCHAR | |
| ip_address | VARCHAR | |
| timestamp | DATETIME | NOT NULL |

No UPDATE or DELETE operations are permitted on this table. Enforced at the application layer.

### revoked_tokens

| Column | Type | Constraints |
|---|---|---|
| jti | VARCHAR | PRIMARY KEY |
| user_id | INTEGER | FOREIGN KEY → users.id |
| revoked_at | DATETIME | NOT NULL |
| expires_at | DATETIME | |

## Star Schema (Analytical Layer)

The `dim_students`, `dim_courses`, `fact_academic_performance`, `fact_engagement`, `fact_consistency`, and `fact_intent_responsiveness` tables form a denormalized star schema used for aggregate analytical queries. Data is populated from the normalized tables during the ingestion pipeline.

## Indexes

- `(student_id, is_active)` on students for active student filtering
- `(student_id, course_id)` on enrollments (unique constraint enforces this)
- `(student_id, DATE(predicted_at))` on predictions (unique constraint)
- `(student_id)` on risk_snapshots for trend queries
- `(user_id, timestamp)` on audit_logs for compliance queries

## Alembic Migrations

17 migration versions are recorded under `alembic/versions/`. Migration history includes: initial schema creation, enrollment constraints, prediction indexes, FERPA audit log fields, soft delete columns, timezone-aware timestamp normalization, and star schema tables.

# Testing

## Running the Test Suite

```bash
source venv/bin/activate
pytest
```

With coverage report:

```bash
pytest --cov=backend --cov-report=term-missing
```

Run a specific test file:

```bash
pytest backend/tests/test_risk_scoring.py -v
```

Run security-focused tests only:

```bash
pytest backend/tests/test_idor.py backend/tests/test_encoding_bypasses.py backend/tests/test_security_headers.py -v
```

## Test Structure

Tests are located in `backend/tests/`. Each test file uses pytest fixtures defined in `conftest.py` at the same level. Fixtures provide an in-memory SQLite test database, a test client (FastAPI `TestClient`), and factory functions for creating test users and students.

Integration tests that call LLM endpoints are marked with `@pytest.mark.llm` and skipped in CI unless `RUN_LLM_TESTS=1` is set.

## Coverage Notes

Areas with strong coverage:
- Authentication flows and token lifecycle
- Risk scoring calculation accuracy
- IDOR and access control enforcement
- Security header presence
- Database referential integrity

Areas with limited coverage:
- Frontend components (no automated UI tests)
- Ingestion pipeline edge cases for malformed Excel files
- Scheduler job execution under concurrency
- LLM hallucination guard edge cases
- Export service PDF generation

## Linting and Type Checking

```bash
flake8 backend/
mypy backend/ --config-file mypy.ini
```

# Deployment

## Local Development

See Installation section.

## Docker Compose

The `docker-compose.yml` at the project root defines three services:

- `backend`: Built from `backend/Dockerfile`. Runs `uvicorn backend.main:app --host 0.0.0.0 --port 8000`. Mounts `backend/data/` as a volume for database persistence.
- `frontend`: Built from `frontend/Dockerfile` (multi-stage). Serves on port 3000 via Nginx.
- `redis`: Official Redis 7 Alpine image. Port 6379 exposed only within the Docker network.

```bash
docker-compose up -d
docker-compose logs -f backend
docker-compose down
```

## Production Deployment

### Prerequisites

1. PostgreSQL 14+ database provisioned
2. Redis 7+ instance provisioned
3. TLS termination at the load balancer or reverse proxy level
4. Environment variables set (see Configuration section)

### Steps

1. Set `ENVIRONMENT=production` and configure a PostgreSQL `DATABASE_URL`
2. Set a strong random `SECRET_KEY` (minimum 64 characters)
3. Configure `CORS_ORIGINS` to list only your production frontend HTTPS origin
4. Run `alembic upgrade head` against the production database
5. Build and push Docker images
6. Deploy using your container orchestration tool (ECS, Cloud Run, Kubernetes, etc.)
7. Configure the load balancer health check to `GET /ready`

### CI/CD Pipeline

The `.github/workflows/ci.yml` pipeline runs on every push and pull request.

Jobs:

1. **test-backend** (Python 3.11, 3.12 matrix): dependency install, flake8 lint, mypy type check, pytest with coverage upload to Codecov
2. **test-frontend** (Node 18.x, 20.x matrix): npm install, ESLint, production build, test run with coverage
3. **security-scan**: Bandit static analysis for Python vulnerabilities, detect-secrets for hardcoded credential detection
4. **docker-build**: Docker image build and `docker-compose config` validation
5. **all-checks-pass**: Fan-in gate job that blocks merge if any prior job failed

### Scaling Considerations

The backend uses a single `asyncio.Lock()` for ingestion serialization. This design is incompatible with multi-worker uvicorn deployments. Running more than one worker process requires replacing this lock with a Redis distributed lock (e.g., using `aioredlock`). A TODO comment in `validated_pipeline.py` marks this limitation.

The APScheduler instance runs in-process. In a multi-replica deployment, all replicas would independently run scheduled jobs, causing duplicate predictions and notifications. This requires either a designated scheduler replica or migration to a distributed task queue (Celery with Redis broker, or a managed scheduler service).

SQLite is incompatible with multi-process write concurrency. PostgreSQL must be used for any deployment with more than one backend process.

# Logging and Monitoring

## Logging

The backend uses Python's standard `logging` module configured in `backend/core/logger.py`. Log format includes timestamp, level, logger name, request ID (injected by the request ID middleware), and message. Log level is configurable via the `LOG_LEVEL` environment variable (default: `INFO`).

PII masking is applied by a custom log filter that replaces student email addresses and BITS IDs in log messages with redacted tokens before emission.

Security events (login attempts, authorization failures, suspicious patterns) are written to a dedicated `security` logger and can be routed to a separate sink.

## Audit Logging

All operations that access, modify, or export student PII write an entry to the `audit_logs` table via `backend/core/audit_logger.py`. This is append-only at the application layer. Records include user ID, action type, resource type, resource ID, client IP address, and timestamp. The audit log is queryable by admin users via `GET /api/admin/audit-logs`.

## Monitoring Endpoints

- `GET /health` — Always returns 200 if the process is running. Used as a liveness probe.
- `GET /ready` — Returns 200 if database and Redis connections are healthy; 503 otherwise. Used as a readiness probe.
- `GET /metrics` — Prometheus-compatible metrics endpoint (request counts, latency histograms, error rates). Available if a metrics library is configured.

## Observability Gaps

There is no distributed tracing integration (no OpenTelemetry instrumentation). Request IDs provide per-request correlation within a single process but do not propagate to external LLM API calls. There is no alerting configuration in the repository.

# Security Considerations

## Authentication

JWT-based authentication using HS256 signing. Access tokens expire after 15 minutes. Refresh Token Rotation (RTR) is implemented: each refresh issues a new refresh token and revokes the previous token's JTI in Redis. Detection of a reused (superseded) refresh token triggers revocation of the entire token family for that user.

Tokens contain: `sub` (user ID), `role`, `exp`, `iat`, `iss`, `aud`, `jti`, `nbf`, `type` (access/refresh).

## Authorization

Role-based access control is enforced at the route handler level via FastAPI dependency injection. The four roles are: `student` (own data only), `faculty` (department-scoped), `retention_team` (institution-wide read), `admin` (full access).

Student ownership is verified on all student-scoped endpoints: a student user cannot access another student's data. Faculty department scoping is verified on student list and detail endpoints. IDOR test cases in `backend/tests/test_idor.py` validate these controls.

## Input Validation

Request bodies are validated by Pydantic models with strict type annotations. Request size is enforced by the `request_validation` middleware. File uploads are limited by `MAX_UPLOAD_SIZE_MB`. SQL injection is not possible through the ORM layer; all queries use parameterized statements via SQLAlchemy.

## LLM Safety

Prompt templates are defined as static strings with typed variable substitution. No raw user-supplied text is interpolated directly into prompts sent to the LLM API. Hallucination guards in `llm_orchestrator.py` validate that LLM responses contain expected structured fields before returning them to API callers. All LLM queries are logged to the `llm_queries` table.

## Rate Limiting

SlowAPI middleware applies per-IP rate limits backed by Redis (TTLCache fallback). Login endpoint: 5 requests/minute. Ingestion endpoint: 10 requests/hour. All other endpoints: 200 requests/minute. LLM endpoints have an additional per-user 10 requests/minute limit applied at the service layer.

## Security Headers

The `security_headers` middleware injects on every response:
- `Content-Security-Policy`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security` (max-age=31536000)
- `Referrer-Policy: strict-origin-when-cross-origin`

## Known Risks

- The SQLite WAL mode does not provide the same isolation guarantees as PostgreSQL under concurrent writes during ingestion. SQLite is not supported for production use.
- The `asyncio.Lock()` in the ingestion pipeline serializes requests but does not survive process restart or multi-worker deployment.
- LLM provider API keys are stored as environment variables. If the container environment is compromised, these keys are exposed. A secrets manager (AWS Secrets Manager, HashiCorp Vault) is recommended for production.
- The `feedback.py` route is a placeholder with no access control enforcement. It must not be mounted in production until fully implemented.

# Performance Considerations

## Bottlenecks

- Feature engineering for all active students runs synchronously in the daily prediction job. For institutions with several thousand students, this job may take several minutes and blocks other scheduler tasks. Parallelization using `asyncio.gather` or a task queue is the recommended remediation.
- LLM API calls are synchronous within async route handlers via `asyncio.run_in_executor`. Response times are dependent on the LLM provider and range from 2 to 15 seconds. These calls are not cached by default.
- The Analytics page makes several sequential API calls on mount. Parallel request batching on the frontend would reduce perceived load time.

## Caching

Redis-backed response caching is implemented in `backend/core/redis_cache.py`. Cache TTL defaults to 300 seconds. Analytics KPI endpoints and student list responses are candidates for caching. Currently, caching is applied selectively; expansion to additional read-heavy endpoints is noted as a future improvement.

The TTLCache fallback operates per-process and is not shared across replicas.

## Database

Composite indexes on frequently queried column combinations (`student_id + is_active`, `student_id + course_id`) are present. For larger datasets, additional indexes on `predictions.predicted_at` and `risk_snapshots.week_number` should be evaluated. The star schema analytical tables offload aggregate query load from the normalized tables.

## Scalability Notes

With SQLite, meaningful concurrency is limited to read-only workloads. PostgreSQL with connection pooling (PgBouncer) is required for any production load. The current architecture is designed for single-institution deployment. Horizontal scaling of the backend requires resolving the distributed lock and scheduler conflicts described above.

# Limitations

- **No LMS API integration.** Data ingestion relies entirely on manually exported Excel files. There is no webhook receiver or LMS plugin. Any automation requires external tooling to place files in the watched directory.
- **SQLite in production is unsupported.** The database layer defaults to SQLite for developer convenience, but SQLite's write concurrency model makes it unsuitable for multi-user production deployment.
- **Single-process scheduler.** The APScheduler instance does not coordinate across multiple backend replicas. Multi-replica deployment will produce duplicate scheduled job execution.
- **Single-worker ingestion lock.** The `asyncio.Lock()` serializes ingestion within one process only. Multi-worker deployment breaks this guarantee.
- **No frontend test suite.** There are no automated UI tests, integration tests for React components, or end-to-end tests. Frontend correctness is unverified by CI.
- **Placeholder routes in codebase.** `predictions.py`, `events.py`, and `feedback.py` are mounted but either unused or partially implemented. They represent active technical debt and potential security surface area.
- **ML model dependency.** The ensemble ML model requires training data not included in the repository. Without a trained model, the system operates in rule-based-only mode. The rule-based scorer produces reasonable results but has not been validated against outcome data in this codebase.
- **No SSO or institutional identity federation.** User accounts are local to the system. Integration with campus LDAP, SAML, or OAuth2 providers is not implemented.
- **No email delivery.** The notification service generates email content and routing decisions but does not include an SMTP client or email service provider integration. Email dispatch requires external implementation.
- **FERPA compliance is application-layer only.** The append-only constraint on `audit_logs` is enforced in application code, not at the database level. A database-level trigger or role restriction is recommended for production.
- **No multi-tenancy.** The data model has no tenant identifier. Deploying for multiple institutions requires schema changes and row-level security implementation.

# Roadmap / Future Improvements

Based on the current state of the codebase and in-code TODO comments:

- Replace the `asyncio.Lock()` ingestion serialization with a Redis distributed lock to support multi-worker deployment
- Migrate APScheduler to a distributed task queue (Celery) to eliminate duplicate scheduled job execution in multi-replica environments
- Implement the `feedback.py` route with proper access control and persistence
- Remove the unused `predictions.py` and `events.py` routes (tracked as CROSS-5 in code comments)
- Train and validate the ML ensemble model against actual student outcome data to enable ML blending in production
- Expand Redis response caching to cover LLM endpoint responses with a per-student TTL
- Add OpenTelemetry instrumentation for distributed tracing across the backend and outbound LLM calls
- Implement SMTP or transactional email provider integration for the notification service
- Add React component tests and at least one end-to-end test covering the login and dashboard load flow
- Enforce the `audit_logs` append-only constraint at the database layer via a trigger or restricted database role
- Add database-level tenant isolation columns as a prerequisite for multi-institution support

# Troubleshooting

## Backend fails to start with "SECRET_KEY is set to a placeholder value"

The application validates that `SECRET_KEY` in your `.env` file is not the example placeholder. Generate a valid key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## `ModuleNotFoundError: No module named 'backend'`

The backend package is not on the Python path. Run uvicorn from the project root with the virtual environment activated:

```bash
source venv/bin/activate
uvicorn backend.main:app --reload
```

## Redis connection warnings on startup

The application logs a warning but starts successfully if Redis is unavailable. Rate limiting falls back to in-memory TTLCache (not persisted, not shared across processes). To suppress the warning, start Redis before the backend or set `REDIS_URL` to an empty string to explicitly disable Redis integration.

## Ingestion job returns 422 Unprocessable Entity

The uploaded file does not match the expected schema. Check the response body for the specific column name that failed validation. Compare against the column definitions in `backend/ingestion/schema_manager.py`.

## Risk scores are all zero or identical

The feature engineering pipeline received enrollment records with null or zero values across all signals. Verify that the ingestion pipeline completed successfully and that the `enrollments` table contains non-null `content_completion` and related fields for the affected students. Check `backend/data/quarantine/` for rows that were rejected during ingestion.

## LLM endpoints return 503

The LLM provider API key is missing or invalid, or the provider's API returned an error. Check the backend logs for the specific error. Verify that `GEMINI_API_KEY` or `ANTHROPIC_API_KEY` is correctly set and that the corresponding `LLM_PROVIDER` value matches.

## JWT token rejected after backend restart (SQLite mode)

In SQLite development mode, the revoked token table persists across restarts, but the in-memory TTLCache fallback (used when Redis is unavailable) is lost on restart. If a token was revoked in the TTLCache and the cache was lost, the token may be incorrectly accepted again. This is a known limitation of the TTLCache fallback. Use Redis to avoid this behavior.

## Docker Compose frontend shows "API unreachable"

The frontend container attempts to reach the backend at `http://backend:8000` via the internal Docker network. If the backend container has not finished its startup health check, the first requests from the frontend will fail. Wait for the backend container to report as healthy:

```bash
docker-compose ps
```

If the backend shows as unhealthy, check its logs:

```bash
docker-compose logs backend
```

# Contributing

## Code Style

Python code is formatted with Black (line length 88) and linted with Flake8. Type annotations are required for all public functions and are checked with MyPy in strict mode. Run the following before submitting a pull request:

```bash
black backend/
flake8 backend/
mypy backend/
```

JavaScript and JSX code follows the ESLint configuration in `frontend/.eslintrc.js`.

## Branching Strategy

- `main` — Production-ready code only. Direct pushes are not permitted.
- `development` — Integration branch. Feature branches are merged here first.
- Feature branches: `feature/<short-description>`
- Bug fix branches: `fix/<short-description>`
- Hotfix branches: `hotfix/<short-description>`

Pull requests must target `development`. Merges to `main` are done from `development` after review and CI passage.

## Commit Message Format

Follow the Conventional Commits specification:

```
<type>(<scope>): <summary>

<body>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`

Examples:

```
feat(risk-scoring): add calendar-aware semester week adjustment
fix(auth): revoke token family on refresh token reuse detection
test(idor): add IDOR test cases for recommendations endpoint
```

The summary line must be 72 characters or fewer. The body is optional and should explain the why, not the what.

## Pull Request Requirements

- CI must pass on all jobs before merge is permitted
- At least one approving review from a team member
- New features must include test coverage for the critical path
- Security-sensitive changes (auth, RBAC, audit logging) require review from a maintainer with security context

# License

No `LICENSE` file was found in the repository at the time of this writing. Licensing terms have not been declared. Contact the repository maintainers before using, distributing, or contributing to this project.
