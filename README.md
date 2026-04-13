# 🎓 Meridian EWS — Early Warning System for Student Retention

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.119.0-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-blue)](backend/tests/)

> **Intelligent Student Retention Platform** — A production-ready Early Warning System that ingests Brightspace LMS data, computes deterministic engagement-based risk scores (0-100), and routes prioritized intervention recommendations to academic advisors through an intelligent queue interface.

---

## 📖 Detailed Project Description

### What This System Does

**Meridian EWS** is a deterministic, rule-based student retention platform engineered for the BITS Pilani Digital operations team. The platform processes weekly Excel exports from Brightspace LMS, applies sophisticated behavioral feature engineering to compute granular 0–100 risk scores, and generates actionable intervention recommendations that advisors can review and act upon through a prioritized queue interface.

### Problem Statement

Educational institutions face significant challenges in identifying at-risk students before they drop out:
- **Reactive approaches**: Traditional systems identify struggling students only after exam failures
- **Data silos**: LMS engagement data remains unutilized for early intervention
- **Advisor overload**: Academic advisors lack prioritization tools to focus on highest-risk cases
- **No systematic tracking**: Intervention outcomes are rarely measured or optimized

### Real-World Relevance

Student retention directly impacts institutional revenue and student outcomes. A 5% improvement in retention can translate to millions in preserved tuition revenue while ensuring students complete their educational goals. Meridian EWS provides:

- **Early identification** of disengagement patterns (as early as Week 2)
- **Prioritized intervention queues** based on risk severity
- **Measurable outcome tracking** to optimize retention strategies
- **FERPA-compliant data handling** for educational records

### Target Users

| Role | Primary Functions |
|------|-------------------|
| **Academic Advisors** | Review intervention queues, act on recommendations, log outcomes |
| **Faculty Members** | View risk summaries for assigned students, receive alerts |
| **Retention Team Leaders** | Monitor cohort-level trends, configure thresholds |
| **Administrators** | Manage data ingestion, user access, system configuration |

### Key Goals & Design Philosophy

1. **Deterministic Transparency**: Rule-based scoring (not black-box ML) ensures explainable risk assessments
2. **Privacy-First Architecture**: FERPA-compliant with pseudonymized identifiers in logs
3. **Operational Resilience**: Graceful degradation when LLM or external services are unavailable
4. **Actionable Intelligence**: Risk scores are meaningless without clear intervention pathways
5. **Data-Driven Optimization**: Post-trimester calibration against actual outcomes

**Important Design Decision:** This is a **rule-based scoring engine**, not a trained machine learning model. The risk scores are computed by a deterministic weighted formula across seven engagement features. There is no neural network, XGBoost classifier, or other ML model producing these scores. The optional LLM features (Gemini or Claude integration for natural-language risk explanations) are entirely separate from the core scoring pipeline and can be disabled without affecting risk calculations.

---

---

## 🚀 Key Features

### Core Platform Features

| Feature | Description | Impact |
|---------|-------------|--------|
| **Automated Data Ingestion** | Weekly Excel upload from Brightspace LMS with idempotent upsert logic | Eliminates manual data entry, ensures data freshness |
| **Deterministic Risk Scoring** | Weighted formula across 7 engagement dimensions producing 0-100 scores | Transparent, explainable risk assessment without ML black boxes |
| **Calendar-Aware Scoring** | Deadline-proximity multipliers for 10 configured courses | Contextualizes risk based on upcoming assessment deadlines |
| **Intervention Queue Management** | Prioritized advisor queues with risk-based sorting | Ensures advisors focus on highest-need students first |
| **Outcome Tracking** | Logs intervention actions and results for efficacy analysis | Enables data-driven optimization of retention strategies |
| **Multi-Role Access Control** | Role-based permissions (advisor, faculty, admin, retention_team) | Secure, principle-of-least-privilege access |

### Advanced Capabilities

- **Ghost Student Detection**: Identifies students with zero LMS logins within 7 days and triggers automated activation outreach
- **Risk Spike Alerts**: Notifications when student risk scores increase by ≥15 points (configurable threshold)
- **Intervention Cooldown Logic**: Prevents advisor spam by enforcing minimum days between interventions per student
- **GDPR/FERPA Compliance Tools**: Built-in data export and erasure endpoints for subject access requests
- **Post-Trimester Calibration**: Automated threshold recommendation based on actual exam outcomes vs. risk predictions

### AI/LLM Features (Optional)

| Feature | Provider | Description |
|---------|----------|-------------|
| **Risk Explanation Generation** | Gemini/Claude | Natural language summary of risk factors per student |
| **Intervention Suggestions** | Gemini/Claude | AI-generated personalized outreach templates |
| **Cohort Narrative Reports** | Gemini/Claude | Executive summaries for retention team leaders |
| **What-If Analysis** | Gemini/Claude | Scenario simulation for advisor training |

**Note:** All LLM features are **optional** and can be disabled via `ENABLE_LLM_FEATURES=false`. The core risk scoring operates entirely without external AI dependencies.

---

