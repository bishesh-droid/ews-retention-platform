# Meridian EWS Retention Platform

Early Warning System for student retention — AI-driven risk prediction and intervention management for educational institutions.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Deployment](#deployment)
- [Logging and Monitoring](#logging-and-monitoring)
- [Security Considerations](#security-considerations)
- [Performance Considerations](#performance-considerations)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Overview

### Problem Statement

Educational institutions lose students due to disengagement, academic struggles, and life circumstances. Traditional retention efforts are reactive and lack data-driven insights. This platform provides:

- Early identification of at-risk students using engagement and academic signals
- Automated intervention recommendations based on risk severity
- Business intelligence for retention teams to measure ROI
- FERPA-compliant audit logging for all student data access

### Target Users

- **Faculty**: View student risk profiles, receive alerts, track intervention outcomes
- **Retention Teams**: Manage intervention queues, analyze cohort trends, forecast revenue impact
- **Administrators**: Configure system settings, manage user roles, review audit logs
- **Students**: View personal risk factors, receive recommendations, track progress

### Core Capabilities

- Rule-based risk scoring from 7 engagement signals (0-100 scale)
- Calendar-aware risk adjustments based on academic deadlines
- LLM-powered explanations and intervention suggestions (Gemini/Claude)
- Automated daily prediction generation via scheduler
- Business intelligence dashboards (retention forecasting, revenue at risk)
- Multi-role authentication with JWT tokens and httpOnly refresh cookies

### System Boundaries

- **In Scope**: Student risk scoring, intervention management, analytics, reporting
- **Out of Scope**: LMS integration (file-based ingestion only), student communication (manual outreach), gradebook functionality

## Architecture

### High-Level System Architecture

```
+-------------------+     +------------------+     +-------------------+
|   React SPA       |---->|  FastAPI Backend |---->|   SQLite/         |
|   (Port 3000)     |     |  (Port 8000)     |     |   PostgreSQL      |
+-------------------+     +------------------+     +-------------------+
                                |
                                v
                          +------------------+
                          |   Redis Cache    |
                          |   (Rate Limit)   |
                          +------------------+
```

### Backend Architecture

**Framework**: FastAPI 0.119.0 with async/sync SQLAlchemy 2.0

**Layer Structure**:
- **Routes** (`backend/routes/`): HTTP endpoint handlers, request/response serialization
- **Services** (`backend/services/`): Business logic (risk scoring, feature engineering, LLM orchestration)
- **Core** (`backend/core/`): Cross-cutting concerns (auth, security, logging, rate limiting)
- **Middleware** (`backend/middleware/`): Request processing pipeline (security headers, validation, audit logging)
- **Database** (`backend/database/`): ORM models, connection management, migrations

**Key Design Patterns**:
- Dependency Injection for database sessions and authentication
- Repository pattern for data access (student_repository.py)
- Strategy pattern for LLM provider abstraction (Gemini/Claude)
- Circuit breaker for external API calls (LLM timeouts)

### Frontend Architecture

**Framework**: React 18.2 with Create React App

**State Management**:
- Context API for authentication (AuthContext) and student data (StudentContext)
- Axios interceptors for JWT token management and automatic refresh

**UI Libraries**:
- React Router 6.22 for navigation
- Bootstrap 5.3 for layout components
- Chart.js 4.4 and Recharts 3.7 for data visualization
- Framer Motion 12.31 for animations

**Build**: Webpack 5 via react-scripts 5.0.1

### Data Layer

**Primary Database**: SQLite (development) / PostgreSQL (production)

**Schema Type**: Star schema with dimension and fact tables

**Data Models**:
- **Dimensions**: DimStudent, DimCourse
- **Facts**: FactEngagement, FactAcademicPerformance, FactConsistency, FactIntentResponsiveness
- **Operational**: Prediction, Intervention, RiskSnapshot, InterventionLog, AuditLog

**Migration Tool**: Alembic 1.18.4

### Integration Points

**External Services**:
- Google Gemini API (LLM features)
- Anthropic Claude API (LLM features)
- Redis (distributed rate limiting, caching)

**Data Ingestion**:
- Excel file uploads (.xlsx) via admin interface
- Scheduled ingestion from `backend/data/` directory
- Row-level validation with quarantine for failed records

### External Services

| Service | Purpose | Required |
|---------|---------|----------|
| Redis | Rate limiting, distributed caching | Yes (production) |
| Google Gemini | LLM explanations, suggestions | Optional |
| Anthropic Claude | Alternative LLM provider | Optional |

## Project Structure

### Root Directory

- `backend/` — FastAPI application code
- `frontend/` — React single-page application
- `data/` — Raw and processed data files
- `data_ingestion/` — Standalone ETL pipeline modules
- `docker/` — Dockerfiles and docker-compose configuration
- `alembic/` — Database migration scripts
- `setup.sh` — Development environment setup script
- `.env.example` — Environment variable template
- `requirements.txt` — Python dependencies
- `SECURITY_AND_COMPLIANCE.md` — Security architecture documentation

### /backend

#### Core Application

- `main.py` — FastAPI application entry point, middleware registration, lifespan events
- `config/__init__.py` — Environment variable parsing, configuration constants
- `api/deps.py` — Dependency injection helpers (auth, database sessions)

#### Routes (API Endpoints)

- `auth.py` — Login, logout, token refresh, user registration
- `student_v1.py` — Student profile, goals, risk history (student-facing)
- `faculty_v1.py` — At-risk student lists, alerts (faculty-facing)
- `admin_v1.py` — User management, system configuration
- `students.py` — Student CRUD operations
- `predictions.py` — ML prediction endpoints (legacy)
- `ml_routes.py` — Model training, batch predictions
- `recommendations.py` — Intervention suggestions
- `advisor.py` — AI academic advisor endpoints
- `business.py` — Business intelligence metrics
- `analytics.py` — Cohort analytics, trend analysis
- `interventions.py` — Intervention CRUD
- `decisions.py` — Intervention decision engine
- `reports.py` — Report generation, PDF exports
- `monitoring.py` — Health checks, scheduler status
- `audit.py` — Audit log queries (FERPA compliance)

#### Services

- `risk_scoring.py` — Rule-based risk score calculation (7 signals)
- `feature_engineering.py` — Feature extraction from raw engagement data
- `ml_service.py` — ML model management, prediction orchestration
- `analytics_service.py` — Cohort analysis, trend computation
- `export_service.py` — PDF report generation
- `calendar_scorer.py` — Calendar-aware risk adjustments
- `decision_engine.py` — Intervention threshold logic

##### AI Services (`services/ai/`)

- `llm_orchestrator.py` — Unified LLM interface (Gemini/Claude)
- `rag_engine.py` — Retrieval-augmented generation for student context
- `advisor.py` — AI academic advisor logic
- `hallucination_guard.py` — LLM output validation

##### Feature Services (`services/features/`)

- `academic.py` — Academic performance feature extraction
- `engagement.py` — Engagement signal computation
- `consistency.py` — Login/activity consistency metrics
- `intent.py` — Dropout intent detection
- `composer.py` — Feature composition orchestrator

##### Infrastructure Services (`services/infrastructure/`)

- `scheduler.py` — APScheduler-based background jobs (daily predictions, weekly retraining, GDPR purges)
- `token_cleanup.py` — Revoked token purging
- `recommender.py` — Intervention recommendation engine

#### Database

- `connection.py` — SQLAlchemy engine setup, session factories, PRAGMA configuration
- `models/` — ORM model definitions:
  - `student.py` — Student dimension table
  - `user.py` — System users with RBAC roles
  - `prediction.py` — Risk score predictions
  - `intervention.py` — Intervention records
  - `intervention_log.py` — Intervention action history
  - `risk_snapshot.py` — Historical risk snapshots
  - `audit.py` — FERPA audit logs
  - `academic.py` — GradedComponent, ExamRecord
  - `event.py` — RawEvent, EngineeredFeatures
  - `canonical.py` — Star schema tables (DimStudent, FactEngagement, etc.)
  - `revoked_token.py` — JWT token blocklist
  - `prediction_log.py` — Prediction audit trail

#### Middleware

- `security_headers.py` — HSTS, CSP, X-Frame-Options, etc.
- `security_logging.py` — Access logging, rate limit monitoring
- `request_validation.py` — Input validation middleware
- `request_id.py` — Request ID injection for log correlation

#### Core Modules

- `auth.py` — JWT token creation/validation, password hashing (bcrypt)
- `security.py` — Input sanitization, prompt injection detection, encoding bypass protection
- `rate_limiting.py` — SlowAPI integration, per-user rate limits
- `logger.py` — Structured logging with PII masking
- `audit_logger.py` — FERPA-compliant audit logging
- `errors.py` — Centralized error handling

#### Schemas (Pydantic Models)

- `auth.py` — Authentication request/response schemas
- `student.py` — Student data schemas
- `prediction.py` — Prediction schemas with validation
- `intervention.py` — Intervention schemas
- `common.py` — Shared schemas with validators (GPA, attendance, student ID regex)

#### Tests

- `test_auth.py` — Authentication, token validation
- `test_risk_scoring.py` — Risk score calculation
- `test_integration_api.py` — End-to-end API tests
- `test_idor.py` — IDOR vulnerability tests
- `test_encoding_bypasses.py` — Input sanitization tests
- `test_security_headers.py` — Security header validation
- `test_scheduler.py` — Background job tests
- `conftest.py` — Pytest fixtures, test database setup

### /frontend

#### Pages (`src/pages/`)

- `Dashboard.jsx` — Main dashboard with KPI cards, risk tables
- `Students.jsx` — Student list with filtering, sorting
- `StudentProfile.jsx` — Individual student risk breakdown
- `Analytics.jsx` — Cohort analytics, trend charts
- `Interventions.jsx` — Intervention queue management
- `Reports.jsx` — Report generation interface
- `Login.jsx`, `Signup.jsx` — Authentication pages
- `FacultyTools.jsx` — Faculty-facing views
- `BusinessAnalytics.jsx` — Business intelligence dashboards

#### Components (`src/components/`)

- `ai/` — AI-powered components (AIRecommendationCard, RiskExplanation, WhatIfSimulator)
- `analytics/` — Analytics visualizations (CohortChurnDiagnostics, CourseRiskAnalysis)
- `business/` — Business metrics (RevenueForecast, InterventionROITimeline)
- `common/` — Shared UI components (Logo, Skeleton, ChartExplainerTooltip)
- `dashboard/` — Dashboard widgets (KpiCard, HighestRiskStudentsTable)
- `interventions/` — Intervention components (InterventionCard, Recommendations)
- `student/` — Student profile components (RiskBreakdownChart, SignalRadarChart)

#### Context (`src/context/`)

- `AuthContext.js` — JWT authentication state, token refresh logic
- `StudentContext.js` — Student data state, pagination

#### Services (`src/services/`)

- `api.js` — Axios-based API client with interceptors

### /data

#### Raw Data (`raw/`)

- `Engagement_Analysis.xlsx` — Primary engagement metrics (logins, content views, time spent)
- `_Trimester-1 2025 Attendance Quiz-Assignment-Exam 5Jan2025.xlsx` — Quiz/exam attendance
- `graded quiz 1 10 feb complete.xlsx` — Graded quiz scores
- `Week 1-2 Student Engagement Analysis.xlsx` — Early engagement snapshot
- `Learner usage week 3.xlsx`, `Learner usage week 5.xlsx` — Weekly usage reports
- `B.S and M.Sc Summary Data*.xlsx` — Aggregate course-level data (not student-level)

#### Archive (`archive/`)

- Historical duplicate files moved after consolidation

### /data_ingestion

Standalone ETL pipeline (can run independently of backend):

- `master_builder.py` — Main orchestrator for dataset building
- `loader.py` — Excel file loading
- `schema_mapper.py` — Column name normalization
- `validator.py` — Schema validation
- `normalizer.py` — Data type normalization
- `merger.py` — Multi-file data merging
- `dataset_cache.py` — Intermediate caching

### /docker

- `Dockerfile` — Multi-stage production build (Python 3.12 slim)
- `Dockerfile.scheduler` — Scheduler service image
- `docker-compose.yml` — Full stack orchestration (backend, frontend, redis, scheduler)
- `.env.example` — Docker environment template

### /alembic

Database migration scripts:

- `versions/001_*` through `versions/007_*` — Incremental schema changes
- `env.py` — Alembic configuration

## Installation

### System Requirements

- **OS**: Linux, macOS, Windows (WSL2 recommended)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB free space
- **Storage**: SSD recommended for database performance

### Prerequisites

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| Redis | 7+ | Rate limiting (production) |
| PostgreSQL | 14+ | Production database (optional) |

### Backend Installation

```bash
# Clone repository
git clone <repository-url>
cd ews-retention-platform

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from backend.database.connection import init_db; init_db()"
```

### Frontend Installation

```bash
cd frontend

# Install npm dependencies
npm install

# Start development server
npm start
```

### Redis Installation (Production)

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Generate secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Edit .env with generated values
```

### Database Setup

**SQLite (Development)**:
```bash
# Database is created automatically on first run
# Location: backend/data/sql_app.db
```

**PostgreSQL (Production)**:
```sql
CREATE DATABASE ews_db;
CREATE USER ews_user WITH PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE ews_db TO ews_user;
```

Update `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://ews_user:secure-password@localhost:5432/ews_db
```

## Configuration

### Environment Variables

All configuration is managed via environment variables. See `.env.example` for the complete list.

#### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (min 32 chars) | `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6` |
| `DATABASE_URL` | Database connection string | `sqlite:///./backend/data/sql_app.db` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `ENVIRONMENT` | Environment mode | `development` or `production` |

#### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Server bind address |
| `API_PORT` | `8000` | Server bind port |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT access token lifetime |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `CLAUDE_API_KEY` | — | Anthropic Claude API key |
| `LLM_PROVIDER` | `gemini` | LLM provider (`gemini` or `claude`) |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

#### Risk Scoring Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RISK_THRESHOLD_HIGH` | `70.0` | High risk threshold (0-100) |
| `RISK_THRESHOLD_MEDIUM` | `40.0` | Medium risk threshold (0-100) |
| `WEIGHT_CONTENT_COMPLETION` | `0.30` | Content completion weight |
| `WEIGHT_LOGIN_CONSISTENCY` | `0.20` | Login consistency weight |
| `WEIGHT_QUIZ_ENGAGEMENT` | `0.20` | Quiz engagement weight |
| `WEIGHT_ASSIGNMENT` | `0.15` | Assignment submission weight |
| `WEIGHT_TIME_INVESTMENT` | `0.08` | Time investment weight |
| `WEIGHT_DISCUSSION` | `0.02` | Discussion engagement weight |
| `WEIGHT_SELF_DIRECTED_LEARNING` | `0.05` | Self-directed learning weight (risk reducer) |

#### Intervention Thresholds

| Variable | Default | Description |
|----------|---------|-------------|
| `THRESHOLD_NO_ACTION` | `30.0` | Below: no intervention |
| `THRESHOLD_GENTLE` | `40.0` | 30-40: Gentle reminder (email) |
| `THRESHOLD_MENTOR` | `60.0` | 40-60: Mentor outreach |
| `THRESHOLD_URGENT` | `80.0` | 60-80: Escalated mentor |
| | 80+: Urgent intervention (sales) |

### Configuration Files

**Backend**: All config via `backend/config/__init__.py` reading from environment

**Frontend**: Environment variables via `REACT_APP_API_URL` or `VITE_API_BASE_URL`

### Secrets Management

**Never commit `.env` to version control.**

Generate secure values:
```bash
# Secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Integration API key hash
python -c "import hashlib; print(hashlib.sha256(b'your-key').hexdigest())"
```

## Usage

### Development Mode

**Backend**:
```bash
source venv/bin/activate
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd frontend
npm start
```

**Redis** (required for rate limiting):
```bash
redis-server
```

### Production Mode

**Using Docker**:
```bash
cd docker
docker-compose up -d
```

**Direct Deployment**:
```bash
# Backend
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4

# Frontend (build static files)
cd frontend
npm run build
# Serve with nginx or similar
```

### API Usage Examples

**Authentication**:
```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"

# Response: {"access_token": "eyJ...", "token_type": "bearer"}
```

**Get Student List**:
```bash
curl -X GET "http://localhost:8000/api/v1/students/students?skip=0&limit=50" \
  -H "Authorization: Bearer <access_token>"
```

**Get Single Student**:
```bash
curl -X GET http://localhost:8000/api/v1/students/students/student@example.com \
  -H "Authorization: Bearer <access_token>"
```

**Trigger Data Ingestion**:
```bash
curl -X POST http://localhost:8000/api/v1/admin/ingest \
  -H "Authorization: Bearer <admin_token>" \
  -F "file=@engagement_data.xlsx"
```

**Health Check**:
```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "checks": {...}}
```

## API Documentation

### Authentication Endpoints

#### POST /api/v1/auth/login

OAuth2 token endpoint.

**Request**:
```
Content-Type: application/x-www-form-urlencoded
username: <string>
password: <string>
```

**Response (200)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Response (401)**:
```json
{
  "detail": "Incorrect username or password"
}
```

#### POST /api/v1/auth/refresh

Refresh access token using httpOnly cookie.

**Response (200)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

#### POST /api/v1/auth/logout

Revoke current token and clear refresh cookie.

**Headers**: `Authorization: Bearer <token>`

**Response (200)**:
```json
{
  "message": "Successfully logged out"
}
```

#### GET /api/v1/auth/me

Get current user profile.

**Headers**: `Authorization: Bearer <token>`

**Response (200)**:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "is_active": true,
  "is_superuser": false
}
```

### Student Endpoints

#### GET /api/v1/students/students

Get paginated student list.

**Query Parameters**:
- `skip` (integer, default: 0) — Offset
- `limit` (integer, default: 50) — Page size
- `sort_by` (string, default: `risk_score`) — Sort field
- `order` (string, default: `desc`) — Sort order (`asc` or `desc`)

**Response (200)**:
```json
{
  "success": true,
  "message": "OK",
  "data": {
    "students": [
      {
        "id": "student@example.com",
        "org_defined_id": "2025EB110001",
        "first_name": "John",
        "last_name": "Doe",
        "risk_score": 75.5,
        "engagement_score": 0.45
      }
    ],
    "total": 150
  }
}
```

#### GET /api/v1/students/students/{student_id}

Get detailed student profile.

**Path Parameters**:
- `student_id` (string) — Student email address

**Response (200)**:
```json
{
  "success": true,
  "message": "OK",
  "data": {
    "id": "student@example.com",
    "org_defined_id": "2025EB110001",
    "first_name": "John",
    "last_name": "Doe",
    "predictions": [...],
    "interventions": [...],
    "risk_history": [...]
  }
}
```

### Risk Scoring Endpoints

#### GET /api/v1/ml/predict/{student_id}

Get ML-based risk prediction for a student.

**Path Parameters**:
- `student_id` (string) — Student email

**Response (200)**:
```json
{
  "success": true,
  "message": "Prediction generated",
  "data": {
    "risk_score": 75.5,
    "engagement_score": 0.45,
    "retention_likelihood": "low",
    "model_version": "rule-based-v1.0",
    "top_risk_factors": ["Content Completion", "Login Consistency"]
  }
}
```

### Intervention Endpoints

#### GET /api/v1/interventions

Get all interventions with filtering.

**Query Parameters**:
- `skip`, `limit` — Pagination
- `status` — Filter by status (pending, completed, etc.)
- `assigned_faculty` — Filter by assignee
- `student_id` — Filter by student

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "interventions": [...],
    "total": 25
  }
}
```

#### POST /api/v1/interventions

Create new intervention.

**Request Body**:
```json
{
  "student_org_id": "2025EB110001",
  "intervention_type": "mentor_outreach",
  "priority": "high",
  "assigned_faculty_id": 5,
  "notes": "Student has missed 3 consecutive quizzes"
}
```

### Analytics Endpoints

#### GET /api/v1/students/analytics/risk-trends

Get cohort risk trends over time.

**Query Parameters**:
- `weeks` (integer, default: 8) — Number of weeks to include

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "trends": [
      {"week": 1, "avg_risk": 45.2},
      {"week": 2, "avg_risk": 42.8}
    ]
  }
}
```

#### GET /api/v1/business/metrics/retention

Get retention metrics for business dashboards.

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "retention_rate": 0.87,
    "high_risk_count": 45,
    "gap_to_target": 0.03
  }
}
```

### Admin Endpoints

#### POST /api/v1/admin/ingest

Trigger data ingestion.

**Request**: Multipart form with optional file upload

**Response (202)**:
```json
{
  "task_id": "abc123",
  "message": "Ingestion started"
}
```

#### GET /api/v1/audit-log

Query FERPA audit logs.

**Query Parameters**:
- `user_id`, `action`, `resource_type`, `resource_id` — Filters
- `start_date`, `end_date` — Date range
- `limit`, `offset` — Pagination

**Response (200)**:
```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": 1,
        "user_id": 5,
        "action": "READ",
        "resource_type": "student",
        "resource_id": "student@example.com",
        "timestamp": "2026-04-14T10:30:00Z"
      }
    ],
    "total": 1500
  }
}
```

### System Endpoints

#### GET /health

Health check endpoint.

**Response (200)**:
```json
{
  "status": "healthy",
  "checks": {
    "database": true,
    "redis": true,
    "ml_pipeline": true
  }
}
```

## Data Flow

### Data Ingestion Flow

```
1. Excel files placed in backend/data/raw/
   |
   v
2. Admin uploads via /admin/ingest endpoint
   |
   v
3. Validation layer (row_validators.py)
   - Column count validation
   - Required field presence
   - Numeric bounds checking
   - Email format validation
   |
   v
4. [Pass] -> Transform -> Star Schema DB
   [Fail] -> Quarantine -> Error Log
   |
   v
5. Feature Engineering (FeatureEngineer.calculate_all_features)
   |
   v
6. Risk Scoring (RiskScorer.calculate_risk_score)
   |
   v
7. Prediction stored in predictions table
```

### Risk Scoring Flow

```
1. Scheduler triggers at 03:00 UTC daily
   |
   v
2. FeatureEngineer calculates 7 signal scores:
   - content_completion_score (30%)
   - login_consistency_score (20%)
   - quiz_engagement_score (20%)
   - assignment_score (15%)
   - time_investment_score (8%)
   - discussion_engagement_score (2%)
   - self_directed_learning_score (5%, inverted)
   |
   v
3. RiskScorer computes weighted engagement
   |
   v
4. Base risk = 100 - weighted_engagement
   |
   v
5. Calendar adjustment applied (40% weight)
   |
   v
6. Academic flags override (dropout_intent, ufm_flagged, etc.)
   |
   v
7. Final score stored (0-100 scale, 1 decimal)
   |
   v
8. PredictionLog entry created for audit
```

### Intervention Decision Flow

```
1. Risk score retrieved for student
   |
   v
2. Check ghost student flags -> activation outreach
   |
   v
3. Check academic flags:
   - dropout_intent -> retention emergency
   - ufm_flagged -> academic integrity
   - health_support_needed -> welfare referral
   |
   v
4. Pattern-based routing:
   - "struggling" -> academic support
   - "disengaged" -> re-engagement campaign
   |
   v
5. Threshold-based intervention:
   - < 30: No action
   - 30-40: Gentle reminder
   - 40-60: Mentor outreach
   - 60-80: Escalated mentor
   - 80+: Urgent intervention
   |
   v
6. Intervention record created
   |
   v
7. Assigned to faculty/sales team queue
```

### Authentication Flow

```
1. User submits credentials to /auth/login
   |
   v
2. Server validates against hashed_password (bcrypt)
   |
   v
3. JWT access token created (15-60 min expiry)
   - Claims: sub, role, exp, iat, iss, aud, jti, nbf
   |
   v
4. Refresh token created (7 day expiry)
   |
   v
5. Refresh token stored in httpOnly cookie
   |
   v
6. Access token returned to client (memory storage)
   |
   v
7. Client attaches Authorization header to requests
   |
   v
8. On 401, client calls /auth/refresh
   |
   v
9. New access token issued, cookie rotated
```

## Database Schema

### Core Tables

#### students
```sql
CREATE TABLE students (
    id VARCHAR PRIMARY KEY,              -- Email address
    org_defined_id VARCHAR UNIQUE,       -- BITS ID (e.g., 2025EB110001)
    first_name VARCHAR,
    last_name VARCHAR,
    old_new_student VARCHAR,             -- 'old' or 'new'
    is_active BOOLEAN DEFAULT TRUE,
    parent_department_name VARCHAR,
    parent_department_code VARCHAR,
    deactivated_at DATETIME,
    deactivation_reason VARCHAR(128)
);
```

#### users
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR NOT NULL,               -- student, faculty, admin, retention team
    department VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT NOW(),
    preferences JSON
);
```

#### predictions
```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY,
    student_id VARCHAR NOT NULL REFERENCES students(id),
    risk_score FLOAT NOT NULL,           -- 0-100 scale
    engagement_score FLOAT NOT NULL,     -- 0-1 scale
    retention_likelihood VARCHAR,        -- high, medium, low
    attendance FLOAT,
    assignments FLOAT,
    grades FLOAT,
    academic_signal_score FLOAT,
    engagement_signal_score FLOAT,
    consistency_signal_score FLOAT,
    intent_signal_score FLOAT,
    responsiveness_signal_score FLOAT,
    model_version VARCHAR,
    prediction_timestamp DATETIME NOT NULL,
    top_risk_factors VARCHAR
);
```

#### risk_snapshots
```sql
CREATE TABLE risk_snapshots (
    id INTEGER PRIMARY KEY,
    student_id VARCHAR NOT NULL REFERENCES students(id),
    risk_score FLOAT NOT NULL,
    engagement_score FLOAT,
    week_number INTEGER,
    semester_name VARCHAR,
    timestamp DATETIME
);
```

#### interventions
```sql
CREATE TABLE interventions (
    id INTEGER PRIMARY KEY,
    student_org_id VARCHAR NOT NULL,
    intervention_type VARCHAR,
    priority VARCHAR,
    status VARCHAR,
    assigned_faculty_id INTEGER,
    notes TEXT,
    created_at DATETIME,
    completed_at DATETIME
);
```

#### intervention_logs
```sql
CREATE TABLE intervention_logs (
    id INTEGER PRIMARY KEY,
    student_org_id VARCHAR NOT NULL,
    intervention_id INTEGER,
    action_type VARCHAR,
    channel VARCHAR,
    outcome VARCHAR,
    recommended_at DATETIME,
    completed_at DATETIME,
    ai_reasoning TEXT
);
```

#### audit_logs
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    user_role VARCHAR,
    action_type VARCHAR,                 -- READ, WRITE, DELETE
    resource_type VARCHAR,
    resource_id VARCHAR,
    ip_address VARCHAR,
    request_id VARCHAR,
    timestamp DATETIME,
    details JSON
);
```

