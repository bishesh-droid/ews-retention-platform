# EWS Retention Platform (Meridian)

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.119.0-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2.0-61DAFB?logo=react)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Early Warning System for Student Retention** — An AI-powered platform that identifies at-risk students using LMS engagement data and enables proactive interventions.

---

## Overview

The EWS Retention Platform (codenamed "Meridian") is a comprehensive system designed to predict and prevent student dropout in educational institutions. It ingests Learning Management System (LMS) data from Excel exports, applies behavioral feature engineering and risk scoring algorithms, and presents actionable insights through an interactive dashboard.

**Core Value Proposition:**
- **Early Identification:** Detect at-risk students before they withdraw
- **Data-Driven Interventions:** Prioritize outreach based on calculated risk scores
- **Multi-Role Support:** Tailored interfaces for faculty, advisors, retention teams, and administrators
- **AI-Powered Insights:** Optional LLM integration for natural language risk explanations

---

## Features

### Core Capabilities

- **Automated Data Ingestion** — Processes Excel exports from Brightspace LMS on application startup
- **Behavioral Feature Engineering** — Derives 6 engagement signals from raw LMS data:
  - Content completion rate
  - Login consistency patterns
  - Quiz engagement metrics
  - Assignment submission rates
  - Time investment analysis
  - Discussion participation

- **Rule-Based Risk Scoring** — Calculates 0-100 risk scores using weighted feature aggregation
- **Scheduled Predictions** — Daily job (03:00 UTC) recomputes risk scores for all students
- **Risk Trend Tracking** — Historical snapshots enable velocity and acceleration analysis

### API Features (20+ Endpoints)

| Category | Endpoints |
|----------|-----------|
| **Authentication** | JWT-based auth with role-based access control |
| **Students** | CRUD, risk profiles, enrollment data, analytics |
| **Predictions** | Batch predictions, individual risk scoring |
| **Interventions** | Create, track, and measure intervention effectiveness |
| **LLM/AI** | Risk explanations, recommendations, what-if scenarios |
| **Analytics** | Cohort analysis, trend reports, distribution stats |
| **Business Intelligence** | Revenue at risk, ROI calculations, retention funnels |
| **Reporting** | Student-level and cohort-level report generation |

### Frontend Features

- **React SPA** with responsive design
- **Interactive Dashboard** — KPI cards, risk distribution charts, at-risk student tables
- **Student Profiles** — Detailed risk breakdowns with radar charts and trend graphs
- **Intervention Management** — Track and manage student interventions
- **Business Analytics** — Executive-level metrics and ROI analysis
- **AI Components** — Explainable risk narratives and what-if simulators