## 🧠 System Architecture & Workflow

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL DATA SOURCES                                      │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ Brightspace LMS     │  │ Exam Systems        │  │ Course Registry     │              │
│  │ (Weekly Exports)    │  │ (Marks/Attendance)  │  │ (Deadlines/Metadata)│              │
│  └──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘              │
└─────────────┼─────────────────────────┼─────────────────────────┼───────────────────────┘
              │                         │                         │
              ▼                         ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              INGESTION PIPELINE (Async)                                │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │  POST /api/v1/admin/ingest  →  Excel Validation  →  StudentLoader/ExamLoader    │    │
│  │                                   ↓                                             │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐   │    │
│  │  │Idempotent   │  │Auto-        │  │Outcome          │  │Intervention     │   │    │
│  │  │Upsert       │  │Deactivation │  │Inference        │  │Backfill         │   │    │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  └─────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA PERSISTENCE LAYER                                      │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────────────┐  │
│  │    students    │ │  enrollments   │ │  risk_snapshots│ │  intervention_logs     │  │
│  │  (identity)    │ │  (courses)     │ │  (scores)      │ │  (actions/outcomes)    │  │
│  └────────────────┘ └────────────────┘ └────────────────┘ └────────────────────────┘  │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────────────┐  │
│  │ graded_        │ │  exam_records  │ │engineered_     │ │  course_registry       │  │
│  │ _components    │ │  (marks)       │ │_features       │ │  (metadata)            │  │
│  └────────────────┘ └────────────────┘ └────────────────┘ └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           FEATURE ENGINEERING & SCORING                                  │
│                                                                                         │
│   ┌────────────────────────┐         ┌─────────────────────────────────────────┐     │
│   │  Raw LMS Metrics       │         │  RiskScorer                             │     │
│   │  • Login count         │────────▶│  • Normalization (0-100)                │     │
│   │  • Content views       │         │  • Weighted aggregation                 │     │
│   │  • Quiz attempts       │         │  • Calendar-aware adjustment (optional) │     │
│   │  • Time spent          │         │  • Output: 0-100 risk score               │     │
│   │  • Discussion posts    │         └─────────────────────────────────────────┘     │
│   └────────────────────────┘                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           DECISION ENGINE & INTERVENTIONS                              │
│                                                                                         │
│   Risk Score + Pattern Analysis  →  get_intervention_recommendation()                   │
│                                                                                         │
│   Score Range    Pattern        Intervention Type         Priority                        │
│   ─────────────────────────────────────────────────────────────                         │
│   0-29           on_track       none                      Low                            │
│   30-49          at_risk        gentle_reminder           Medium                         │
│   50-69          struggling     mentor_outreach           High                           │
│   70-89          disengaged     urgent                   Critical                        │
│   90-100         ghost          activation_outreach      Critical                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER (FastAPI + JWT)                                 │
│                                                                                         │
│   100+ REST Endpoints  │  Role-Based Access Control  │  Rate Limiting  │  Audit Log   │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              REACT FRONTEND DASHBOARD                                  │
│                                                                                         │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│   │  Advisor     │  │   Student    │  │   Cohort     │  │   Admin      │                │
│   │  Queue       │  │   Profile    │  │   Analytics  │  │   Panel      │                │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **Ingestion Pipeline** | Python + Pandas + OpenPyXL | Async Excel processing, data validation, idempotent upserts |
| **Feature Engineering** | Python + NumPy | Normalization, weighted aggregation, calendar-aware adjustments |
| **Risk Scorer** | Rule-based engine | Deterministic 0-100 score computation |
| **Decision Engine** | Rule-based router | Intervention type classification |
| **API Gateway** | FastAPI + Uvicorn | REST endpoints, JWT auth, request validation |
| **Database** | SQLAlchemy + Alembic | ORM models, migrations, SQLite/PostgreSQL support |
| **Cache/Lock** | Redis | Distributed ingestion locks, rate limiting |
| **Frontend** | React 18 + Bootstrap | Advisor dashboard, data visualization |
| **Scheduler** | APScheduler | Daily prediction runs, weekly retention reports |

### Security Considerations

- **Authentication**: JWT tokens with configurable expiry, refresh token rotation
- **Authorization**: Role-based access control (RBAC) with ownership checks
- **Data Privacy**: PII masking in logs, pseudonymized identifiers for LLM calls
- **Input Validation**: Pydantic schemas for all API inputs
- **Rate Limiting**: SlowAPI with per-endpoint burst/sustained limits
- **Audit Trail**: FERPA-compliant access logging for all student data reads

---

## 🛠️ Tech Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 18.2.0 | UI framework with functional components and hooks |
| **React Bootstrap** | 2.10.10 | Component library for responsive design |
| **React Router DOM** | 6.22.3 | Client-side routing and navigation |
| **Chart.js / Recharts** | 4.4.2 / 3.7.0 | Data visualization for risk trends and cohort analytics |
| **Framer Motion** | 12.31.0 | Animation library for smooth UI transitions |
| **Axios** | 1.6.8 | HTTP client for API communication |
| **React Icons** | 5.5.0 | Icon library |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.12 | Primary language |
| **FastAPI** | 0.119.0 | High-performance async web framework |
| **Uvicorn** | 0.38.0 | ASGI server |
| **Pydantic** | 2.12.5 | Data validation and settings management |
| **SQLAlchemy** | 2.0.45 | ORM for database operations |
| **Alembic** | 1.18.4 | Database migration tool |