### Star Schema Tables

#### dim_student
```sql
CREATE TABLE dim_student (
    student_key INTEGER PRIMARY KEY,
    student_id VARCHAR UNIQUE,
    org_defined_id VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    department VARCHAR,
    is_active BOOLEAN,
    effective_from DATETIME,
    effective_to DATETIME
);
```

#### fact_engagement
```sql
CREATE TABLE fact_engagement (
    fact_key INTEGER PRIMARY KEY,
    student_key INTEGER,
    course_key INTEGER,
    date_key INTEGER,
    login_count INTEGER,
    content_views INTEGER,
    time_spent_seconds INTEGER,
    discussion_posts INTEGER,
    quiz_attempts INTEGER
);
```

#### fact_academic_performance
```sql
CREATE TABLE fact_academic_performance (
    fact_key INTEGER PRIMARY KEY,
    student_key INTEGER,
    course_key INTEGER,
    date_key INTEGER,
    component_type VARCHAR,
    score FLOAT,
    max_score FLOAT,
    submission_status VARCHAR
);
```

### Indexes

```sql
-- Student queries
CREATE INDEX ix_student_department ON students(parent_department_name);
CREATE INDEX ix_student_org_id ON students(org_defined_id);
CREATE INDEX ix_student_is_active ON students(is_active);
CREATE INDEX ix_student_dept_active ON students(parent_department_name, is_active);

-- Prediction queries
CREATE INDEX ix_prediction_student ON predictions(student_id);
CREATE INDEX ix_prediction_risk_score ON predictions(risk_score);
CREATE INDEX ix_prediction_timestamp ON predictions(prediction_timestamp);

-- Risk snapshots
CREATE INDEX ix_risk_snapshot_student ON risk_snapshots(student_id);
CREATE INDEX ix_risk_snapshot_week ON risk_snapshots(week_number);

-- Audit logs
CREATE INDEX ix_audit_user ON audit_logs(user_id);
CREATE INDEX ix_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX ix_audit_timestamp ON audit_logs(timestamp);
```

