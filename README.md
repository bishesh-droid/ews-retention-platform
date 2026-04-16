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
- [System Design Principles](#system-design-principles)
- [Dependency Overview](#dependency-overview)
- [API Versioning Strategy](#api-versioning-strategy)
- [Error Handling Strategy](#error-handling-strategy)
- [Background Job Lifecycle](#background-job-lifecycle)
- [LLM Fallback Strategy](#llm-fallback-strategy)
- [Caching Strategy Details](#caching-strategy-details)
- [Concurrency Model](#concurrency-model)
- [Database Transaction Strategy](#database-transaction-strategy)
- [Data Consistency Guarantees](#data-consistency-guarantees)
- [Failure Recovery Strategy](#failure-recovery-strategy)
- [Observability and Metrics Strategy](#observability-and-metrics-strategy)
- [Alerting Strategy](#alerting-strategy)
- [Health Check Internals](#health-check-internals)
- [CI/CD Pipeline](#cicd-pipeline)
- [Known Technical Debt](#known-technical-debt)
- [Operational Runbook](#operational-runbook)
- [Developer Onboarding Guide](#developer-onboarding-guide)
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
- Multi-role authentication with JWT (15-min access tokens), Refresh Token Rotation (RTR), Redis-backed revocation, and httpOnly SameSite=Strict refresh cookies scoped to the refresh endpoint
- FERPA-compliant audit logging covering all student data access and AI-generated disclosures
- LLM provider fallback chain (Gemini → Claude → deterministic template) for high availability

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
                          |   (Rate Limit /  |
                          |   Token Revoke)  |
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
- Redis-first token revocation with SQLite fallback for high-throughput auth checks
- Waterfall LLM fallback strategy: Gemini → Claude → rule-based template

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

> **Note**: Alembic schema version is verified at startup — server will refuse to start if migrations are not at HEAD.

### Integration Points

**External Services**:
- Google Gemini API (LLM features)
- Anthropic Claude API (LLM features)
- Redis (distributed rate limiting, token revocation, caching)

**Data Ingestion**:
- Excel file uploads (.xlsx) via admin interface
- Scheduled ingestion from `backend/data/` directory
- Row-level validation with quarantine for failed records

### External Services

| Service | Purpose | Required |
|---------|---------|----------|
| Redis | Rate limiting, token revocation, distributed caching | Yes (production) |
| Google Gemini | LLM explanations, suggestions | Optional |
| Anthropic Claude | Alternative LLM provider | Optional |

## Visual Architecture & System Working (Diagrammatic View)

### System Architecture

```mermaid
flowchart TD
    subgraph External["External Services"]
        Gemini["Google Gemini API"]
        Claude["Anthropic Claude API"]
    end

    subgraph Frontend["Frontend Layer"]
        React["React SPA (Port 3000)"]
        AuthContext["AuthContext (JWT State)"]
        StudentContext["StudentContext (Data State)"]
        Axios["Axios Interceptors"]
    end

    subgraph Backend["Backend Layer - FastAPI (Port 8000)"]
        subgraph Routes["Routes Layer"]
            Auth["auth.py"]
            StudentV1["student_v1.py"]
            FacultyV1["faculty_v1.py"]
            AdminV1["admin_v1.py"]
            MLRoutes["ml_routes.py"]
            Interventions["interventions.py"]
            Decisions["decisions.py"]
            Business["business.py"]
            Analytics["analytics.py"]
        end

        subgraph Services["Services Layer"]
            RiskScorer["risk_scoring.py"]
            FeatureEngineer["feature_engineering.py"]
            CalendarScorer["calendar_scorer.py"]
            DecisionEngine["decision_engine.py"]
            MLService["ml_service.py"]
            AnalyticsService["analytics_service.py"]
        end

        subgraph AIServices["AI Services (services/ai/)"]
            LLMOrchestrator["llm_orchestrator.py"]
            RAGEngine["rag_engine.py"]
            HallucinationGuard["hallucination_guard.py"]
        end

        subgraph Infrastructure["Infrastructure Services"]
            Scheduler["scheduler.py"]
            TokenCleanup["token_cleanup.py"]
            Recommender["recommender.py"]
        end

        subgraph Core["Core Modules"]
            JWTAuth["auth.py (JWT)"]
            Security["security.py"]
            RateLimit["rate_limiting.py"]
            AuditLogger["audit_logger.py"]
        end

        subgraph Middleware["Middleware"]
            SecurityHeaders["security_headers.py"]
            RequestValidation["request_validation.py"]
            AuditMiddleware["security_logging.py"]
        end
    end

    subgraph DataLayer["Data Layer"]
        SQLite[("SQLite / PostgreSQL")]
        Redis[("Redis (Rate Limit / Token Revocation)")]
    end

    subgraph DataIngestion["Data Ingestion Pipeline"]
        MasterBuilder["master_builder.py"]
        Loader["loader.py"]
        Validator["validator.py"]
        Normalizer["normalizer.py"]
        SchemaMapper["schema_mapper.py"]
    end

    React --> Axios
    Axios --> AuthContext
    Axios --> StudentContext
    Axios --> Auth
    Axios --> StudentV1
    Axios --> FacultyV1
    Axios --> AdminV1
    Axios --> MLRoutes
    Axios --> Interventions
    Axios --> Business
    Axios --> Analytics

    Auth --> JWTAuth
    StudentV1 --> RiskScorer
    FacultyV1 --> RiskScorer
    MLRoutes --> MLService
    Interventions --> DecisionEngine
    Decisions --> DecisionEngine
    Business --> AnalyticsService
    Analytics --> AnalyticsService

    RiskScorer --> FeatureEngineer
    RiskScorer --> CalendarScorer
    MLService --> FeatureEngineer
    DecisionEngine --> LLMOrchestrator

    LLMOrchestrator --> Gemini
    LLMOrchestrator --> Claude
    LLMOrchestrator --> HallucinationGuard
    LLMOrchestrator --> RAGEngine

    Scheduler --> RiskScorer
    Scheduler --> MLService
    Scheduler --> TokenCleanup

    Routes --> Middleware
    Middleware --> Core
    Routes --> SQLite
    Core --> SQLite
    Core --> Redis
    Services --> SQLite
    AIServices --> SQLite

    MasterBuilder --> Loader
    Loader --> Validator
    Validator --> Normalizer
    Normalizer --> SchemaMapper
    SchemaMapper --> SQLite
```

### Runtime Working Flow

```mermaid
flowchart TD
    subgraph AuthFlow["Authentication Flow"]
        User["User"] --> Login["POST /auth/login"]
        Login --> ValidateCreds["Validate Credentials (bcrypt)"]
        ValidateCreds --> CreateJWT["Create JWT Access Token (15 min)"]
        CreateJWT --> CreateRefresh["Create Refresh Token (httpOnly, Secure, SameSite=Strict, path=/api/v1/auth/refresh)"]
        CreateRefresh --> ReturnToken["Return Access Token"]
    end

    subgraph RequestCycle["Authenticated Request Cycle"]
        Client["Client"] --> AttachHeader["Attach Authorization Header"]
        AttachHeader --> ValidateJWT["JWT Validation Middleware"]
        ValidateJWT --> CheckRevoked["Check Redis Revocation / RevokedToken Fallback"]
        CheckRevoked --> RBAC["RBAC Authorization Check"]
        RBAC --> AuditLog["Audit Logger (FERPA)"]
        AuditLog --> ProcessRequest["Process Request"]
    end

    subgraph RiskPipeline["Risk Scoring Pipeline"]
        Trigger["Scheduler Trigger (03:00 UTC)"]
        Trigger --> LoadFeatures["Load Student Features"]
        LoadFeatures --> CalcContent["content_completion_score (30%)"]
        LoadFeatures --> CalcLogin["login_consistency_score (20%)"]
        LoadFeatures --> CalcQuiz["quiz_engagement_score (20%)"]
        LoadFeatures --> CalcAssignment["assignment_score (15%)"]
        LoadFeatures --> CalcTime["time_investment_score (8%)"]
        LoadFeatures --> CalcDiscussion["discussion_engagement_score (2%)"]
        LoadFeatures --> CalcSelf["self_directed_learning_score (5%)"]
        CalcContent --> WeightedSum["Compute Weighted Engagement"]
        CalcLogin --> WeightedSum
        CalcQuiz --> WeightedSum
        CalcAssignment --> WeightedSum
        CalcTime --> WeightedSum
        CalcDiscussion --> WeightedSum
        CalcSelf --> WeightedSum
        WeightedSum --> BaseRisk["Base Risk = 100 - weighted_engagement"]
        BaseRisk --> CalendarAdj["Calendar Adjustment (40% blend)"]
        CalendarAdj --> AcademicFlags["Academic Flags Override"]
        AcademicFlags --> StorePrediction["Store in predictions table"]
        StorePrediction --> LogPrediction["Write to prediction_log"]
    end

    subgraph InterventionFlow["Intervention Decision Engine"]
        GetRisk["Get Risk Score"] --> CheckGhost["Check Ghost Student Flags"]
        CheckGhost --> CheckAcademic["Check Academic Flags"]
        CheckAcademic --> PatternRoute["Pattern-Based Routing"]
        PatternRoute --> ThresholdCheck["Threshold Check"]
        ThresholdCheck --> NoAction["< 30: No Action"]
        ThresholdCheck --> Gentle["30-40: Gentle Reminder"]
        ThresholdCheck --> Mentor["40-60: Mentor Outreach"]
        ThresholdCheck --> Escalated["60-80: Escalated Mentor"]
        ThresholdCheck --> Urgent["80+: Urgent Intervention"]
        Gentle --> CreateIntervention["Create Intervention Record"]
        Mentor --> CreateIntervention
        Escalated --> CreateIntervention
        Urgent --> CreateIntervention
        CreateIntervention --> AssignQueue["Assign to Faculty/Sales Queue"]
    end

    subgraph SchedulerCycle["Scheduler-Triggered Prediction Cycle"]
        DailyTrigger["APScheduler Daily Trigger"] --> AcquireLock["Acquire Async Lock"]
        AcquireLock --> LoadStudents["Load All Active Students"]
        LoadStudents --> BatchProcess["Batch Process (feature extraction)"]
        BatchProcess --> ScoreBatch["Score Batch (risk_scoring.py)"]
        ScoreBatch --> PersistBatch["Persist to Database"]
        PersistBatch --> UpdateSnapshots["Update Risk Snapshots"]
        UpdateSnapshots --> ReleaseLock["Release Lock"]
        ReleaseLock --> LogCompletion["Log Completion to audit_logs"]
    end

    subgraph AuditLogging["Audit Logging Flow"]
        AnyAction["Any Data Access"] --> AuditMiddleware["Audit Middleware"]
        AuditMiddleware --> MaskPII["Mask PII (email, student_id)"]
        MaskPII --> WriteAudit["Write to audit_logs table"]
        WriteAudit --> IncludeMetadata["Include: user_id, action, resource_type, timestamp, request_id"]
    end

    ReturnToken --> Client
    ProcessRequest --> GetRisk
    LogPrediction --> AnyAction
    AssignQueue --> AnyAction
    LogCompletion --> AuditLogging
```

### Data Flow

```mermaid
flowchart LR
    subgraph Input["Data Input"]
        ExcelFiles["Excel Files (.xlsx)"]
        RawDir["backend/data/raw/"]
    end

    subgraph Upload["Upload Process"]
        AdminUpload["Admin Upload /admin/ingest"]
        Multipart["Multipart Form Data"]
    end

    subgraph Validation["Validation Layer"]
        RowValidator["row_validators.py"]
        ColumnCount["Column Count Check"]
        RequiredFields["Required Field Presence"]
        NumericBounds["Numeric Bounds Checking"]
        EmailFormat["Email Format Validation"]
    end

    subgraph Quarantine["Quarantine Path"]
        ValidationFail["Validation Failed"]
        QuarantineDir["backend/data/quarantine/"]
        ErrorLog["Error Log Entry"]
    end

    subgraph Transform["Transformation"]
        SchemaMapper["schema_mapper.py"]
        ColumnNorm["Column Name Normalization"]
        DataTypeNorm["Data Type Normalization"]
        MasterBuilder["master_builder.py"]
    end

    subgraph StarSchema["Star Schema Load"]
        DimStudent["dim_student"]
        DimCourse["dim_course"]
        FactEngagement["fact_engagement"]
        FactAcademic["fact_academic_performance"]
        FactConsistency["fact_consistency"]
        FactIntent["fact_intent_responsiveness"]
    end

    subgraph FeatureEng["Feature Engineering"]
        AcademicExtractor["features/academic.py"]
        EngagementExtractor["features/engagement.py"]
        ConsistencyExtractor["features/consistency.py"]
        IntentExtractor["features/intent.py"]
        FeatureComposer["features/composer.py"]
    end

    subgraph Calculation["Risk Calculation"]
        RiskScorer["risk_scoring.py"]
        WeightedCalc["Weighted Signal Calculation"]
        CalendarAdj["calendar_scorer.py"]
        FinalRisk["Final Risk Score (0-100)"]
    end

    subgraph Persistence["Prediction Persistence"]
        PredictionsTable["predictions table"]
        RiskSnapshots["risk_snapshots table"]
        PredictionLog["prediction_log table"]
    end

    ExcelFiles --> RawDir
    RawDir --> AdminUpload
    AdminUpload --> Multipart
    Multipart --> RowValidator
    RowValidator --> ColumnCount
    ColumnCount --> RequiredFields
    RequiredFields --> NumericBounds
    NumericBounds --> EmailFormat

    EmailFormat -->|Pass| SchemaMapper
    EmailFormat -->|Fail| ValidationFail
    ValidationFail --> QuarantineDir
    ValidationFail --> ErrorLog

    SchemaMapper --> ColumnNorm
    ColumnNorm --> DataTypeNorm
    DataTypeNorm --> MasterBuilder
    MasterBuilder --> DimStudent
    MasterBuilder --> DimCourse
    MasterBuilder --> FactEngagement
    MasterBuilder --> FactAcademic
    MasterBuilder --> FactConsistency
    MasterBuilder --> FactIntent

    FactEngagement --> EngagementExtractor
    FactAcademic --> AcademicExtractor
    FactConsistency --> ConsistencyExtractor
    FactIntent --> IntentExtractor

    EngagementExtractor --> FeatureComposer
    AcademicExtractor --> FeatureComposer
    ConsistencyExtractor --> FeatureComposer
    IntentExtractor --> FeatureComposer

    FeatureComposer --> RiskScorer
    RiskScorer --> WeightedCalc
    WeightedCalc --> CalendarAdj
    CalendarAdj --> FinalRisk

    FinalRisk --> PredictionsTable
    FinalRisk --> RiskSnapshots
    FinalRisk --> PredictionLog
```

### Deployment View

```mermaid
flowchart TD
    subgraph External["External Traffic"]
        Users["Users / Admins / Faculty"]
        Internet["Internet"]
    end

    subgraph ReverseProxy["Reverse Proxy Layer"]
        Nginx["nginx Load Balancer"]
        SSL["SSL Termination"]
    end

    subgraph DockerNetwork["Docker Network: ews-network"]
        subgraph FrontendContainer["Frontend Container"]
            ReactApp["React SPA (nginx:alpine)"]
            StaticFiles["Static Build Files"]
            NginxConf["nginx.conf"]
        end

        subgraph BackendContainer["Backend Container"]
            FastAPIApp["FastAPI Application (Python 3.12 slim)"]
            Uvicorn["Uvicorn Server (4 workers)"]
            MiddlewareStack["Middleware Stack"]
            RoutesLayer["Routes Layer"]
            ServicesLayer["Services Layer"]
        end

        subgraph SchedulerContainer["Scheduler Container"]
            APScheduler["APScheduler Service"]
            SchedulerScript["scheduler.py"]
            BackgroundJobs["Background Jobs"]
        end

        subgraph RedisContainer["Redis Container"]
            RedisServer["Redis 7 (alpine)"]
            RateLimitStore["Rate Limit Counters"]
            TokenRevocation["Token Revocation (RTR)"]
            LLMCache["LLM Response Cache"]
        end

        subgraph DatabaseContainer["Database Container (Production)"]
            Postgres["PostgreSQL 14"]
            DataVolume["Persistent Volume"]
        end
    end

    subgraph DataVolumeMount["Data Volumes"]
        SQLiteDev["SQLite (dev): ./backend/data/"]
        PostgresData["Postgres Data: postgres_data"]
        LogsVolume["Logs: ./logs/"]
    end

    Users --> Internet
    Internet --> Nginx
    Nginx --> SSL
    SSL --> ReactApp
    SSL --> Uvicorn

    ReactApp --> StaticFiles
    ReactApp --> NginxConf

    Uvicorn --> FastAPIApp
    FastAPIApp --> MiddlewareStack
    MiddlewareStack --> RoutesLayer
    RoutesLayer --> ServicesLayer

    FastAPIApp --> RedisServer
    FastAPIApp --> Postgres

    APScheduler --> SchedulerScript
    SchedulerScript --> BackgroundJobs
    BackgroundJobs --> Uvicorn

    RedisServer --> RateLimitStore
    RedisServer --> TokenRevocation
    RedisServer --> LLMCache

    Postgres --> DataVolume

    SQLiteDev -.->|Development| FastAPIApp
    PostgresData -.->|Production| Postgres
    LogsVolume -.->|All Containers| FastAPIApp
```

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

- `llm_orchestrator.py` — Unified LLM interface with waterfall fallback (Gemini → Claude → template)
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
| Redis | 7+ | Rate limiting and token revocation (production) |
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
| `REDIS_URL` | Redis connection URL — required in production for rate limiting and token revocation | `redis://localhost:6379/0` |
| `ENVIRONMENT` | Environment mode | `development` or `production` |

#### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Server bind address |
| `API_PORT` | `8000` | Server bind port |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | JWT access token lifetime in minutes (keep ≤15) |
| `TRUSTED_PROXY_IPS` | `` (empty) | Comma-separated IPs of trusted reverse proxies |
| `LLM_BUDGET_ALERT_USD_PER_WEEK` | `10.00` | Weekly LLM spend alert threshold |
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

**Redis** (required for rate limiting and token revocation):
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

Refresh access token using httpOnly cookie. Old refresh token JTI is revoked immediately (RTR).

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
3. JWT access token created (15-min expiry, configurable via ACCESS_TOKEN_EXPIRE_MINUTES)
   - Claims: sub, role, exp, iat, iss, aud, jti, nbf
   |
   v
4. Refresh token created (7 day expiry)
   |
   v
5. Refresh token stored in httpOnly, Secure, SameSite=Strict cookie
   scoped to path="/api/v1/auth/refresh" only
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
9. New access token issued, old refresh token JTI revoked in Redis (RTR), new cookie set
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
    top_risk_factors VARCHAR,
    UNIQUE (student_id, prediction_date)  -- prevents duplicate daily predictions
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
    -- Append-only: no UPDATE or DELETE permitted at the application layer
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

### Pre-Deployment Checklist

- [ ] `.env` not tracked by git (`git status` shows no `.env`)
- [ ] All secrets rotated and stored in secrets manager or CI secrets
- [ ] `alembic upgrade head` applied to production DB
- [ ] `ENVIRONMENT=production` set (triggers CORS HTTPS enforcement)
- [ ] `REDIS_URL` points to a live Redis instance
- [ ] `CORS_ORIGINS` contains only HTTPS origins (no localhost)
- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES=15` confirmed
- [ ] `TRUSTED_PROXY_IPS` set to the IP(s) of your reverse proxy/load balancer
- [ ] Docker image built from digest-pinned base image
- [ ] CI pipeline passing with all quality gates unblocked

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

### Authentication & Token Security

- Access tokens expire in 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh Token Rotation (RTR): old refresh token JTI is revoked immediately upon rotation
- Refresh token cookie is `httpOnly`, `Secure`, `SameSite=Strict`, scoped to `path="/api/v1/auth/refresh"` only
- Token revocation is Redis-backed with TTL-based expiry; SQLite serves as a cold fallback

### Role-Based Access Control

- Four roles: `student`, `faculty`, `retention_team`, `admin`
- All role checks are enforced at the FastAPI dependency layer, not inside route handlers
- Students are strictly scoped to their own data — IDOR protection verified at ownership checker level for every student-scoped endpoint

### FERPA Compliance

- Every endpoint that accesses or returns student PII writes to the `AuditLog` table
- AI-generated disclosures (LLM advice surfaced to students) are logged with model name, operation, and a prompt hash — no raw prompts or responses stored
- `AuditLog` is append-only — no UPDATE or DELETE operations are permitted at the application layer
- IP address logging is proxy-aware: `X-Forwarded-For` is only trusted from known proxy IPs (configured via `TRUSTED_PROXY_IPS`)

### Rate Limiting

- Redis-backed distributed rate limiting on all auth endpoints
- LLM endpoints have a separate rate limiter to control API cost
- Graceful degradation: if Redis is unreachable, rate limiting falls back to in-process TTLCache with reduced limits; service continues without crashing

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

### Input Validation & Injection Prevention

- All request inputs validated via Pydantic v2 schemas
- Student free-text fields are never interpolated directly into LLM prompts — structured prompt templates are used throughout `llm_orchestrator.py`
- Excel ingestion validates sheet names, column headers, and row-level data before writing; failed rows are quarantined with full error context

**Validators**:
- GPA: 0.0-4.0 range
- Attendance: 0-100 range
- Student ID: Alphanumeric, 4-20 chars, regex `^[A-Za-z0-9_-]{4,20}$`

### Secrets Management

- No secrets are stored in version-controlled files
- `.env` is in `.gitignore`; `.env.example` contains placeholders only
- All secrets loaded via environment variables using `pydantic-settings`
- Rotate any key immediately if it appears in git history:
  `git filter-repo --path .env --invert-paths`

Generate secure values:
```bash
# Secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Integration API key hash
python -c "import hashlib; print(hashlib.sha256(b'your-key').hexdigest())"
```

### CI Security Gates

- Bandit security scan (blocks on new HIGH/CRITICAL findings against `.bandit.baseline`)
- detect-secrets scan (blocks on new secret patterns against `.secrets.baseline`)
- mypy type checking (blocking)
- flake8 linting (blocking)

**Known Vulnerabilities Addressed**:
- XSS: Content Security Policy, input sanitization
- CSRF: JWT tokens, httpOnly SameSite=Strict cookies
- IDOR: Resource ownership checker, role-based access
- SQL Injection: SQLAlchemy ORM with parameterized queries
- Prompt Injection: LLM input sanitization, structured templates, guardrails

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
- Token revocation (RTR) with TTL-based expiry
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

### Completed

- [x] JWT with RTR and Redis revocation
- [x] FERPA audit logging with AI disclosure trail
- [x] LLM waterfall fallback chain (Gemini → Claude → template)
- [x] Alembic startup schema verification
- [x] CI security gates (Bandit, detect-secrets, mypy — all blocking)
- [x] Unique constraint on Prediction(student_id, prediction_date)
- [x] Calendar scorer dynamic week cap

### In Progress

- [ ] Bulk import validation UI (preview → confirm flow)
- [ ] Frontend chart library consolidation (Chart.js → Recharts)
- [ ] PostgreSQL migration documentation

### Planned

- [ ] Webhook / email notification system for faculty risk threshold alerts (E-1)
- [ ] Automated intervention outcome tracking with effectiveness scoring (E-2)
- [ ] Model drift detection with PSI-based weekly snapshots (E-4)
- [ ] Student FERPA data export endpoint (E-5)
- [ ] LLM cost tracking dashboard with budget alerts (E-9)
- [ ] Multi-tenancy foundations (E-6)
- [ ] Redis graceful degradation with circuit breaker (E-8)

## System Design Principles

### Core Principles

**1. Separation of Concerns**
- Routes handle HTTP concerns only (validation, serialization, status codes)
- Services contain business logic (risk scoring, feature engineering)
- Core modules provide cross-cutting concerns (auth, security, logging)
- Middleware processes requests uniformly before reaching routes

**2. Defense in Depth**
- Input validation at multiple layers (Pydantic, middleware, service layer)
- Authentication at route level, authorization at service level
- Rate limiting at middleware, resource quotas at service level
- Audit logging for all data access regardless of role

**3. Fail Secure**
- Authentication failures default to denied access
- Rate limit exceeded returns 429 without leaking system state
- Database errors return generic messages (details logged server-side)
- LLM service failures fall back to rule-based responses

**4. Least Privilege**
- RBAC with four distinct roles (student, faculty, admin, retention_team)
- Token scope limited to specific claims (sub, role, exp)
- Database connections use minimal required permissions
- Service accounts isolated from user authentication flow

**5. Observability by Design**
- Request ID propagation through all layers
- Structured logging with consistent field naming
- PII masking at logging boundary (not scattered through code)
- Health checks expose internal state without exposing sensitive data

### Architectural Boundaries

| Layer | Responsibility | Forbidden Operations |
|-------|---------------|---------------------|
| Routes | HTTP handling, input validation | Direct database queries |
| Services | Business logic, orchestration | HTTP-specific operations |
| Core | Cross-cutting utilities | Business rule enforcement |
| Middleware | Request/response processing | Database state changes |
| Database | Persistence, constraints | Business calculations |

## Dependency Overview

### Python Dependencies

**Core Framework (Web)**
- `fastapi==0.119.0` — ASGI web framework
- `uvicorn==0.38.0` — ASGI server
- `starlette==0.48.0` — ASGI toolkit (FastAPI dependency)
- `python-multipart==0.0.22` — Form/multipart parsing

**Database**
- `SQLAlchemy==2.0.45` — ORM and SQL toolkit
- `alembic==1.18.4` — Database migrations
- `psycopg2-binary>=2.9` — PostgreSQL adapter
- `asyncpg>=0.29.0` — Async PostgreSQL driver
- `aiosqlite==0.21.0` — Async SQLite driver
- `greenlet==3.3.2` — SQLAlchemy greenlet support

**Data Processing**
- `pandas==2.3.3` — Data manipulation
- `numpy==2.3.5` — Numerical computing
- `openpyxl==3.1.5` — Excel file handling
- `chardet==5.2.0` — Character encoding detection

**Machine Learning**
- `scikit-learn==1.8.0` — ML utilities (calibration only)
- `joblib==1.5.2` — Model serialization

**Security**
- `pydantic==2.12.5` — Data validation
- `pydantic_core==2.41.5` — Pydantic core
- `passlib==1.7.4` — Password hashing
- `bcrypt==5.0.0` — bcrypt implementation
- `PyJWT==2.12.0` — JWT handling
- `cryptography==46.0.5` — Cryptographic operations
- `python-magic==0.4.27` — File type detection
- `bleach==6.1.0` — HTML sanitization
- `email-validator==2.2.0` — Email validation
- `slowapi==0.1.9` — Rate limiting

**Caching and Queuing**
- `redis==4.6.0` — Redis client

**Scheduling**
- `APScheduler==3.11.2` — Job scheduling

**PDF Generation**
- `fpdf2==2.8.6` — PDF generation

**Configuration**
- `python-dotenv==1.2.1` — Environment variables

**Optional (LLM)**
- `google-generativeai>=0.8.0` — Gemini API (optional)
- `anthropic>=0.34.0` — Claude API (optional)

### Node.js Dependencies

**Core Framework**
- `react==18.2.0` — UI framework
- `react-dom==18.2.0` — React DOM renderer
- `react-scripts==5.0.1` — Build toolchain

**Routing and State**
- `react-router-dom==6.22.3` — Client-side routing
- `axios==1.6.8` — HTTP client

**UI Components**
- `bootstrap==5.3.8` — CSS framework
- `react-bootstrap==2.10.10` — React Bootstrap components
- `react-icons==5.5.0` — Icon library

**Data Visualization**
- `chart.js==4.4.2` — Chart library
- `react-chartjs-2==5.2.0` — React Chart.js wrapper
- `recharts==3.7.0` — React chart library

**Animation**
- `framer-motion==12.31.0` — Animation library
- `react-intersection-observer==10.0.2` — Intersection observer hook

**Performance**
- `react-window==2.2.5` — Virtualized lists
- `react-window-infinite-loader==2.0.1` — Infinite scroll

**Testing**
- `@testing-library/jest-dom==5.17.0` — Jest DOM matchers
- `@testing-library/react==13.4.0` — React testing utilities
- `@testing-library/user-event==13.5.0` — User event simulation
- `web-vitals==2.1.4` — Performance metrics

### External Services

| Service | Version | Purpose | Network Requirements |
|---------|---------|---------|-------------------|
| Redis | 7.x | Rate limiting, token revocation, caching | Port 6379 TCP |
| PostgreSQL | 14+ | Production database | Port 5432 TCP |
| Google Gemini API | v1beta | LLM features | HTTPS outbound |
| Anthropic Claude API | v1 | LLM features | HTTPS outbound |

## API Versioning Strategy

### Current Version

API version: `v1`

Base path: `/api/v1/`

### Versioning Approach

**URL Path Versioning**
- Versions embedded in URL path (not headers or query params)
- Example: `/api/v1/students`, `/api/v2/students`

**Breaking Changes Definition**
- Removing or renaming fields in response schemas
- Changing field types in request/response
- Removing endpoints
- Changing authentication requirements
- Altering rate limit behavior

**Non-Breaking Changes**
- Adding new optional fields
- Adding new endpoints
- Expanding enum values
- Increasing rate limits
- Performance improvements

### Version Lifecycle

| Version | Status | Support End Date |
|---------|--------|-----------------|
| v1 | Current | TBD |

### Deprecation Process

1. New version announced 6 months before deprecation
2. Deprecated versions return `Sunset` header with end-of-life date
3. 30-day grace period after deprecation date
4. Final shutdown returns 410 Gone with migration documentation

### Backwards Compatibility

- Response schemas use `Optional[]` for new fields
- Request schemas accept unknown fields (Pydantic `extra='ignore'`)
- Enum values include `UNKNOWN` fallback
- Date formats follow ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)

## Error Handling Strategy

### Error Hierarchy

```
Exception
├── HTTPException (FastAPI)
│   ├── 400 Bad Request (validation errors)
│   ├── 401 Unauthorized (authentication)
│   ├── 403 Forbidden (authorization)
│   ├── 404 Not Found
│   ├── 409 Conflict (duplicate resource)
│   ├── 422 Unprocessable Entity
│   ├── 429 Too Many Requests
│   └── 500 Internal Server Error
├── SecurityException
│   ├── InputValidationError
│   ├── EncodingBypassError
│   └── PromptInjectionError
├── DatabaseException
│   ├── IntegrityError
│   └── ConnectionError
└── ServiceException
    ├── LLMServiceError
    ├── RateLimitExceeded
    └── FeatureExtractionError
```

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field 'risk_score' must be between 0 and 100",
    "field": "risk_score",
    "request_id": "abc-123-def"
  }
}
```

### Error Handling Layers

**1. Middleware Layer**
- Catches unhandled exceptions
- Returns generic 500 for unexpected errors
- Logs full stack trace with request_id

**2. Route Layer**
- Converts service exceptions to HTTP responses
- Adds request_id to error response
- Validates error response schema

**3. Service Layer**
- Raises domain-specific exceptions
- Includes context for debugging
- No HTTP-specific logic

**4. Database Layer**
- SQLAlchemy exceptions converted to DatabaseException
- IntegrityError includes constraint name
- ConnectionError triggers retry logic

### Retry Strategy

| Operation | Max Retries | Backoff | Exceptions Retried |
|-----------|-------------|---------|-------------------|
| Database read | 3 | Exponential (1s, 2s, 4s) | ConnectionError, Timeout |
| Database write | 2 | Exponential (1s, 2s) | ConnectionError |
| LLM API call | 2 | Fixed 5s | Timeout, RateLimit |
| Redis operation | 3 | Exponential | ConnectionError |

### Error Logging

- ERROR level: 5xx errors, unhandled exceptions
- WARNING level: 4xx errors (except 401/403)
- INFO level: 401/403 (security monitoring)
- DEBUG level: Full request/response (development only)

## Background Job Lifecycle

### Job Types

**1. Scheduled Jobs (APScheduler)**

| Job | Schedule | Duration | Priority |
|-----|----------|----------|----------|
| Daily Risk Scoring | 03:00 UTC | 5-10 min | High |
| Weekly Model Retraining | Sunday 02:00 UTC | 30-60 min | Medium |
| Token Cleanup | Daily 04:00 UTC | < 1 min | Low |
| GDPR Data Purge | 1st of month 01:00 UTC | Variable | Low |

**2. Triggered Jobs**

| Job | Trigger | Async/Sync |
|-----|---------|-----------|
| Data Ingestion | Admin upload | Async |
| Batch Prediction | API call | Async |
| PDF Report Generation | User request | Async |
| LLM Caching | API response | Sync |

### Job State Machine

```
PENDING -> RUNNING -> COMPLETED
   |          |
   v          v
FAILED    TIMEOUT -> FAILED
```

### Concurrency Control

**Async Locks (asyncio.Lock)**
- Prediction job: Single instance across all workers
- Token cleanup: Single instance
- Data ingestion: Per-file lock (allows parallel files)

**Lock Timeouts**
- Prediction job: 2 hours
- Data ingestion: 30 minutes per file
- Token cleanup: 10 minutes

### Job Monitoring

**Scheduler Status Endpoint**
```
GET /api/v1/monitoring/scheduler

Response:
{
  "status": "running",
  "jobs": [
    {
      "id": "daily_risk_scoring",
      "next_run": "2026-04-15T03:00:00Z",
      "last_run": "2026-04-14T03:00:00Z",
      "last_status": "completed"
    }
  ]
}
```

**Job Logging**
- Job start: INFO level with job_id, trigger_time
- Job progress: DEBUG level with batch numbers
- Job completion: INFO level with duration, record counts
- Job failure: ERROR level with exception, retry count

### Failure Handling

**Retry Policy**
- Max 3 retries for transient failures
- Exponential backoff between retries
- Dead letter queue for permanent failures (logged to database)

**Circuit Breaker**
- LLM API: Open after 5 failures, close after 60s
- Database: Open after 3 connection failures, close after 30s

## LLM Fallback Strategy

### Primary Provider: Google Gemini

**Configuration**
- Model: `gemini-1.5-flash`
- Timeout: 30 seconds
- Max tokens: 2048
- Temperature: 0.7

### Fallback Provider: Anthropic Claude

**Trigger Conditions**
- Gemini API returns 5xx error
- Gemini response timeout
- Gemini rate limit exceeded (429)
- HallucinationGuard flags Gemini response

**Configuration**
- Model: `claude-3-haiku-20240307`
- Timeout: 30 seconds
- Max tokens: 2048
- Temperature: 0.7

### Final Fallback: Rule-Based Response

**Trigger Conditions**
- Both LLM providers fail
- Both responses fail hallucination check
- LLM features disabled (no API keys)

**Implementation**
- Static response templates based on risk score ranges
- Pre-defined intervention suggestions by category
- No personalization (generic recommendations)

### Response Caching

**Cache Key**: Hash of (student_features + prompt_template_version)
**TTL**: 300 seconds (5 minutes)
**Storage**: Redis

**Cache Bypass**
- Debug mode enabled
- Explicit `cache=false` parameter
- Student features changed significantly (>20% delta)

### Error Handling

| Error | Retry | Fallback | Log Level |
|-------|-------|----------|-----------|
| Timeout | Yes (1) | Next provider | WARNING |
| Rate limit | Yes (2, 5s) | Next provider | WARNING |
| 5xx error | Yes (2) | Next provider | ERROR |
| 4xx error | No | Next provider | ERROR |
| Hallucination | No | Next provider | WARNING |

## Caching Strategy Details

### Cache Layers

**1. Redis Cache (Distributed)**

| Data Type | TTL | Invalidation | Key Pattern |
|-----------|-----|--------------|-------------|
| LLM responses | 300s | Feature change | `llm:{hash}` |
| Rate limit counters | 60s | Window expiry | `ratelimit:{user}:{endpoint}` |
| Feature vectors | 600s | New prediction | `features:{student_id}` |
| Student lists | 120s | Data ingestion | `students:list:{params}` |

**2. Application Cache (In-Memory)**

| Data Type | TTL | Scope |
|-----------|-----|-------|
| Configuration | 60s | Process |
| Database metadata | 300s | Process |
| Compiled schemas | None | Process |

**3. Database Query Cache (SQLAlchemy)**

- Enabled for: Read-only lookup tables
- Disabled for: Student data, predictions, audit logs
- Expiration: 300 seconds

### Cache Invalidation

**Event-Based Invalidation**
- Data ingestion: Invalidate student list caches
- New prediction: Invalidate feature caches for student
- Configuration change: Invalidate config cache

**Time-Based Invalidation**
- All caches have explicit TTL (no infinite caching)
- Short TTL for volatile data (rate limits)
- Long TTL for stable data (reference tables)

### Cache Warming

**Startup Warming**
- Load active student list into cache
- Pre-compute common filter combinations
- Warm LLM cache with common queries

**Scheduled Warming**
- Every 4 hours for reference data
- After data ingestion completion

### Cache Monitoring

**Metrics**
- Hit rate by cache type
- Miss rate by cache type
- Average TTL remaining on hits
- Eviction rate

**Health Check**
- Redis connectivity verified in `/health`
- Cache latency < 10ms (p95)

## Concurrency Model

### Async/Sync Strategy

**Async Operations (async/await)**
- HTTP request handling (FastAPI)
- Database queries (async SQLAlchemy with asyncpg)
- External API calls (LLM, webhooks)
- WebSocket connections (if implemented)

**Sync Operations**
- File I/O (data ingestion)
- CPU-intensive calculations (feature engineering)
- PDF generation
- Background job execution (APScheduler)

### Database Concurrency

**SQLite (Development)**
- Single writer, multiple readers
- WAL mode enabled (PRAGMA journal_mode=WAL)
- Timeout: 30 seconds
- Check same thread disabled

**PostgreSQL (Production)**
- Connection pooling via SQLAlchemy
- Pool size: 10 connections
- Max overflow: 20 connections
- Pool timeout: 30 seconds
- Pool recycle: 3600 seconds

### Request Concurrency

**Uvicorn Workers**
- Development: 1 worker (reload enabled)
- Production: 4 workers (configurable via `--workers`)

**Async Lock Usage**
- Prediction job lock: Prevents overlapping scheduled runs
- Ingestion file lock: Allows parallel processing of different files
- Token cleanup lock: Prevents concurrent cleanup jobs

### Thread Safety

**Thread-Local Storage**
- Database sessions (SQLAlchemy scoped sessions)
- Request context (Flask-style g object)

**Shared State**
- Redis connection pool (thread-safe)
- Configuration singleton (read-only after startup)
- Logger instances (thread-safe)

### Race Condition Prevention

**Database**
- Unique constraints prevent duplicate inserts
- Optimistic locking for concurrent updates
- Advisory locks for long-running operations

**Application**
- Async locks for singleton operations
- Atomic Redis operations for counters
- Immutable feature vectors (new versions on change)

## Database Transaction Strategy

### Transaction Boundaries

**Route-Level Transactions**
- Each HTTP request wrapped in transaction
- Automatic rollback on unhandled exception
- Commit on successful response

**Service-Level Transactions**
- Explicit transaction boundaries for multi-step operations
- Nested transactions via SQLAlchemy savepoints

**Background Job Transactions**
- Each job step independently transactional
- Partial failure allowed (logged, continues)

### Isolation Levels

| Operation | Isolation Level | Rationale |
|-----------|-----------------|-----------|
| Student read | READ COMMITTED | Allow concurrent updates |
| Prediction write | READ COMMITTED | Standard consistency |
| Audit log write | READ UNCOMMITTED | Performance, loss acceptable |
| Data ingestion | SERIALIZABLE | Prevent duplicates |
| Risk score update | REPEATABLE READ | Prevent lost updates |

### Connection Management

**Request Lifecycle**
- Connection acquired at request start
- Transaction begun at first query
- Commit at response generation
- Connection released to pool

**Background Jobs**
- Short-lived connections per batch
- Connection closed between batches
- Pool overflow handling for large jobs

### Retry Logic

**Retryable Errors**
- Deadlock detected
- Serialization failure
- Connection timeout

**Retry Configuration**
- Max retries: 3
- Backoff: Exponential (100ms, 200ms, 400ms)
- Jitter: Random 0-50ms

## Data Consistency Guarantees

### Consistency Levels

**Strong Consistency**
- Student identity (email, org_id)
- User authentication (password hash, role)
- Audit logs (immutable once written)

**Eventual Consistency**
- Risk scores (may lag behind raw data)
- Feature vectors (cached for 10 minutes)
- Aggregated analytics (computed periodically)

**Best-Effort**
- LLM-generated content (cached for 5 minutes)
- Real-time dashboards (30-second refresh)

### Consistency Mechanisms

**Database Constraints**
- Foreign key constraints with cascade rules
- Unique constraints on email, org_defined_id
- Check constraints on score ranges (0-100)

**Application Enforcement**
- Risk score calculation idempotent (same input = same output)
- Feature extraction deterministic (no randomness)
- Prediction timestamps immutable

**Reconciliation**
- Daily consistency check job (03:30 UTC)
- Detects orphaned records (predictions without students)
- Fixes inconsistencies via soft delete or data correction

### CAP Tradeoffs

**Primary Database (PostgreSQL)**
- CP system (Consistency + Partition tolerance)
- Synchronous replication for critical data
- Async replication for analytics replicas

**Redis Cache**
- AP system (Availability + Partition tolerance)
- Eventual consistency with database
- Cache misses trigger database read (consistent)

### Data Integrity Checks

**Scheduled Validation**
- Orphaned prediction records
- Students without risk snapshots
- Interventions without student references
- Audit logs with missing user references

**On-Demand Validation**
- Data ingestion validation (row-level)
- Risk score bounds checking (0-100)
- Referential integrity before deletion

## Failure Recovery Strategy

### Failure Modes

**1. Database Failure**

**Detection**
- Health check fails after 3 consecutive errors
- Connection pool exhausted
- Query timeout exceeded

**Recovery**
- Failover to read replica (if configured)
- Queue writes for later replay (Redis)
- Return 503 Service Unavailable with Retry-After header

**2. Redis Failure**

**Detection**
- Connection timeout
- Command execution error

**Recovery**
- Rate limiting disabled (fallback to in-memory)
- Caching disabled (direct database access)
- Return 200 OK with warning header

**3. LLM Service Failure**

**Detection**
- API timeout (30s)
- 5xx error response
- Rate limit exceeded

**Recovery**
- Fallback to alternative provider
- Final fallback to rule-based responses
- Queue for retry if all providers fail

**4. Background Job Failure**

**Detection**
- Exception thrown during execution
- Timeout exceeded
- Lock acquisition failed

**Recovery**
- Automatic retry (3 attempts)
- Exponential backoff between retries
- Dead letter logging for permanent failures

### Disaster Recovery

**RTO (Recovery Time Objective)**: 4 hours
**RPO (Recovery Point Objective)**: 1 hour

**Backup Strategy**
- Database: Daily full backup, hourly incremental
- Configuration: Version controlled (Git)
- Logs: 30-day retention, compressed

**Restoration Procedure**
1. Restore database from latest backup
2. Replay queued transactions from Redis
3. Verify data integrity with consistency checks
4. Gradual traffic ramp-up

### Circuit Breaker Pattern

| Service | Failure Threshold | Recovery Time | Half-Open Requests |
|---------|------------------|---------------|-------------------|
| LLM API | 5 errors | 60s | 1 test request |
| Database | 3 errors | 30s | 1 test query |
| Redis | 3 errors | 15s | 1 test command |

## Observability and Metrics Strategy

### Metric Categories

**1. Infrastructure Metrics**

| Metric | Collection Method | Alert Threshold |
|--------|------------------|-----------------|
| CPU usage | Docker stats | > 80% for 5 min |
| Memory usage | Docker stats | > 85% for 5 min |
| Disk I/O | Host metrics | > 1000 IOPS sustained |
| Network latency | Ping | > 100ms |

**2. Application Metrics**

| Metric | Collection Method | Retention |
|--------|------------------|-----------|
| Request latency | Middleware | 30 days |
| Error rate | Error handler | 90 days |
| Active users | Auth middleware | 30 days |
| Prediction count | Scheduler job | 1 year |

**3. Business Metrics**

| Metric | Source | Dashboard |
|--------|--------|-----------|
| Students at risk | Database | Daily |
| Intervention completion | Database | Weekly |
| Retention rate | Analytics service | Monthly |
| Revenue at risk | Business service | Monthly |

### Metric Collection

**Structured Logging**
- All metrics emitted as structured logs
- Consistent field naming (snake_case)
- Timestamps in UTC (ISO 8601)

**Log Levels for Metrics**
- INFO: Business events (prediction generated, intervention created)
- DEBUG: Performance metrics (query timing, cache hits)
- WARNING: Anomalous behavior (slow queries, high error rates)

### Distributed Tracing

**Request ID Propagation**
- Generated at entry point (nginx or FastAPI)
- Passed to all downstream services
- Included in all log entries
- Returned to client in response header

**Trace Context**
- Trace ID: Unique per request
- Span ID: Unique per operation within request
- Parent Span ID: Hierarchical relationship

### Metric Storage

**Short-term (7 days)**
- Application logs
- Raw request logs
- Debug metrics

**Medium-term (30 days)**
- Aggregated performance metrics
- Error summaries
- User activity

**Long-term (1 year)**
- Business KPIs
- Audit logs (compliance)
- Prediction history

## Alerting Strategy

### Alert Levels

**P0 (Critical)**
- Database unavailable
- All LLM providers down
- Authentication system failure
- Data corruption detected

**P1 (High)**
- Error rate > 10%
- Response latency > 5s (p95)
- Redis unavailable
- Single LLM provider down

**P2 (Medium)**
- Error rate > 5%
- Response latency > 2s (p95)
- Background job failures
- Disk space > 80%

**P3 (Low)**
- Error rate > 1%
- Unusual traffic patterns
- Certificate expiration < 30 days
- Dependency update available

### Alert Channels

| Level | Email | Pager | Slack | Dashboard |
|-------|-------|-------|-------|-----------|
| P0 | Yes | Yes | Yes | Yes |
| P1 | Yes | No | Yes | Yes |
| P2 | Yes | No | No | Yes |
| P3 | No | No | No | Yes |

### Alert Routing

**On-Call Rotation**
- Primary: Platform team lead
- Secondary: Backend engineer
- Escalation: Engineering manager (after 15 min)

**Business Hours vs Off-Hours**
- P0-P1: Alert 24/7
- P2: Alert business hours only
- P3: Dashboard only, weekly digest

### Alert Fatigue Prevention

**Grouping**
- Similar alerts grouped within 5-minute window
- Single notification for related failures

**Suppression**
- Maintenance windows disable non-critical alerts
- Dependent service failure suppresses downstream alerts

**Acknowledgment**
- Alerts require manual acknowledgment
- Auto-escalate if not acknowledged in 15 minutes

## Health Check Internals

### Health Check Endpoint

```
GET /health

Response (healthy):
{
  "status": "healthy",
  "timestamp": "2026-04-14T10:30:00Z",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "pass",
      "response_time_ms": 15,
      "last_success": "2026-04-14T10:29:55Z"
    },
    "redis": {
      "status": "pass",
      "response_time_ms": 5,
      "last_success": "2026-04-14T10:29:58Z"
    },
    "ml_pipeline": {
      "status": "pass",
      "last_prediction": "2026-04-14T03:00:00Z",
      "predictions_today": 500
    }
  }
}

Response (degraded):
{
  "status": "degraded",
  "checks": {
    "database": {"status": "pass"},
    "redis": {"status": "fail", "error": "Connection timeout"},
    "ml_pipeline": {"status": "pass"}
  }
}

Response (unhealthy):
{
  "status": "unhealthy",
  "checks": {
    "database": {"status": "fail", "error": "Connection refused"},
    "redis": {"status": "pass"},
    "ml_pipeline": {"status": "unknown"}
  }
}
```

### Health Check Implementation

**Database Check**
- Query: `SELECT 1`
- Timeout: 5 seconds
- Failure threshold: 3 consecutive failures

**Redis Check**
- Command: `PING`
- Timeout: 2 seconds
- Failure threshold: 3 consecutive failures

**ML Pipeline Check**
- Verify last prediction timestamp < 25 hours ago
- Verify prediction count matches student count
- Check for failed predictions in last 24 hours

### Health Check Usage

**Load Balancer**
- Interval: 10 seconds
- Timeout: 5 seconds
- Unhealthy threshold: 2 failures
- Healthy threshold: 2 successes

**Kubernetes (if applicable)**
- Liveness probe: `/health` (restart if unhealthy)
- Readiness probe: `/health` (remove from service if not ready)
- Startup probe: Allow 60s for initialization

**Monitoring**
- Health status logged every minute
- Status changes trigger immediate alert
- Historical health data retained 30 days

## CI/CD Pipeline

### Pipeline Overview

```
Push/PR -> Lint -> Test -> Security Scan -> Build -> Deploy
```

### GitHub Actions Workflow

**Trigger Events**
- Push to `main` or `develop`
- Pull request to `main` or `develop`

**Jobs**

**1. test-backend**
- Runs on: ubuntu-latest
- Python versions: 3.11, 3.12
- Steps:
  - Checkout code
  - Set up Python
  - Cache pip dependencies
  - Install requirements.txt and requirements-dev.txt
  - Lint with flake8
  - Type check with mypy
  - Run pytest with coverage
  - Upload coverage to Codecov

**2. test-frontend**
- Runs on: ubuntu-latest
- Node versions: 18.x, 20.x
- Steps:
  - Checkout code
  - Set up Node.js
  - Cache npm dependencies
  - Install dependencies (npm ci)
  - Run ESLint
  - Build (npm run build)
  - Run tests (npm test)

**3. security-scan**
- Runs on: ubuntu-latest
- Steps:
  - Checkout code
  - Run Bandit security scan
  - Check for hardcoded secrets (detect-secrets)

**4. docker-build**
- Runs on: ubuntu-latest
- Steps:
  - Checkout code
  - Set up Docker Buildx
  - Build Docker images (docker-compose build)
  - Validate docker-compose configuration

**5. all-checks-pass**
- Depends on: test-backend, test-frontend, security-scan, docker-build
- Runs on: ubuntu-latest
- Purpose: Gate for merge requirements

### Quality Gates

**Required Checks for Merge**
- Backend tests pass (Python 3.11 and 3.12)
- Frontend tests pass (Node 18.x and 20.x)
- Security scan passes
- Docker build succeeds
- Codecov coverage upload succeeds

**Linting Rules**
- Python: flake8 with max line length 127
- JavaScript: ESLint with react-app configuration

**Type Checking**
- Python: mypy with SQLAlchemy plugin
- JavaScript: PropTypes (no TypeScript in current codebase)

### Deployment Environments

| Environment | Branch | Trigger | Approval |
|-------------|--------|---------|----------|
| Development | any | Manual | None |
| Staging | develop | Auto on merge | None |
| Production | main | Auto on merge | Required (1 reviewer) |

### Rollback Strategy

**Automatic Rollback**
- Health check failure after deployment
- Error rate > 10% for 5 minutes
- P0 alert triggered

**Manual Rollback**
- Previous Docker image available
- Database migrations reversible (downgrade script)
- Redis cache can be cleared

## Known Technical Debt

### Critical (Address in next quarter)

| Item | Location | Impact | Mitigation |
|------|----------|--------|------------|
| ARCH-2: Distributed lock needed | `services/infrastructure/scheduler.py` | Multi-worker deployments unsafe | Async lock sufficient for single-worker |
| Token cleanup job | `services/infrastructure/token_cleanup.py` | revoked_tokens table growth | Scheduled cleanup runs daily |
| SQLite in production | `database/connection.py` | Concurrency limitations | PostgreSQL migration path documented |

### High (Address within 6 months)

| Item | Location | Impact | Mitigation |
|------|----------|--------|------------|
| No trained ML model | `services/ml_service.py` | Rule-based only | XGBoost pipeline in roadmap |
| No LMS API integration | `data_ingestion/` | Manual file uploads only | Excel ingestion robust |
| Single-process prediction | `services/infrastructure/scheduler.py` | Scaling bottleneck | Batch processing within job |
| No horizontal scaling | `docker/docker-compose.yml` | Single backend instance | Vertical scaling available |
| Chart.js and Recharts both present in frontend bundle | `frontend/` | ~220KB bundle overhead | Consolidation to Recharts in progress |
| EWSDataPipeline class is a deprecated CLI-only tool | `ingestion/pipeline.py` | Confusion with production path | Production ingestion uses `ingest_all_data()` from `data_ingestion.py` |

### Medium (Address within 12 months)

| Item | Location | Impact | Mitigation |
|------|----------|--------|------------|
| Ghost student detection | `services/risk_scoring.py` | Relies on zero engagement threshold | Manual review for edge cases |
| Calendar scorer edge cases | `services/calendar_scorer.py` | Trimester boundary issues | Test coverage for boundary dates |
| LLM requires manual config | `services/ai/llm_orchestrator.py` | Optional feature disabled by default | Rule-based fallback always available |
| No automated email | `services/infrastructure/recommender.py` | Manual outreach only | Intervention queue tracks assignments |
| Legacy K-12 weight keys pending removal | `services/risk_scoring.py` | Unused config keys | Removal blocked on test migration |
| PostgreSQL production migration guide incomplete | `docs/postgresql-migration.md` | No documented migration path | SQLite sufficient for current scale |

### Low (Nice to have)

| Item | Location | Impact | Mitigation |
|------|----------|--------|------------|
| Limited frontend tests | `frontend/` | Manual QA required | Critical paths covered |
| Basic PDF generation | `services/export_service.py` | Limited formatting | FPDF2 sufficient for reports |
| No scheduled reports | `routes/reports.py` | On-demand only | Admin can trigger manually |

### Debt Tracking

**Location**: GitHub Issues with label `technical-debt`
**Review**: Monthly technical debt review meeting
**Prioritization**: Based on business impact and engineering bandwidth

## Operational Runbook

### Daily Operations

**Health Check (09:00 UTC)**
1. Check `/health` endpoint
2. Verify scheduler status at `/api/v1/monitoring/scheduler`
3. Review error logs for P0/P1 alerts
4. Check disk space on database and log volumes

**Log Review (End of business day)**
1. Review ERROR and CRITICAL logs
2. Check for unusual patterns
3. Investigate any 5xx errors
4. Document findings in operations log

### Weekly Operations

**Sunday 02:00 UTC: Weekly Model Retraining**
- Monitor job completion
- Verify model metrics improved
- Check for training failures

**Monday Morning: Weekly Review**
1. Review weekend alerts
2. Check prediction generation ran successfully
3. Verify data ingestion completed (if scheduled)
4. Review capacity trends

### Monthly Operations

**1st of Month (01:00 UTC): GDPR Data Purge**
- Monitor purge job completion
- Verify retention policy compliance
- Check audit log for purge operations

**Monthly Maintenance Window**
- Dependency updates (security patches)
- Database maintenance (VACUUM, reindex)
- Log rotation and archival
- Certificate renewal check

### Incident Response

**Incident Classification**
- SEV1: System down, all users affected (P0 alerts)
- SEV2: Degraded performance, partial functionality (P1 alerts)
- SEV3: Minor issue, workarounds available (P2 alerts)
- SEV4: No user impact, preventive (P3 alerts)

**Response Procedures**

**SEV1 Response**
1. Acknowledge alert within 5 minutes
2. Assess scope (all users vs subset)
3. Check dependent services (database, Redis)
4. If database down: Check connection pool, restart if needed
5. If Redis down: Restart container, verify cache rebuild
6. Communicate status to stakeholders
7. Post-incident review within 24 hours

**SEV2 Response**
1. Acknowledge alert within 15 minutes
2. Identify degraded component
3. Check recent deployments (rollback candidate)
4. Check error logs for patterns
5. Apply known fixes from runbook
6. Escalate to SEV1 if not resolved in 30 minutes

### Database Operations

**Backup Verification (Weekly)**
1. Check backup completion logs
2. Verify backup file integrity
3. Test restore procedure on staging

**Connection Pool Monitoring**
- Check `connections_active` metric
- Alert if > 80% of pool exhausted
- Alert if connection wait time > 1s

### Redis Operations

**Memory Monitoring**
- Check memory usage trend
- Alert if > 80% of max memory
- Eviction policy: allkeys-lru

**Replication Monitoring (if clustered)**
- Check replication lag < 1s
- Verify replica sync status

### Log Management

**Log Rotation**
- Application logs: Daily rotation, 30-day retention
- Access logs: Daily rotation, 90-day retention
- Audit logs: No rotation, 7-year retention (compliance)

**Log Analysis**
- Daily: Review ERROR and CRITICAL
- Weekly: Trend analysis
- Monthly: Capacity planning insights

## Developer Onboarding Guide

### Pre-requisites Checklist

**System Setup**
- [ ] Python 3.12+ installed
- [ ] Node.js 18+ installed
- [ ] Git configured with SSH keys
- [ ] Docker installed (optional but recommended)
- [ ] IDE with Python and JavaScript support
- [ ] Access to repository

**Accounts and Access**
- [ ] GitHub access to repository
- [ ] Local development environment variables (`.env`)
- [ ] Test API keys (optional for LLM features)

### Day 1: Environment Setup

**Morning (4 hours)**
1. Clone repository
2. Create Python virtual environment
3. Install backend dependencies (`pip install -r requirements.txt`)
4. Install frontend dependencies (`cd frontend && npm install`)
5. Copy `.env.example` to `.env` and configure
6. Run migrations (`alembic upgrade head`)
7. Initialize database (`python -c "from backend.database.connection import init_db; init_db()"`)
8. Seed test data if available

**Afternoon (4 hours)**
1. Start backend (`uvicorn backend.main:app --reload`)
2. Start frontend (`cd frontend && npm start`)
3. Verify application loads at `http://localhost:3000`
4. Login with test credentials
5. Explore UI and verify API connectivity

### Day 2: Codebase Orientation

**Backend Tour (4 hours)**
1. Review `backend/main.py` (application entry point)
2. Explore `backend/routes/` (API endpoints)
3. Understand `backend/services/` (business logic)
4. Review `backend/core/` (security, auth, logging)
5. Study `backend/middleware/` (request processing)
6. Examine `backend/database/models/` (data layer)

**Frontend Tour (4 hours)**
1. Review `frontend/src/App.js` (routing)
2. Explore `frontend/src/pages/` (main views)
3. Understand `frontend/src/components/` (UI components)
4. Study `frontend/src/context/` (state management)
5. Review `frontend/src/services/api.js` (API client)

### Day 3: Testing and Development Workflow

**Testing (4 hours)**
1. Run backend tests (`pytest backend/tests -v`)
2. Understand test structure and fixtures
3. Review security tests (`test_idor.py`, `test_encoding_bypasses.py`)
4. Run frontend tests (`cd frontend && npm test`)

**Development Workflow (4 hours)**
1. Create feature branch (`git checkout -b feature/my-feature`)
2. Make small change (add log message or comment)
3. Run pre-commit checks (flake8, mypy)
4. Run tests
5. Commit with conventional commit format
6. Push branch
7. Create pull request (for practice, close after)

### Week 1: First Tasks

**Recommended First Issues**
1. Add logging to a service method
2. Update error message for clarity
3. Add unit test for edge case
4. Update documentation comment
5. Fix minor linting issue

**Guidelines**
- Pair with senior developer for first few PRs
- Ask questions in team chat
- Document any confusing code discovered
- Suggest improvements to this onboarding guide

### Development Best Practices

**Code Style**
- Python: Follow PEP 8, use type hints, max line length 100
- JavaScript: Follow ESLint rules, use functional components
- Commits: Use conventional commit format

**Testing**
- Write tests for new features
- Run tests before committing
- Update tests when changing behavior
- Security tests required for auth changes

**Security**
- Never commit secrets
- Sanitize all user input
- Follow RBAC for new endpoints
- Add audit logging for data access

**Performance**
- Use async for I/O operations
- Batch database operations when possible
- Cache expensive computations
- Profile slow endpoints

### Common Development Issues

**Issue: Database locked (SQLite)**
- Solution: Stop all processes, restart backend only
- Prevention: Use PostgreSQL for concurrent development

**Issue: Frontend not connecting to backend**
- Solution: Check `REACT_APP_API_URL` in environment
- Verify backend running on correct port

**Issue: Tests failing locally**
- Solution: Ensure `TESTING=true` environment variable
- Check for port conflicts

**Issue: Import errors**
- Solution: Verify virtual environment activated
- Check PYTHONPATH includes project root

**Issue: "Database schema out of date" error on startup**
- Solution: Run `alembic upgrade head` before starting the server
- This check runs automatically at startup and will refuse to start if migrations are pending

**Issue: Token immediately rejected after refresh**
- Solution: Verify Redis is running — the RTR revocation write requires Redis to be reachable
- Check with: `redis-cli ping`

### Resources

**Documentation**
- API docs: Run backend and visit `/docs` (Swagger UI)
- Architecture: See `docs/ARCHITECTURE.md`
- Database: See `docs/DATABASE_INTEGRITY_STRATEGY.md`
- Deployment: See `docs/DEPLOYMENT.md`

**Getting Help**
- Technical questions: Ask in development chat
- Architecture questions: Schedule time with tech lead
- Bug reports: Create GitHub issue with reproduction steps
- Feature requests: Create GitHub issue with use case

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