### Database & Cache
| Technology | Version | Purpose |
|------------|---------|---------|
| **SQLite** | 3.35+ | Default development database |
| **PostgreSQL** | 15+ | Production database (recommended) |
| **psycopg2-binary** | 2.9+ | PostgreSQL adapter |
| **Redis** | 7.x | Distributed locks, rate limiting cache |
| **asyncpg** | 0.29.0 | Async PostgreSQL driver |

### Data Processing
| Technology | Version | Purpose |
|------------|---------|---------|
| **Pandas** | 2.3.3 | Excel data processing and manipulation |
| **NumPy** | 2.3.5 | Numerical computations for feature engineering |
| **OpenPyXL** | 3.1.5 | Excel file reading/writing |
| **python-magic** | 0.4.27 | MIME type validation for uploads |

### Security & Auth
| Technology | Version | Purpose |
|------------|---------|---------|
| **PyJWT** | 2.12.0 | JWT token generation and validation |
| **Passlib + bcrypt** | 1.7.4 / 5.0.0 | Password hashing |
| **Cryptography** | 46.0.5 | Encryption utilities |
| **SlowAPI** | 0.1.9 | Rate limiting middleware |

### AI/ML Integrations (Optional)
| Technology | Version | Purpose |
|------------|---------|---------|
| **Google Generative AI** | 0.8.0+ | Gemini API for risk explanations |
| **Anthropic** | 0.34.0+ | Claude API for intervention suggestions |
| **scikit-learn** | 1.8.0 | Threshold calibration (post-trimester analysis only) |

### DevOps & Deployment
| Technology | Purpose |
|------------|---------|
| **Docker** | Containerization |
| **APScheduler** | Background job scheduling |
| **fpdf2** | PDF report generation |
| **pytest** | Testing framework |
| **mypy** | Static type checking |

---

## ⚙️ Installation & Setup Guide

### Prerequisites

| Component | Version | Installation Notes |
|-----------|---------|-------------------|
| Python | 3.12.x | `pyenv install 3.12` or system package manager |
| Node.js | 18+ | Required for frontend development only |
| Redis | 7.x | `docker run -d -p 6379:6379 redis:alpine` |
| SQLite | 3.35+ | Usually pre-installed on most systems |
| PostgreSQL | 15+ | Optional, recommended for production |

### Step-by-Step Setup

#### 1. Clone Repository

```bash
git clone https://github.com/your-org/ews-retention-platform.git
cd ews-retention-platform
```

#### 2. Python Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

#### 3. Install Backend Dependencies

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

#### 4. Install Frontend Dependencies (Optional)

```bash
cd frontend
npm install
cd ..
```

#### 5. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with required values
nano .env  # or your preferred editor
```

**Required Environment Variables:**

| Variable | Value | How to Generate |
|----------|-------|-----------------|
| `SECRET_KEY` | 64-char hex string | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GEMINI_MODEL` | `gemini-1.5-pro-002` | Use exact pinned version |

**Optional but Recommended:**

| Variable | Development | Production |
|----------|-------------|------------|
| `DATABASE_URL` | `sqlite:///./backend/data/meridian.db` | `postgresql://user:pass@host/db` |
| `REDIS_URL` | `redis://localhost:6379` | Production Redis URL |
| `GEMINI_API_KEY` | Optional (mock responses) | Required for LLM features |

#### 6. Database Setup

```bash
# Run migrations
alembic upgrade head

# Seed development data (creates admin user)
python -m backend.scripts.seed_dev_data
```

**Default Dev Credentials:**
- Username: `dev_admin`
- Password: `changeme_local_only`
- Roles: `admin`, `faculty`, `retention_team`

#### 7. Start Redis (if not using Docker)

```bash
# Using Docker (recommended)
docker run -d -p 6379:6379 --name redis redis:alpine

# Or using system Redis
redis-server
```

#### 8. Start Backend Server

```bash
# Development (with auto-reload)
uvicorn backend.main:app --reload --port 8000

# Production (single worker required)
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**⚠️ Critical:** The application must run as a **single uvicorn worker** due to the Redis distributed lock for ingestion. Multi-worker deployment requires additional coordination architecture.

#### 9. Start Frontend (Optional)

```bash
cd frontend
npm start
```

Frontend available at `http://localhost:3000`

#### 10. Verify Installation

```bash
# Run smoke tests
bash scripts/smoke_test.sh

# Or test API health
curl http://localhost:8000/health
```

---

## 📊 Risk Score Interpretation

### How the Score is Computed

The 0–100 risk score is a **deterministic weighted aggregation** of seven engagement features:

| Feature | Default Weight | Description | Data Source |
|---------|----------------|-------------|-------------|
| Content completion rate | 0.25 | Percentage of course content visited | Brightspace LMS |
| Login consistency | 0.20 | Regularity of LMS logins (streak-based) | Brightspace LMS |
| Quiz engagement | 0.20 | Quiz attempts and scores | Brightspace LMS |
| Assignment submission | 0.15 | On-time submission rate | Brightspace LMS |
| Time investment | 0.10 | Hours spent in LMS per week | Brightspace LMS |
| Discussion participation | 0.10 | Forum posts and replies | Brightspace LMS |
| Calendar proximity | variable | Days until next deadline (10 courses only) | Course Registry |