## Testing

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest backend/tests -v

# Run specific test file
pytest backend/tests/test_auth.py -v

# Run with coverage
pytest backend/tests --cov=backend --cov-report=html

# Run security tests
pytest backend/tests/test_encoding_bypasses.py -v
pytest backend/tests/test_security_headers.py -v
```

### Test Structure

```
backend/tests/
├── conftest.py              # Pytest fixtures, test DB setup
├── test_auth.py             # Authentication, token validation
├── test_idor.py             # IDOR vulnerability tests
├── test_encoding_bypasses.py # Input sanitization tests
├── test_security_headers.py # Security header validation
├── test_risk_scoring.py     # Risk score calculation
├── test_integration_api.py  # End-to-end API tests
├── test_scheduler.py        # Background job tests
├── test_monitoring.py       # Health check tests
└── features/                # Feature extractor tests
    ├── test_academic_extractor.py
    ├── test_engagement_extractor.py
    ├── test_consistency_extractor.py
    └── test_intent_extractor.py
```

### Test Configuration

- **Database**: In-memory SQLite for isolation
- **SECRET_KEY**: Test-specific value (`test-secret-key-not-for-production-x7f9k2m`)
- **TESTING=true**: Enables test mode in config
- **INTEGRATION_API_KEY_HASH**: Pre-configured for integration tests

### Coverage Notes

As of current implementation:
- Authentication: Full coverage
- Risk scoring: Full coverage
- Input sanitization: Full coverage
- API integration: Partial coverage
- LLM features: Limited coverage (requires API keys)

### Missing Tests

- End-to-end frontend tests
- Load testing for concurrent users
- Chaos engineering tests (Redis failure, DB failure)

## Deployment

### Production Deployment Steps

1. **Prepare Environment**:
   ```bash
   # Set production environment variables
   export ENVIRONMENT=production
   export SECRET_KEY=<generate-secure-key>
   export DATABASE_URL=postgresql://user:pass@host/db
   export REDIS_URL=redis://redis-host:6379/0
   export CORS_ORIGINS=https://your-domain.com
   ```

2. **Database Migration**:
   ```bash
   alembic upgrade head
   ```

3. **Start Services**:
   ```bash
   # Using docker-compose
   cd docker
   docker-compose up -d

   # Or directly
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

