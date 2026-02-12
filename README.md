# AI-Based Early Warning System (EWS) for Student Retention

## Overview

An AI-driven Early Warning System that monitors student engagement, predicts dropout risk using machine learning, and provides real-time decision intelligence to faculty, sales, and marketing teams.

Designed for EdTech companies and educational institutions to proactively identify at-risk learners and optimize retention, revenue, and learning outcomes.

## Architecture

```
Student Data (CSV, 5000 students) --> SQLite Database
                                        |
                                        v
                Feature Engineering (36 features: 7-year averages + 3-year trends)
                                        |
                                        v
                ML Pipeline (XGBoost/RandomForest + SMOTE) --> Risk Scores [0-100]
                                        |
                                        v
        FastAPI Backend (35+ endpoints) <--> React Frontend (13 pages, 50+ components)
                                        |
                                        v
                Google Gemini --> RAG-grounded AI Recommendations
```

This creates a closed-loop **predict -> act -> improve** retention system.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python, SQLAlchemy |
| ML | XGBoost, scikit-learn, SMOTE (imbalanced-learn) |
| Database | SQLite |
| Frontend | React 18, React Router, Chart.js, Recharts, Framer Motion, Bootstrap |
| AI/LLM | Google Gemini (`google-generativeai`), RAG Engine |
| Deployment | Docker Compose |

## Core Capabilities

### Behavioral Monitoring
Ingests data from 5 sources via dedicated API endpoints:
- Learning Management Systems (logins, assignments, grades)
- Zoom / live classes (attendance, duration)
- Website and app usage (videos, clicks)
- WhatsApp / Email engagement
- Marketing campaigns (Meta, Ads, lead source)

### ML Dropout Prediction
- 7 years of student metrics (absence rates, suspensions, mobility, quarterly GPA)
- 36 engineered features with rolling 3-year trends
- XGBoost classifier with SMOTE for class imbalance handling
- Multi-layer validation ensuring predictions never return invalid values
- 5 signal categories: academic, engagement, consistency, intent, responsiveness

### Decision Engine
Automated intervention triggers based on risk thresholds:
- `<30%`: No action
- `30-60%`: Gentle reminder (automated email)
- `60-80%`: Mentor outreach (faculty + mentor call)
- `>=80%`: Urgent intervention (sales call + WhatsApp + incentive)

### AI Recommendation Engine (LLM)
- RAG-grounded responses using actual student/cohort data
- Hallucination prevention with confidence scoring
- Role-based prompts: faculty, sales, marketing, student-specific
- Features: risk explanations, what-if simulations, study plans, weekly briefs, priority queues, pattern discovery

### Frontend Dashboard
13 pages with 50+ components organized by domain:
- **Dashboard**: KPIs, risk distribution, AI insights, priority alerts
- **Students**: Filterable table, comparison modal, student drawer
- **Student Profile**: Risk breakdown, timeline, interventions, AI advice
- **Student Portal**: Health score, what-if simulator, micro-goals, weekly progress
- **Faculty Tools**: AI summaries, priority queue, similar students, annotations
- **Business Intelligence**: Revenue at risk, retention funnel, intervention ROI
- **Analytics**: Risk trends, scatter analysis, cohort diagnostics
- **Interventions**: Library, tracking, assignment wizard
- **Reports**: Templates, scheduling, AI-generated narratives
- **Risk Factors**: Weight configuration for risk model
- **Settings**: System configuration

## Project Structure