**Weight Validation:** All weights must sum to 1.0 ± 0.01 (enforced at startup by `validate_ml_config()`).

### Intervention Thresholds

| Score Range | Intervention Type | Risk Band | Advisor Action |
|-------------|-------------------|-----------|----------------|
| 0–29 | No action | On track | Monitor only |
| 30–49 | Gentle reminder | At risk | Automated email |
| 50–69 | Mentor outreach | Struggling | Faculty contact |
| 70–89 | Urgent intervention | Disengaged | Immediate advisor meeting |
| 90–100 | Critical alert | Ghost | Activation outreach + escalation |

**Configurable via:** `THRESHOLD_NO_ACTION`, `THRESHOLD_GENTLE`, `THRESHOLD_MENTOR`, `THRESHOLD_URGENT`

### Engagement Patterns

| Pattern | Trigger Condition | Typical Intervention |
|---------|-------------------|---------------------|
| **ghost** | Zero logins in past 7 days | Activation outreach |
| **disengaged** | Login consistency score < 30 | Mentor check-in |
| **struggling** | Quiz average < 40% AND content completion < 50% | Academic support |
| **on_track** | Risk score < 30 AND all feature scores > 60 | Continue monitoring |

### Important Caveats

**⚠️ This is NOT a machine learning prediction.** The score is a deterministic weighted formula that has not yet been validated against historical dropout outcomes. The system uses rule-based thresholds, not a trained classifier.

**Recommended Usage:**
- Use as a **prioritization signal** for advisor attention
- **NOT** as a definitive prediction of student withdrawal
- Run `python -m backend.ml.training.calibrate` after each trimester to compute recommended thresholds based on actual exam outcomes

---

## ▶️ Usage Guide

### Running the Application

#### Backend Only (API Mode)

```bash
# Terminal 1: Start Redis
docker run -d -p 6379:6379 redis:alpine

# Terminal 2: Start FastAPI server
uvicorn backend.main:app --reload --port 8000

# Access API documentation
open http://localhost:8000/docs  # Interactive Swagger UI
```

#### Full-Stack (With Frontend)

```bash
# Terminal 1: Redis
docker run -d -p 6379:6379 redis:alpine

# Terminal 2: Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 3: Frontend
cd frontend
npm start

# Access application
open http://localhost:3000  # React frontend
```

### Weekly Data Ingestion Workflow

#### Step 1 — Export from Brightspace

1. Navigate to **Course Admin → Reports → Learner Usage**
2. Select date range: previous 7 days
3. Include columns: Username, Org Defined ID, First Name, Last Name, Last Login, Content Visits, Quiz Attempts, Assignment Submissions, Discussion Posts, Time in Content
4. Export as **Excel (.xlsx)**

#### Step 2 — Upload via API

```bash
# Obtain admin token first
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"dev_admin","password":"changeme_local_only"}'

# Upload Excel file
curl -X POST http://localhost:8000/api/v1/admin/ingest \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/brightspace_export.xlsx" \
  -F "semester_name=T1-2025" \
  -F "week_number=5"
```

Response:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Ingestion task queued"
}
```

#### Step 3 — Check Task Status

```bash
curl http://localhost:8000/api/v1/admin/ingest/status/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <admin_token>"
```

Status values: `pending` → `running` → `success` | `partial` | `failed`

#### Step 4 — Verify in Audit Log

```bash
curl http://localhost:8000/api/v1/admin/ingestion-runs \
  -H "Authorization: Bearer <admin_token>"
```

### Example Workflows

#### Advisor Daily Workflow

1. **Log in** to React dashboard (`http://localhost:3000`)
2. **Review intervention queue** sorted by risk score (highest first)
3. **Click student** to view detailed risk profile and engagement metrics
4. **Take action**: Call, email, or schedule meeting with student
5. **Log outcome** in system for tracking efficacy

#### Admin Configuration Workflow

```bash
# View current thresholds
curl http://localhost:8000/api/v1/config/thresholds \
  -H "Authorization: Bearer <admin_token>"

# Update thresholds
curl -X PUT http://localhost:8000/api/v1/config/thresholds \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "threshold_no_action": 25.0,
    "threshold_gentle": 45.0,
    "threshold_mentor": 65.0,
    "threshold_urgent": 85.0
  }'

# Run post-trimester calibration
python -m backend.ml.training.calibrate
```

---

## 📂 Project Structure