### Docker Deployment

**Build Images**:
```bash
cd docker
docker-compose build
```

**Run Stack**:
```bash
docker-compose up -d
```

**View Logs**:
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

### CI/CD

No CI/CD pipeline currently configured. Recommended setup:

1. **GitHub Actions** for:
   - Run tests on PR
   - Build Docker images on merge
   - Deploy to staging/production

2. **Pre-deployment Checks**:
   - Security scan (bandit, safety)
   - Dependency audit (pip-audit)
   - Database migration dry-run

### Environment Separation

| Environment | Database | Redis | LLM | Purpose |
|-------------|----------|-------|-----|---------|
| Development | SQLite (local) | localhost:6379 | Optional | Local development |
| Staging | PostgreSQL | Staging Redis | Test keys | QA testing |
| Production | PostgreSQL (HA) | Redis Cluster | Production keys | Live users |

### Scaling Considerations

**Current Limitations**:
- Single-process design (async lock for prediction jobs)
- SQLite not suitable for concurrent writes
- No horizontal scaling for backend

**Recommendations**:
- Use PostgreSQL for production
- Deploy behind load balancer with sticky sessions
- Redis cluster for distributed rate limiting
- Consider Celery for background job distribution

## Logging and Monitoring

### Logging System

**Logger**: Python logging with structured output