```
ews-retention-platform/
├── backend/
│   ├── main.py                          # FastAPI app entry point
│   ├── database.py                      # Database initialization and session management.
│   ├── config.py                        # Environment configuration
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py                  # FastAPI dependencies (DB session, RBAC)
│   │   │   └── routes/
│   │   │       ├── advisor.py           # AI academic advisor related endpoints
│   │   │       ├── business.py          # Business intelligence related endpoints
│   │   │       ├── decisions.py         # Intervention recommendation & execution endpoints
│   │   │       ├── events.py            # Event ingestion endpoints
│   │   │       ├── features.py          # Feature computation & signal summaries endpoints
│   │   │       ├── feedback.py          # Intervention response tracking endpoints
│   │   │       ├── llm.py               # LLM related endpoints (explain, advise, simulate)
│   │   │       ├── predictions.py       # Single & batch predictions endpoints
│   │   │       ├── recommendations.py   # Intervention suggestions endpoints
│   │   │       └── students.py          # Student CRUD + analytics endpoints
│   │   ├── database/
│   │   │   ├── connection.py            # DB connection setup
│   │   │   ├── session.py               # Session management
│   │   │   └── queries.py               # Query helpers
│   │   ├── models/                      # SQLAlchemy ORM models
│   │   │   ├── student.py               # Student (7-year metrics)
│   │   │   ├── prediction.py            # Prediction (risk, engagement, signals)
│   │   │   ├── intervention.py          # Intervention tracking
│   │   │   ├── event.py                 # RawEvent + EngineeredFeatures
│   │   │   ├── feature.py               # StudentResponse (feedback)
│   │   │   └── llm.py                   # LLMQuery, LLMInsight, AIExplanation, PatternDiscovery
│   │   ├── schemas/                     # Pydantic validation schemas
│   │   │   ├── student.py, prediction.py, intervention.py
│   │   │   ├── event.py, llm.py, common.py
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   │   ├── llm_orchestrator.py  # Central LLM coordination
│   │   │   │   ├── rag_engine.py        # Retrieval-augmented generation
│   │   │   │   ├── hallucination_guard.py # Response validation
│   │   │   │   ├── advisor.py           # AI academic advisor
│   │   │   │   ├── study_plan_generator.py
│   │   │   │   ├── faculty_summary.py
│   │   │   │   └── advisor_context.py
│   │   │   ├── analytics/
│   │   │   │   ├── pattern_discovery.py # Systemic issue detection
│   │   │   │   └── intervention_intel.py # Evidence-based recommendations
│   │   │   ├── core/
│   │   │   │   ├── ews_engine.py        # Risk calculation orchestration
│   │   │   │   ├── decision_engine.py   # Intervention threshold logic
│   │   │   │   ├── feature_service.py   # 5-category signal computation
│   │   │   │   └── data_ingestion.py    # CSV data loading
│   │   │   └── infrastructure/
│   │   │       ├── scheduler.py         # Background job scheduling
│   │   │       ├── audit_logger.py      # RBAC audit trails
│   │   │       └── recommender.py       # Basic recommendations
│   │   └── utils/                       # (Currently empty)
│   ├── ml/
│   │   ├── config.py                    # ML configuration
│   │   ├── features/
│   │   │   └── feature_engineering.py   # 36 feature creation (averages + trends)
│   │   ├── inference/
│   │   │   ├── predictor.py             # Multi-layer validated prediction
│   │   │   └── risk_formula.py          # Risk explanation & what-if simulation
│   │   ├── models/
│   │   │   └── model_registry.py        # Model loading & caching
│   │   └── training/
│   │       ├── train.py                 # XGBoost training with SMOTE
│   │       └── evaluate.py              # Model evaluation
│   ├── data/
│   │   ├── Engagement_Analysis.xlsx     # Raw engagement analysis data
│   │   └── labels.csv                   # Data labels for ML models
│   └── tests/
│       ├── test_llm_services.py
│       ├── test_risk_scoring.py
│       └── test_risk_validation.py
├── frontend/
│   ├── package.json
│   ├── public/
│   │   └── data/
│   │       └── student_data_test.csv   # Frontend fallback data
│   └── src/
│       ├── App.js                       # Route definitions (13 pages)
│       ├── api.js                       # API client with CSV fallback
│       ├── chartConfig.js               # Chart.js registration
│       ├── design-system.css            # 570-line design system
│       ├── index.js                     # React entry point
│       ├── context/
│       │   └── StudentContext.js        # Global state (students + predictions)
│       ├── components/
│       │   ├── ai/                      # AI-powered components (10 files)
│       │   ├── analytics/               # Analytics visualizations
│       │   ├── business/                # Business intelligence components
│       │   ├── common/                  # Shared UI (Layout, Spinner, Skeleton, etc.)
│       │   ├── dashboard/               # Dashboard-specific components
│       │   ├── interventions/           # Intervention management
│       │   ├── quality/                 # Data quality & bias indicators
│       │   └── student/                 # Student profile components
│       ├── pages/                       # 13 page components
│       ├── hooks/                       # useStudentRisk, useIntervention
│       ├── services/                    # studentService, businessService
│       ├── constants/                   # Risk thresholds
│       └── utils/                       # Validators, calculators, generators
├── prompts/
│   ├── faculty_advice.txt               # Faculty intervention prompt
│   ├── marketing_advice.txt             # Marketing outreach prompt
│   ├── sales_advice.txt                 # Sales conversation prompt
│   └── student_specific_advice.txt      # Student coaching prompt
├── docs/
│   ├── LLM_ARCHITECTURE.md             # LLM integration design
│   ├── FACULTY_AI_GUIDE.md             # Faculty user guide
│   ├── STUDENT_AI_GUIDE.md             # Student user guide
│   └── llm_security_architecture.md    # Security & RBAC details
├── docker/
│   └── docker-compose.yml              # 3 services: backend, scheduler, frontend
├── scripts/
│   └── generate_data_catalog.py         # Script for generating data catalog
├── .env.example                         # Environment variable template
├── requirements.txt                     # Python dependencies
├── seed_db.py                          # Database seeding script
├── SETUP.md                            # Setup & deployment guide
├── TESTING.md                          # Testing guide
└── DEPLOYMENT_NOTES.md                 # Deployment notes
```

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js (LTS version)
- Docker (for containerized deployment)

### Backend Setup
```bash
# Navigate to project root
cd ews-retention-platform

# Create and activate a virtual environment
python3 -m venv backend/venv
source backend/venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file from the example
cp .env.example .env

# IMPORTANT: Edit .env and add your Google Gemini API Key
# GEMINI_API_KEY=your_api_key_here

# Run the backend server
uvicorn backend.main:app --reload
```
The backend will be available at `http://localhost:8000`. API documentation can be accessed at `http://localhost:8000/docs`. Database initialization and data ingestion happen automatically on startup.