```
ews-retention-platform/
├── 📁 backend/                    # FastAPI backend application
│   ├── 📁 api/                    # API versioning and routing
│   ├── 📁 application/            # Application services
│   ├── 📁 config/                 # Configuration management
│   ├── 📁 controllers/            # Request controllers
│   ├── 📁 core/                   # Core utilities and shared code
│   ├── 📁 database/               # Database models and connections
│   │   ├── 📁 models/             # SQLAlchemy ORM models
│   │   └── 📁 migrations/         # Alembic migration scripts
│   ├── 📁 domain/                 # Domain logic and entities
│   ├── 📁 ingestion/              # Data ingestion pipeline
│   │   ├── 📄 excel_loader.py    # Excel file processing
│   │   ├── 📄 student_loader.py  # Student record upserts
│   │   └── 📄 exam_loader.py     # Exam data ingestion
│   ├── 📁 jobs/                   # Background scheduled jobs
│   ├── 📁 middleware/             # FastAPI middleware
│   ├── 📁 ml/                     # ML-related code (calibration)
│   │   └── 📁 training/
│   │       └── 📄 calibrate.py    # Threshold calibration tool
│   ├── 📁 presentation/           # API presentation layer
│   ├── 📁 routes/                 # FastAPI route definitions (25 modules)
│   ├── 📁 schemas/                # Pydantic request/response schemas
│   ├── 📁 scripts/                # Utility scripts
│   ├── 📁 services/               # Business logic services (40 modules)
│   ├── 📁 tests/                  # Pytest test suite
│   └── 📄 main.py                 # Application entry point
│
├── 📁 frontend/                   # React frontend application
│   ├── 📁 public/                 # Static assets
│   ├── 📁 src/
│   │   ├── 📁 components/         # React components
│   │   ├── 📁 pages/              # Page-level components
│   │   ├── 📁 services/           # API client services
│   │   └── 📁 utils/              # Utility functions
│   ├── 📄 package.json            # Node.js dependencies
│   └── 📄 tailwind.config.js      # Tailwind CSS configuration
│
├── 📁 data/                       # Data files and exports
├── 📁 alembic/                    # Database migrations
├── 📁 docker/                     # Docker configuration
├── 📁 docs/                       # Documentation
│   ├── 📄 API_REFERENCE.md        # Detailed API docs
│   ├── 📄 ARCHITECTURE.md         # Architecture decisions
│   └── 📄 DEPLOYMENT.md           # Deployment guide
│
├── 📁 models/                     # Trained ML models (future use)
├── 📁 prompts/                    # LLM prompt templates
├── 📁 scripts/                    # Shell scripts
│   └── 📄 smoke_test.sh           # Integration smoke tests
│
├── 📄 .env.example                # Environment template
├── 📄 requirements.txt            # Python dependencies
├── 📄 requirements-dev.txt        # Dev dependencies
├── 📄 pytest.ini                # Pytest configuration
├── 📄 mypy.ini                  # Type checking configuration
├── 📄 SECURITY.md               # Security policy
├── 📄 CODE_OF_CONDUCT.md        # Community guidelines
└── 📄 README.md                 # This file
```

### Key Files Explained

| Path | Purpose |
|------|---------|
| `backend/main.py` | FastAPI application factory, middleware registration |
| `backend/routes/` | 25 route modules covering all API endpoints |
| `backend/services/` | 40 service modules with business logic |
| `backend/ingestion/` | Excel processing pipeline with validation |
| `backend/database/models/` | SQLAlchemy ORM models |
| `frontend/src/` | React components and pages |
| `.env.example` | Comprehensive environment variable template |
| `alembic/versions/` | Database migration history |

---

---

## 🔐 Configuration & Environment Variables

### Security Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SECRET_KEY` | string | — | **Yes** | JWT signing key (min 32 chars) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | 30 | No | JWT expiry time |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | 7 | No | Refresh token expiry |
| `INTEGRATION_API_KEY_HASH` | string | — | No | API key hash for external integrations |
| `CORS_ORIGINS` | string | `http://localhost:3000` | No | Comma-separated allowed origins |

### Database Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DATABASE_URL` | string | `sqlite:///./data/meridian.db` | No | SQLAlchemy connection string |

### Redis Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `REDIS_URL` | string | `redis://localhost:6379` | No | Redis connection for distributed lock |

### Server Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ENVIRONMENT` | string | `development` | No | `development` / `staging` / `production` |
| `DEBUG` | bool | `false` | No | Enable debug logging |
| `PORT` | int | 8000 | No | Server port |
| `API_HOST` | string | `0.0.0.0` | No | FastAPI bind host |

### Ingestion Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `TRIMESTER_START_DATE` | date | — | No | Academic trimester start (YYYY-MM-DD) |
| `CURRENT_SEMESTER_NAME` | string | — | No | e.g. "T1-2025" |
| `MAX_UPLOAD_SIZE_MB` | int | 50 | No | Excel file size limit |
| `ENABLE_STUDENT_DEACTIVATION` | bool | `true` | No | Auto-deactivate missing students |
| `ENGAGEMENT_DATA_FILE` | string | `Engagement_Analysis.xlsx` | No | Primary data filename |

### Risk Scoring Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `THRESHOLD_NO_ACTION` | float | 29.0 | No | Max score for "on track" |
| `THRESHOLD_GENTLE` | float | 49.0 | No | Max score for "gentle reminder" |
| `THRESHOLD_MENTOR` | float | 69.0 | No | Max score for "mentor outreach" |
| `THRESHOLD_URGENT` | float | 89.0 | No | Max score for "urgent" |
| `RISK_SPIKE_THRESHOLD` | float | 15.0 | No | Min delta for "spike" pattern |
| `INTERVENTION_COOLDOWN_DAYS` | int | 7 | No | Days between interventions |

### Feature Weights (Must Sum to 1.0)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WEIGHT_CONTENT_COMPLETION` | float | 0.25 | Content visit rate weight |
| `WEIGHT_LOGIN_CONSISTENCY` | float | 0.20 | Login regularity weight |
| `WEIGHT_QUIZ_ENGAGEMENT` | float | 0.20 | Quiz performance weight |
| `WEIGHT_ASSIGNMENT_SUBMISSION` | float | 0.15 | Assignment submission weight |
| `WEIGHT_TIME_INVESTMENT` | float | 0.10 | Time spent weight |
| `WEIGHT_DISCUSSION_PARTICIPATION` | float | 0.10 | Discussion forum weight |
| `WEIGHT_SELF_DIRECTED_LEARNING` | float | 0.05 | Self-study indicator weight |