**Log File**: `backend/backend.log` (configurable via `LOG_FILE`)

**Log Levels**:
- `DEBUG` — Detailed debugging information
- `INFO` — General operational messages
- `WARNING` — Warning conditions (non-blocking)
- `ERROR` — Error conditions (blocking)
- `CRITICAL` — Critical failures (service impact)

### Log Format

```json
{
  "timestamp": "2026-04-14T10:30:00Z",
  "level": "INFO",
  "message": "Request completed: GET /students - Status: 200",
  "request_id": "abc-123-def",
  "user_id": 5,
  "duration_ms": 45
}
```

### PII Masking

All logs automatically mask sensitive data:
- Email addresses: `stu***@ex***.com`
- Student IDs: `STU***789`
- JWT tokens: `[REDACTED_JWT]`
- Phone numbers: `[REDACTED_PHONE]`

### Error Tracking

**Current**: File-based logging only

**Recommended**:
- Sentry integration for error aggregation
- Alerting on ERROR/CRITICAL logs
- Dashboard for error rates

### Observability

**Health Endpoints**:
- `GET /health` — Overall system health
- `GET /api/v1/monitoring/scheduler` — Scheduler status

**Metrics to Monitor**:
- Request latency (p95, p99)
- Error rate by endpoint
- Redis connection pool usage
- Database query latency
- Prediction job duration

