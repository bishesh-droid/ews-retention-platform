# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-driven Early Warning System (EWS) for student retention that monitors engagement, predicts dropout risk using ML, and provides AI-powered recommendations to faculty, sales, and marketing teams.

**Tech Stack:** FastAPI (Python) + React 18 + SQLite + scikit-learn + Google Gemini LLM

## Build & Run Commands

### Backend
```bash
# Activate venv (create with: python3 -m venv backend/venv)
source backend/venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server (port 8000)
uvicorn backend.main:app --reload

# API docs at http://localhost:8000/docs
```

### Frontend
```bash
cd frontend
npm install
npm start          # Development server (port 3000)
npm test           # Run Jest tests
npm run build      # Production build
```

### ML Model
```bash
python models/train_model.py    # Train model → models/saved_models/retention_model.joblib
python models/predict.py        # Test prediction
```

### Tests
```bash
pytest backend/tests/ -v                    # Backend unit tests
pytest backend/tests/ --cov=backend         # With coverage
cd frontend && npm test -- --coverage       # Frontend tests
```

## Architecture

```
Student Data (CSV) → Data Ingestion → SQLite
        ↓
Feature Engineering (35 features) → RandomForest + SMOTE → Risk Scores (0-100%)
        ↓
FastAPI Backend ←→ React Frontend
        ↓
LLM Service (Gemini) → AI Recommendations (RAG-grounded)
```

### Key Architectural Patterns

1. **ML Pipeline**: 7 years of student metrics (absence, suspensions, mobility, GPA) → feature engineering with 3-year trends → RandomForest classifier with SMOTE for class imbalance

2. **LLM Integration**: RAG engine retrieves actual student data before LLM calls; hallucination prevention validates responses; role-based prompts (faculty/sales/marketing/student)

3. **Frontend State**: StudentContext (React Context) caches all students + batch predictions globally; individual pages use local state for filters/sorting

4. **RBAC**: X-User-Role header controls data visibility (student/faculty/admin/sales); audit logger tracks all actions

## Key Files

**Backend Entry Points:**
- `backend/main.py` - FastAPI app setup, CORS, startup events
- `backend/database.py` - SQLAlchemy models (Student, Prediction, Intervention, LLM*)
- `backend/services/ews_engine.py` - `get_student_risk()` wraps ML prediction
- `backend/services/llm_service.py` - LLMOrchestrator for all AI features

**ML Pipeline:**
- `models/feature_engineering.py` - Creates 32 engineered features from raw data
- `models/train_model.py` - RandomForest training with SMOTE balancing

**Frontend Entry Points:**
- `frontend/src/App.js` - Route definitions (13 pages)
- `frontend/src/context/StudentContext.js` - Global state with batch predictions
- `frontend/src/api.js` - Axios client (BaseURL: localhost:8000)

**LLM Prompts:**
- `prompts/faculty_advice.txt`, `prompts/sales_advice.txt`, `prompts/marketing_advice.txt`

## API Endpoints

- `GET /students/` - List all students
- `GET /predictions/{student_id}` - Single prediction
- `GET /predictions/batch` - All predictions (used by frontend context)
- `GET /recommendations/{student_id}` - Intervention suggestions
- `POST /api/llm/*` - LLM endpoints (explain-risk, what-if, summarize, etc.)

## Database Schema (SQLite)

**Student**: id, absrate1-7, nsusp1-7, mobility1-7, q1-4mpa1-7, nograd (target)
**Prediction**: student_id, risk_score, engagement_score, retention_likelihood
**Intervention**: student_id, date, action, ai_suggested, effectiveness_score

## Environment Variables

```bash
GEMINI_API_KEY=your_key_here  # Required for LLM features
```

## Data Flow

1. `simulated_data.csv` (5000 students) ingested to SQLite on startup
2. Feature engineering creates rolling trends and aggregations
3. RandomForest predicts dropout probability (risk_score 0-1)
4. Frontend fetches batch predictions, caches in context
5. LLM endpoints ground responses in actual student/cohort data via RAG