### Calendar Scorer Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CALENDAR_RISK_BLEND_WEIGHT` | float | 0.3 | Weight for calendar vs historical blend |
| `ENABLE_CALENDAR_SCORER` | bool | `true` | Enable calendar-aware risk adjustment |

### LLM/AI Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `LLM_PROVIDER` | string | `gemini` | No | Provider: `gemini` or `claude` |
| `GEMINI_API_KEY` | string | — | No | Gemini API key |
| `GEMINI_MODEL` | string | `gemini-1.5-pro-002` | **Yes** | Pinned model version |
| `CLAUDE_API_KEY` | string | — | No | Claude API key |
| `CLAUDE_MODEL` | string | `claude-3-5-sonnet-20241022` | No | Claude model name |
| `LLM_TIMEOUT_SECONDS` | int | 30 | No | LLM request timeout |
| `LLM_MAX_TOKENS` | int | 1024 | No | Max tokens in response |
| `LLM_TEMPERATURE` | float | 0.3 | No | Sampling temperature |
| `ENABLE_LLM_FEATURES` | bool | `true` | No | Master LLM feature toggle |

### Logging & Monitoring

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_FILE` | string | `logs/meridian.log` | Log file path |
| `LOG_LEVEL` | string | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `LOG_ROTATION_MAX_BYTES` | int | 52428800 | 50MB per file |
| `LOG_ROTATION_BACKUP_COUNT` | int | 5 | Number of backup files |
| `ALERT_WEBHOOK_URL` | string | — | Webhook for ingestion failure alerts |

### Feature Flags

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_CALENDAR_SCORER` | bool | `true` | Enable calendar-based risk adjustments |
| `ENABLE_LLM_FEATURES` | bool | `true` | Enable LLM-powered endpoints |
| `ENABLE_STUDENT_DEACTIVATION` | bool | `true` | Enable auto-deactivation |

### Business Metrics (for ROI Calculations)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AVERAGE_STUDENT_LTV` | float | 150000.0 | Lifetime value per student |
| `TUITION_PER_SEMESTER` | float | 75000.0 | Semester tuition amount |
| `INTERVENTION_COST_PER_STUDENT` | float | 500.0 | Average intervention cost |
| `TARGET_RETENTION_RATE` | float | 0.90 | Target retention percentage |

---

## 📡 API Documentation

### Authentication Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| `POST` | `/api/v1/auth/login` | No | — | Username/password login |
| `POST` | `/api/v1/auth/refresh` | No | — | Refresh access token |
| `GET` | `/api/v1/auth/me` | Yes | — | Current user profile |

**Example Login Request:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "dev_admin",
    "password": "changeme_local_only"
  }'
```

**Example Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "role": "admin"
}
```

### Student Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| `GET` | `/api/v1/students` | Yes | staff | List students with pagination |
| `GET` | `/api/v1/students/{id}` | Yes | staff | Student detail with risk profile |
| `GET` | `/api/v1/students/{id}/weekly-summary` | Yes | staff | Weekly engagement summary |
| `GET` | `/api/v1/students/{id}/risk-trend` | Yes | staff | Risk score history |
| `GET` | `/api/v1/students/{id}/interventions` | Yes | staff | Intervention history |

### Intervention Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| `GET` | `/api/v1/interventions` | Yes | staff | List interventions |
| `POST` | `/api/v1/interventions` | Yes | staff | Create intervention |
| `PUT` | `/api/v1/interventions/{id}` | Yes | staff | Update intervention |
| `DELETE` | `/api/v1/interventions/{id}` | Yes | admin | Delete intervention |
| `POST` | `/api/v1/interventions/{id}/act` | Yes | advisor | Mark acted upon |
| `POST` | `/api/v1/interventions/{id}/dismiss` | Yes | advisor | Dismiss recommendation |
| `GET` | `/api/v1/interventions/pending` | Yes | advisor | Pending queue by priority |

### Admin - Ingestion Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| `POST` | `/api/v1/admin/ingest` | Yes | admin | Upload Excel file |
| `GET` | `/api/v1/admin/ingest/status/{task_id}` | Yes | admin | Check task status |
| `GET` | `/api/v1/admin/ingestion-runs` | Yes | admin | List ingestion history |
| `POST` | `/api/v1/admin/run-predictions` | Yes | admin | Trigger risk scoring |

### Admin - Data Management

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| `GET` | `/api/v1/admin/students` | Yes | admin | All students (including inactive) |
| `POST` | `/api/v1/admin/students/{id}/reactivate` | Yes | admin | Reactivate student |
| `DELETE` | `/api/v1/admin/students/{org_id}/erase` | Yes | admin | GDPR erasure |
| `GET` | `/api/v1/admin/students/{org_id}/data-export` | Yes | admin | GDPR export |