## Security Considerations

### Authentication

**Method**: JWT (JSON Web Tokens) with bcrypt password hashing

**Token Structure**:
- Access token: 15-60 minute expiry, stored in memory
- Refresh token: 7 day expiry, httpOnly cookie
- Claims: sub, role, exp, iat, iss, aud, jti, nbf

**Security Features**:
- Token revocation blocklist (RevokedToken table)
- Automatic token rotation on refresh
- Signature validation with SECRET_KEY
- Audience and issuer validation

### Authorization

**Method**: Role-Based Access Control (RBAC)

**Roles**:
- `student` — Own data only
- `faculty` — All student data, interventions
- `admin` — Full system access, user management
- `retention team` — Intervention management, analytics

**Superuser**: `is_superuser=True` bypasses all role checks

### Input Validation

**Layers**:
1. **Pydantic schemas** — Type validation, field constraints
2. **SecurityManager.sanitize_input()** — HTML sanitization with bleach
3. **Encoding detection** — URL, Unicode, HTML entity decoding
4. **Control character stripping** — Null bytes, newlines
5. **Prompt injection detection** — LLM-specific patterns

**Validators**:
- GPA: 0.0-4.0 range
- Attendance: 0-100 range
- Student ID: Alphanumeric, 4-20 chars, regex `^[A-Za-z0-9_-]{4,20}$`