### Frontend Setup
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm start
```
The frontend will be available at `http://localhost:3000`.

### ML Model Training
To retrain the machine learning model:
```bash
# Ensure your virtual environment is active
source backend/venv/bin/activate

# Run the training script
python -m backend.ml.training.train
```

### Running Tests
```bash
# Run backend tests with verbose output
pytest backend/tests/ -v

# Run backend tests with coverage report
pytest backend/tests/ --cov=backend

# Run frontend tests with coverage
cd frontend && npm test -- --coverage
```

## API Endpoints

### Core
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/students/` | List students (paginated, filterable) |
| GET | `/students/{id}` | Student detail |
| GET | `/predictions/batch` | All predictions |
| GET | `/predictions/{id}` | Single prediction |
| GET | `/decisions/{id}` | Intervention recommendation |
| POST | `/decisions/execute` | Execute intervention |

### AI/LLM
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/llm/explain-risk-change` | Why risk changed |
| POST | `/llm/student-advice` | Personalized advice |
| POST | `/llm/what-if-simulation` | Scenario analysis |
| POST | `/llm/faculty-summary` | Faculty-oriented summary |
| POST | `/llm/intervention-suggestions` | Evidence-based interventions |
| GET | `/llm/prioritize-students` | Priority queue |
| GET | `/llm/institutional-insights` | System-wide patterns (admin) |

### Business Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/business/metrics/retention` | Retention KPIs |
| GET | `/business/metrics/revenue-at-risk` | Revenue impact |
| GET | `/business/metrics/intervention-roi` | ROI analysis |
| GET | `/business/funnel` | Retention funnel |
| GET | `/business/executive-summary` | Executive dashboard (admin) |

## Environment Variables

This system is configured via environment variables. See `.env.example` for the complete list.

### Key Variables
| Variable | Description | Default |
|---|---|---|
| **`GEMINI_API_KEY`** | **Required for all AI features.** | `your_api_key_here` |
| `DATABASE_URL` | Connection string for the database. | `sqlite:///./backend/data/sql_app.db` |
| `MODEL_TYPE` | Specifies the ML model to use. | `xgboost` |
| `SCHEDULER_ENABLED` | Toggles the background job scheduler. | `true` |
| `PREDICTION_UPDATE_INTERVAL`| Frequency of prediction updates in seconds. | `3600` |
| `LOG_LEVEL` | Logging level for the application. | `INFO` |

### Risk & Intervention Thresholds
| Variable | Description | Default |
|---|---|---|
| `RISK_THRESHOLD_HIGH` | Risk score above which a student is "High Risk". | `0.7` |
| `RISK_THRESHOLD_MEDIUM` | Risk score above which a student is "Medium Risk".| `0.4` |
| `THRESHOLD_GENTLE` | Risk score to trigger a gentle intervention. | `0.60` |
| `THRESHOLD_MENTOR` | Risk score to trigger a mentor outreach. | `0.80` |

### Signal Weights
These weights control the contribution of each signal category to the final risk score. **They must sum to 1.0.**
| Variable | Description | Default |
|---|---|---|
| `WEIGHT_ACADEMIC` | Weight for academic performance signals. | `0.30` |
| `WEIGHT_ENGAGEMENT` | Weight for student engagement signals. | `0.25` |
| `WEIGHT_CONSISTENCY`| Weight for behavioral consistency signals. | `0.20` |
| `WEIGHT_INTENT` | Weight for signals indicating student intent. | `0.15` |
| `WEIGHT_RESPONSIVENESS`| Weight for signals on responsiveness to outreach. | `0.10` |

### Business Metrics
| Variable | Description | Default |
|---|---|---|
| `AVERAGE_STUDENT_LTV` | Average Lifetime Value of a student. | `12500.0` |
| `INTERVENTION_COST` | Average cost of one intervention cycle. | `350.0` |

## RBAC (Role-Based Access Control)

Access is controlled via the `X-User-Role` HTTP header on API requests.
- **`student`**: Access to their own data and the student portal features.
- **`faculty`**: Access to their assigned students, AI summaries, and intervention tools.
- **`admin`**: Full access, including institutional insights and executive summaries.
- **`sales`**: Access to business metrics and revenue analysis.

## Docker Deployment

The `docker-compose.yml` file in the `docker/` directory defines three services for a containerized deployment:

- **`backend`**: The FastAPI application. Builds from the project root and runs on port `8000`.
- **`scheduler`**: A separate container that runs the background job scheduler (`python -m backend.services.scheduler`).
- **`frontend`**: The React application. Builds from the `frontend/` directory and is served on port `3000`.

To build and run the entire application with Docker:
```bash
# Navigate to the docker directory
cd docker

# Build and start the services
docker-compose up --build
```

## Use Cases
- Detect early signs of student disengagement
- Predict dropout before it happens
- Improve teaching and mentoring strategies with AI-powered insights
- Optimize marketing campaigns and retention outreach
- Translate academic risk into revenue impact for business stakeholders

## Contributing
Contributions, ideas, and improvements are welcome.
Feel free to open an issue or submit a pull request.