### Admin - Configuration

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| `GET` | `/api/v1/config/thresholds` | Yes | admin | Get current thresholds |
| `PUT` | `/api/v1/config/thresholds` | Yes | admin | Update thresholds |
| `GET` | `/api/v1/config/feature-weights` | Yes | admin | Get feature weights |
| `PUT` | `/api/v1/config/feature-weights` | Yes | admin | Update weights |
| `GET` | `/api/v1/admin/audit-log` | Yes | admin | FERPA audit trail |

### LLM / AI Endpoints (Optional)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| `POST` | `/api/v1/llm/risk-explanation` | Yes | staff | LLM risk summary |
| `POST` | `/api/v1/llm/intervention-suggestions` | Yes | staff | LLM intervention ideas |
| `POST` | `/api/v1/llm/report-narrative` | Yes | staff | LLM report generation |
| `POST` | `/api/v1/llm/what-if` | Yes | staff | LLM scenario simulation |
| `GET` | `/api/v1/llm/status` | Yes | — | LLM service health |

### Health & Monitoring

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | No | Service health check |
| `GET` | `/api/v1/health/detailed` | Yes (admin) | Detailed health with ingestion staleness |

### Full API Schema

Interactive API documentation available at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## 🧪 Testing

### Running Tests

```bash
# Full test suite
pytest backend/tests/ -v

# Specific test modules
pytest backend/tests/test_intervention_chain.py -v
pytest backend/tests/test_critical_paths.py -v
pytest backend/tests/test_department_assignment.py -v

# With coverage report
pytest backend/tests/ --cov=backend --cov-report=html

# Type checking
mypy backend/

# Smoke tests (requires running server)
bash scripts/smoke_test.sh
```

### Test Structure

| Test Category | Location | Coverage |
|-------------|----------|----------|
| Unit Tests | `backend/tests/unit/` | Services, utilities |
| Integration Tests | `backend/tests/integration/` | API endpoints, auth flows |
| Security Tests | `backend/tests/security/` | JWT, RBAC, rate limiting |
| ML Tests | `backend/tests/ml/` | Scoring, calibration |

### Threshold Calibration Testing

Run after each trimester to validate risk thresholds:

```bash
python -m backend.ml.training.calibrate
```

**When to run:**
- After T1/T2/T3 exam results are ingested
- Before configuring thresholds for next trimester
- When risk score distribution seems misaligned with actual outcomes

**Sample Output:**
```
Recommended thresholds:
  THRESHOLD_NO_ACTION: 28.5
  THRESHOLD_GENTLE: 48.2
  THRESHOLD_MENTOR: 68.7
  THRESHOLD_URGENT: 88.3

Recommended weights:
  WEIGHT_CONTENT_COMPLETION: 0.27
  ...
```

---

## ⚠️ Known Issues & Limitations

### Current Constraints

1. **Rule-Based Scoring Only**
   - The risk formula has not been validated against historical dropout outcomes
   - Run `backend/ml/training/calibrate.py` after each trimester to calibrate thresholds
   - **Mitigation:** Post-trimester analysis provides recommended adjustments

2. **Limited Calendar-Aware Courses**
   - CalendarAwareScorer only covers 10 specifically configured courses
   - All other courses receive no calendar-based risk adjustment
   - **Mitigation:** Course registry can be extended via admin API

3. **Development Database Limitations**
   - Default SQLite has single-writer constraints
   - Not suitable for production with >500 concurrent users
   - **Mitigation:** PostgreSQL migration path is fully supported

4. **Single-Worker Deployment Constraint**
   - Asyncio/Redis ingestion lock requires single-process deployment
   - Multi-worker scaling requires additional coordination architecture
   - **Mitigation:** Documented in `docs/adr/ADR-002.md`

5. **LLM Data Processing Agreement Required**
   - LLM features require signed DPA with provider before production use
   - **Mitigation:** All LLM features can be disabled; core system works without them

6. **Frontend Authentication**
   - React frontend uses hardcoded demo credentials in development
   - **Mitigation:** Production requires full JWT integration (documented)

### Troubleshooting Common Issues

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| All students show 0% content completion | Ingestion failed | Check `GET /api/v1/admin/ingestion-runs`, verify Excel columns |
| Empty student list by risk range | No risk snapshots | Run `POST /api/v1/admin/run-predictions` or wait for scheduled job |
| Ingestion task stuck at "pending" | Redis lock contention | Clear lock: `redis-cli DEL "ews_ingestion_lock"` |
| All students showing "urgent" | Thresholds misconfigured | Run calibration script, update `.env` |
| LLM 500 errors | API key/model issue | Check `GEMINI_API_KEY`, verify pinned model version |

---

## 🔮 Future Improvements & Roadmap

### Near-Term (Next 3 Months)

#### Feature Enhancements
- [ ] **Mobile Advisor App**: React Native companion for on-the-go intervention logging
- [ ] **Bulk Intervention Actions**: Select multiple students for simultaneous outreach
- [ ] **Custom Alert Rules**: User-configurable notification triggers beyond default thresholds
- [ ] **Multi-Semester Trend Analysis**: Longitudinal student risk tracking across trimesters

#### Performance Optimizations
- [ ] **Database Query Optimization**: Add composite indexes for common query patterns
- [ ] **Redis Caching Layer**: Cache risk snapshots for dashboard loading
- [ ] **Async Prediction Pipeline**: Move risk scoring to background workers