---

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Faculty    │  │   Student    │  │    Admin     │               │
│  │  Dashboard   │  │    Portal    │  │   Console    │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                  │                  │                     │
│         └──────────────────┼──────────────────┘                     │
│                            ▼                                        │
│                   ┌─────────────────┐                               │
│                   │  React SPA      │                               │
│                   │  (Port 3000)    │                               │
│                   └────────┬────────┘                               │
└────────────────────────────┼─────────────────────────────────────────┘
                             │ HTTP / REST
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       API Layer (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Middleware Stack:                                           │   │
│  │  • Rate Limiting (SlowAPI)                                   │   │
│  │  • CORS Handling                                             │   │
│  │  • Request Validation                                        │   │
│  │  • Security Logging                                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐    │
│  │   Auth     │ │  Students  │ │Interventions│ │  Analytics    │    │
│  │  Routes    │ │  Routes    │ │   Routes    │ │   Routes      │    │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └───────┬────────┘    │ 
│        └──────────────┼───────────────┴─────────────────┘           │
│                       ▼                                             │
│              ┌─────────────────┐                                    │
│              │  Service Layer  │                                    │
│              │  • StudentService│                                   │
│              │  • RiskScorer    │                                   │
│              │  • FeatureEng    │                                   │
│              └────────┬────────┘                                    │
└───────────────────────┼─────────────────────────────────────────────┘
                        │
┌───────────────────────┼─────────────────────────────────────────────┐
│                       ▼                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │ 
│  │                    Data Layer                                │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐  │   │
│  │  │  SQLite    │  │   Redis    │  │   XLSX Files           │  │   │
│  │  │ (Primary)  │  │  (Cache)   │  │  (LMS Data Sources)    │  │   │
│  │  └────────────┘  └────────────┘  └────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Optional: LLM Providers                        │    │
│  │         Google Gemini  │  Anthropic Claude                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Ingestion** — XLSX files parsed at startup, data upserted to SQLite
2. **Feature Engineering** — Raw counters transformed into normalized engagement scores (0-100)
3. **Risk Scoring** — Weighted aggregation produces risk scores with confidence adjustments
4. **Persistence** — Daily scheduler stores predictions and snapshots
5. **API Serving** — Live computation or cached retrieval based on request

---

## Tech Stack

### Backend

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | FastAPI | 0.119.0 |
| Database | SQLAlchemy + SQLite/PostgreSQL | 2.0.45 |
| Data Processing | Pandas, NumPy, OpenPyXL | 2.3.3 |
| ML | scikit-learn, joblib | 1.8.0 |
| Auth | python-jose, passlib, bcrypt | 3.5.0 |
| Scheduling | APScheduler | 3.11.2 |
| Caching | Redis (optional) | 4.6.0 |
| Rate Limiting | SlowAPI | 0.1.9 |
| PDF Generation | fpdf2 | 2.8.6 |

### Frontend

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | React | 18.2.0 |
| Routing | React Router DOM | 6.22.3 |
| Styling | Bootstrap, Tailwind CSS | 5.3.8 |
| Charts | Chart.js, Recharts | 4.4.2 |
| HTTP Client | Axios | 1.6.8 |
| Animation | Framer Motion | 12.31.0 |
| Icons | React Icons | 5.5.0 |

### Infrastructure

| Component | Technology |
|-----------|------------|
| Containerization | Docker, Docker Compose |
| Server | Uvicorn (ASGI) |
| Migrations | Alembic |

---

## Installation

### Prerequisites

- Python 3.11 or higher
- Node.js 18+ and npm 9+
- (Optional) Redis 7+ for caching

### Backend Setup

```bash
# 1. Clone and navigate to repository
cd /path/to/ews-retention-platform

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set SECRET_KEY:
# python -c "import secrets; print(secrets.token_hex(32))"

# 5. Ensure data files exist
# Place Engagement_Analysis.xlsx in backend/data/

# 6. Start server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
# Application available at http://localhost:3000
```

### Docker Deployment

```bash
# Using provided docker-compose
cd docker
docker-compose up -d

# Services:
# - Backend API: http://localhost:8000
# - Frontend: http://localhost:3000
# - Redis: localhost:6379
```

---

## Usage

### Creating an Admin User

```bash
# Option 1: Seed script (development)
python -m backend.scripts.seed_dev_data
# Credentials: dev_admin / changeme_local_only

# Option 2: Manual API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "email": "admin@example.com", "password": "SecurePass123!"}'

# Login to obtain JWT
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d 'username=admin&password=SecurePass123!'
```

### API Examples

```bash
# Health check
curl http://localhost:8000/health

# Get students (requires JWT)
curl http://localhost:8000/api/v1/students/students \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json"

# Get at-risk students
curl "http://localhost:8000/api/v1/students/at-risk?threshold=70&limit=10" \
  -H "Authorization: Bearer <your_token>"

# Create intervention
curl -X POST http://localhost:8000/api/v1/interventions \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "student@example.com",
    "action": "Schedule advising meeting",
    "assigned_faculty": "Dr. Smith",
    "channels": ["email"]
  }'
```

### Running Scheduled Jobs

```bash
# Daily predictions run automatically at 03:00 UTC
# Manual trigger (development):
python -c "from backend.services.infrastructure.scheduler import scheduler_service; scheduler_service.generate_daily_predictions()"

# Feature store pre-computation:
python -m backend.jobs.feature_store_job
```

---

## Folder Structure

```
ews-retention-platform/
├── backend/                      # FastAPI application
│   ├── main.py                   # Application entry point
│   ├── config/                   # Centralized configuration
│   ├── routes/                   # 22 API route modules
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── students.py          # Student management
│   │   ├── interventions.py     # Intervention tracking
│   │   ├── llm.py               # AI/LLM endpoints
│   │   └── ...
│   ├── services/                 # Business logic layer
│   │   ├── feature_engineering.py   # Feature calculation
│   │   ├── risk_scoring.py         # Risk algorithm
│   │   ├── student_service.py      # Student orchestration
│   │   ├── ai/                     # LLM integrations
│   │   │   ├── llm_orchestrator.py
│   │   │   └── rag_engine.py
│   │   └── infrastructure/
│   │       └── scheduler.py        # Background jobs
│   ├── database/
│   │   ├── models/               # 25+ SQLAlchemy models
│   │   ├── connection.py         # Engine configuration
│   │   └── session.py            # Session management
│   ├── core/                     # Auth, security, caching
│   ├── middleware/               # Request processing
│   ├── ml/                       # ML models and inference
│   └── data/                     # SQLite DB + XLSX files
│
├── frontend/                     # React application
│   ├── src/
│   │   ├── App.js               # Route definitions
│   │   ├── pages/               # 15+ page components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Students.jsx
│   │   │   └── ...
│   │   ├── components/          # 60+ reusable components
│   │   ├── context/             # Auth and Student contexts
│   │   └── services/            # API client modules
│   └── package.json
│
├── docker/                       # Docker configuration
│   ├── docker-compose.yml
│   └── Dockerfile
│
├── docs/                         # Additional documentation
│   ├── ADR-001-risk-scoring-approach.md
│   └── ...
│
├── requirements.txt              # Python dependencies
└── .env.example                  # Configuration template
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes (prod) | insecure | JWT signing key |
| `DATABASE_URL` | No | sqlite:///... | Database connection |
| `API_HOST` | No | 0.0.0.0 | Server bind address |
| `API_PORT` | No | 8000 | Server port |
| `CORS_ORIGINS` | No | localhost:3000 | Allowed origins |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 60 | JWT expiry |
| `REDIS_URL` | No | redis://localhost:6379/0 | Cache connection |
| `RISK_THRESHOLD_HIGH` | No | 70.0 | High risk cutoff |
| `RISK_THRESHOLD_MEDIUM` | No | 40.0 | Medium risk cutoff |
| `GEMINI_API_KEY` | No | - | Enable Gemini LLM |
| `CLAUDE_API_KEY` | No | - | Enable Claude LLM |
| `ENVIRONMENT` | No | development | deployment mode |

### Feature Weights

Configure risk scoring weights in `.env`:

```env
WEIGHT_CONTENT_COMPLETION=0.30
WEIGHT_LOGIN_CONSISTENCY=0.20
WEIGHT_QUIZ_ENGAGEMENT=0.20
WEIGHT_ASSIGNMENT=0.15
WEIGHT_TIME_INVESTMENT=0.08
WEIGHT_DISCUSSION=0.02
WEIGHT_SELF_DIRECTED_LEARNING=0.05
```

---

## Security & Limitations

### Current Security Model

- **Backend:** JWT-based authentication with role-based access control
- **Rate Limiting:** In-memory (per-process) — upgrade to Redis for production
- **Password Hashing:** bcrypt with secure defaults
- **Input Validation:** Pydantic schemas with sanitization

### Known Limitations

1. **Frontend Authentication Gap** — React app uses hardcoded credentials for demo purposes. Production requires backend JWT integration.

2. **ML Model Status** — Pre-trained XGBoost/Logistic Regression models exist but have schema mismatches with live data. System falls back to rule-based scoring.

3. **SQLite Constraints** — Single-writer database suitable for single-instance deployment. Consider PostgreSQL for multi-worker setups.

4. **Rate Limiter** — In-memory implementation resets on restart. Use Redis-backed SlowAPI for production.

5. **LLM Fallbacks** — Returns mock responses when API keys absent. Enable real LLM features by adding Gemini or Claude keys.

### Security Recommendations

1. Replace hardcoded frontend auth with proper JWT flow
2. Enable HTTPS with HSTS for production
3. Add email verification for registration
4. Implement per-student data isolation
5. Use Redis for distributed rate limiting

---

## Future Improvements

### Immediate (Production Readiness)

- [ ] Fix frontend authentication to use backend JWT
- [ ] Consolidate risk scoring implementations
- [ ] Standardize risk score representation (0-100 throughout)
- [ ] Implement distributed rate limiting
- [ ] Add comprehensive test suite

### Medium Term

- [ ] Retrain ML models on current feature schema
- [ ] Migrate to PostgreSQL for production
- [ ] Integrate advanced ingestion pipeline
- [ ] Add training label collection workflow
- [ ] Implement feature store pre-computation

### Long Term

- [ ] Real-time LMS data feed (webhooks/API)
- [ ] WebSocket alerts for risk threshold breaches
- [ ] Model drift detection and auto-retraining
- [ ] Prometheus metrics and structured logging
- [ ] Multi-tenant support

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork** the repository
2. Create a **feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. Open a **Pull Request**

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run linting
flake8 backend/

# Run tests (when available)
pytest
```

---

## License

This project is licensed under the MIT License.

---

## Support

For questions or issues:
- Open a GitHub Issue
- Review documentation in `/docs` directory
- Check `ARCHITECTURE.md` for system design details
- See `SECURITY.md` for vulnerability reporting

---

**Version:** 2.1.0  
**Last Updated:** April 2026