### Rate Limiting

**Implementation**: SlowAPI with Redis backend

**Limits**:
| Endpoint | Limit | Window |
|----------|-------|--------|
| Login | 5 | per minute |
| Data Ingestion | 10 | per hour |
| LLM (per user) | 5 | per minute |
| LLM (per user) | 20 | per hour |
| Default | 200 | per minute |

**Response on Limit**:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: application/json

{
  "detail": "Rate limit exceeded",
  "retry_after": 60
}
```

### Secrets Management

**Storage**: Environment variables only (never in code)

**Generation**:
```bash
# Secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Integration API key hash
python -c "import hashlib; print(hashlib.sha256(b'your-key').hexdigest())"
```

**Validation**: Startup validation rejects weak/placeholder values in production

### Known Vulnerabilities

**Addressed**:
- XSS: Content Security Policy, input sanitization
- CSRF: JWT tokens, httpOnly cookies
- IDOR: Resource ownership checker, role-based access
- SQL Injection: SQLAlchemy ORM with parameterized queries
- Prompt Injection: LLM input sanitization, guardrails

**Under Review**:
- Multi-worker deployment requires distributed lock (ARCH-2)
- Token cleanup job needed for revoked_tokens table growth

## Performance Considerations

### Bottlenecks

1. **SQLite Concurrency**: Single-writer limitation
   - Mitigation: Use PostgreSQL in production

2. **Prediction Job Lock**: Async lock prevents overlapping runs
   - Impact: Single-worker deployment only
   - Fix: Redis distributed lock for multi-worker

3. **LLM API Latency**: 30-second timeout
   - Mitigation: Caching, fallback responses

### Caching

**Redis Cache**:
- Rate limit counters
- LLM response cache (TTL: 300 seconds)
- Feature computation cache (planned)

### Optimization Strategies

**Database**:
- Keyset pagination (O(n) vs O(n^2))
- Composite indexes for common queries
- Connection pooling (SQLAlchemy)

**Application**:
- Async endpoints for I/O-bound operations
- Batch processing for bulk operations
- Lazy loading for relationships

### Scalability Notes

**Current Capacity**:
- ~1000 students per instance
- ~100 concurrent users
- Daily prediction generation: 5-10 minutes for 500 students

**Scaling Path**:
1. PostgreSQL with read replicas
2. Redis cluster for distributed caching
3. Celery for background job distribution
4. Horizontal backend scaling behind load balancer

## Limitations

### Technical Limitations

1. **ML Model**: Rule-based scoring only (no trained ML model)
   - XGBoost training pipeline not implemented
   - Weights manually configured

2. **Data Ingestion**: File-based only (no LMS API integration)
   - Requires manual Excel uploads
   - No real-time sync

3. **Single-Process Design**: Async lock for prediction jobs
   - Multi-worker deployment requires Redis distributed lock

4. **SQLite Default**: Not suitable for production concurrency
   - PostgreSQL migration required for scale

### Functional Limitations

1. **Intervention Tracking**: Manual outcome logging
   - No automated follow-up scheduling
   - No communication integration (email, WhatsApp)

2. **Student Portal**: Limited functionality
   - Read-only access to risk data
   - No self-service intervention requests

3. **Reporting**: Basic PDF generation
   - No scheduled report delivery
   - Limited export formats

### Known Issues

- Ghost student detection relies on zero engagement threshold
- Calendar risk scorer may produce edge cases at trimester boundaries
- LLM features require manual API key configuration

## Roadmap

### Phase 1: Core Improvements

- [ ] PostgreSQL migration guide
- [ ] Multi-worker deployment with Redis distributed locks
- [ ] LMS API integration (Canvas, Moodle, Blackboard)
- [ ] Automated email interventions

### Phase 2: ML Enhancement

- [ ] XGBoost training pipeline
- [ ] Model versioning and A/B testing
- [ ] Feature importance tracking
- [ ] Automated model retraining

### Phase 3: Advanced Features

- [ ] Student self-service portal
- [ ] Communication platform integration
- [ ] Early alert system for faculty
- [ ] Retention campaign management

### Phase 4: Enterprise Features

- [ ] Multi-tenancy support
- [ ] SSO integration (SAML, OIDC)
- [ ] Advanced analytics (cohort segmentation)
- [ ] API rate limiting per organization

## Troubleshooting

### Common Errors

#### "Redis is not reachable"

**Cause**: Redis service not running or incorrect `REDIS_URL`

**Fix**:
```bash
# Check Redis status
redis-cli ping  # Should return PONG