### Medium-Term (3-6 Months)

#### Scalability Improvements
- [ ] **Multi-Worker Architecture**: Implement coordinated distributed locking for horizontal scaling
- [ ] **Read Replicas**: Support PostgreSQL read replicas for reporting queries
- [ ] **CDN Integration**: Serve static frontend assets via CDN

#### Security Enhancements
- [ ] **OAuth 2.0 / SSO**: Integrate with institutional identity providers
- [ ] **Row-Level Security**: Database-level enforcement of student data access
- [ ] **Audit Log Streaming**: Real-time audit log streaming to SIEM

#### AI/ML Evolution
- [ ] **Trained ML Model**: Optional XGBoost classifier trained on historical outcomes
- [ ] **Feature Importance Analysis**: Explain which factors drive risk per student
- [ ] **Predictive Intervention Timing**: ML-suggested optimal outreach moments

### Long-Term (6-12 Months)

#### Platform Expansion
- [ ] **LMS Integration API**: Direct Brightspace/D2L API integration (no Excel)
- [ ] **Third-Party Integrations**: Zoom attendance, library system data
- [ ] **Parent/Guardian Portal**: Optional family visibility into student engagement
- [ ] **Chatbot Advisor**: LLM-powered conversational interface for students

#### Advanced Analytics
- [ ] **Cohort Comparison**: Benchmark retention across programs/years
- [ ] **Intervention Efficacy Dashboard**: A/B testing framework for outreach methods
- [ ] **Dropout Prediction**: Early warning 4-6 weeks in advance
- [ ] **Revenue Impact Modeling**: ROI calculator for retention investments

### Technical Debt
- [ ] **Complete Bounded Context Migration**: Finish refactor from `app/routes` to domain packages
- [ ] **Async Database Layer**: Fully async SQLAlchemy operations
- [ ] **API Versioning**: Implement v2 API with improved pagination and filtering

---

## 🤝 Contributing Guidelines

We welcome contributions from the community! Please follow these guidelines:

### Getting Started

1. **Fork the repository** and create your branch from `main`
2. **Set up your development environment** following the Installation Guide
3. **Run tests** to ensure baseline functionality: `pytest backend/tests/ -v`

### Branch Naming Convention

| Prefix | Use Case | Example |
|--------|----------|---------|
| `feature/` | New features | `feature/calendar-scoring-v2` |
| `fix/` | Bug fixes | `fix/ingestion-timeout` |
| `chore/` | Maintenance | `chore/update-dependencies` |
| `docs/` | Documentation | `docs/api-examples` |

### Code Quality Standards

Before submitting a PR:

```bash
# Run all tests
pytest backend/tests/ -v --tb=short

# Type checking
mypy backend/

# Security scan
bandit -r backend/

# Linting
flake8 backend/ --count --statistics

# Smoke tests (if server running)
bash scripts/smoke_test.sh

# Verify no secrets leaked
git-secrets --scan
```

### Database Migrations

Any model changes must include a migration:

```bash
# Generate migration
alembic revision --autogenerate -m "Add X to Y"

# Review and edit generated file to ensure downgrade() is complete

# Test migration
alembic upgrade head
alembic downgrade -1  # Verify reversibility
alembic upgrade head
```

### Pull Request Process

1. **Update documentation** for any changed functionality
2. **Add tests** for new features or bug fixes
3. **Ensure CI passes** (tests, type checks, security scan)
4. **Request review** from at least one maintainer
5. **Squash commits** before merge for clean history

### Code of Conduct

Please read our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community standards.

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2026 BITS Pilani Digital

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 👨‍💻 Authors & Acknowledgements

### Core Team

| Role | Name | Contribution |
|------|------|--------------|
| **Lead Architect** | BITS Pilani Digital Engineering Team | System design, risk scoring engine |
| **Backend Engineering** | Backend Development Team | FastAPI implementation, data pipeline |
| **Frontend Engineering** | Frontend Development Team | React dashboard, data visualization |
| **DevOps** | Infrastructure Team | Docker, deployment automation |

### Special Thanks

- **Brightspace/D2L** for LMS data export capabilities
- **Google Gemini & Anthropic Claude** teams for LLM API access
- **FastAPI & SQLAlchemy** communities for excellent documentation
- All beta testers and early adopters who provided feedback

### Third-Party Libraries

This project stands on the shoulders of open-source giants:
- FastAPI for the web framework
- React for the frontend
- SQLAlchemy & Alembic for database management
- Pandas & NumPy for data processing
- Chart.js & Recharts for visualization

---

## 📞 Support & Contact

For questions, bug reports, or feature requests:

- **GitHub Issues**: [Open an issue](../../issues)
- **Documentation**: See [`docs/`](./docs/) directory
  - [`API_REFERENCE.md`](./docs/API_REFERENCE.md) - Detailed API documentation
  - [`ARCHITECTURE.md`](./docs/ARCHITECTURE.md) - Architecture Decision Records
  - [`DEPLOYMENT.md`](./docs/DEPLOYMENT.md) - Production deployment guide
- **Security Issues**: See [SECURITY.md](SECURITY.md) for vulnerability reporting

---

**Version:** 2.1.0  
**Last Updated:** April 2026  
**Maintained by:** BITS Pilani Digital Engineering Team