# Start Redis
redis-server

# Or with Docker
docker run -d -p 6379:6379 redis:7-alpine
```

#### "DATABASE_URL environment variable is required"

**Cause**: Missing database configuration

**Fix**:
```bash
# Add to .env
DATABASE_URL=sqlite:///./backend/data/sql_app.db

# Or for PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost:5432/ews_db
```

#### "SECRET_KEY environment variable is not set"

**Cause**: Missing or weak secret key

**Fix**:
```bash
# Generate secure key
python -c "import secrets; print(secrets.token_hex(32))"

# Add to .env (min 32 characters)
SECRET_KEY=<generated-key>
```

#### "Token has been revoked"

**Cause**: User logged out, token added to blocklist

**Fix**: Re-authenticate by logging in again

#### "Rate limit exceeded"

**Cause**: Too many requests in time window

**Fix**: Wait for retry period or increase limits in config

#### "Student not found" (404)

**Cause**: Student ID not in database or IDOR protection

**Fix**: Verify student exists and user has access permissions

### Database Issues

#### "database is locked" (SQLite)

**Cause**: Concurrent write attempts

**Fix**:
- Reduce concurrent writes
- Migrate to PostgreSQL
- Increase timeout in connection string

#### Migration failures

**Cause**: Schema drift or incomplete migrations

**Fix**:
```bash
# Check current version
alembic current

# Upgrade to latest
alembic upgrade head

# If stuck, reset (development only)
alembic downgrade base
alembic upgrade head
```

### Frontend Issues

#### "Network Error" in browser console

**Cause**: Backend not running or CORS misconfiguration

**Fix**:
```bash
# Start backend
python -m uvicorn backend.main:app --reload

# Check CORS_ORIGINS in .env
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

#### Blank page after build

**Cause**: Incorrect `REACT_APP_API_URL` or missing environment

**Fix**:
```bash
# Set correct API URL
export REACT_APP_API_URL=http://your-backend:8000/api/v1

# Rebuild
npm run build
```

## Contributing

### Code Style

**Python**:
- Follow PEP 8
- Type hints required for function signatures
- Docstrings for public APIs
- Maximum line length: 100 characters

**JavaScript/React**:
- ESLint rules in `frontend/package.json`
- Functional components with hooks
- PropTypes or TypeScript for type safety

### Branching Strategy

```
main          # Production-ready code
  ├── develop         # Integration branch
  │     ├── feature/* # New features
  │     ├── bugfix/*  # Bug fixes
  │     └── hotfix/*  # Production hotfixes
```

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build/config changes

**Example**:
```
feat(risk-scoring): add calendar-aware risk adjustment

- Implement calendar_scorer module
- Blend feature-based and calendar-based scores
- Add CALENDAR_RISK_BLEND_WEIGHT config

Fixes: #123
```

### Pull Request Process

1. Create feature branch from `develop`
2. Implement changes with tests
3. Run test suite: `pytest backend/tests -v`
4. Update documentation
5. Submit PR to `develop`
6. Address review comments
7. Merge after approval

### Security Review

All PRs must pass:
- Encoding bypass tests
- Security header tests
- IDOR vulnerability tests
- Input validation tests

## License

Proprietary software. All rights reserved.
