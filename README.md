# Meridian EWS — Early Warning System for Student Retention

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.119.0-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-pytest-blue)](backend/tests/)

> **BITS Pilani Digital — Student Retention Platform** An Early Warning System that ingests Brightspace LMS data, computes engagement-based risk scores, and routes intervention recommendations to academic advisors.

---

## What this system does

Meridian EWS is a deterministic, rule-based student retention platform designed for the BITS Pilani Digital operations team. It processes weekly Excel exports from Brightspace LMS, applies behavioral feature engineering to compute 0–100 risk scores, and generates intervention recommendations that advisors can act upon through a prioritised queue interface.

The system serves multiple user roles: academic advisors review and act on intervention queues; faculty members view risk summaries for their assigned students; retention team leaders monitor cohort-level trends; and administrators manage data ingestion, user access, and system configuration.

**Important:** This is a rule-based scoring engine, not a trained machine learning model. The risk scores are computed by a deterministic weighted formula across seven engagement features. There is no neural network, XGBoost classifier, or other ML model producing these scores. The optional LLM features (Gemini or Claude integration for natural-language risk explanations) are entirely separate from the core scoring pipeline and can be disabled without affecting risk calculations.

---

## Architecture overview

```
Brightspace Excel exports (weekly)
         ↓
POST /api/v1/admin/ingest
         ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Ingestion Pipeline                                  │
│                                                                              │
│   ┌────────────────────┐   ┌────────────────────┐   ┌────────────────────┐   │
│   │   StudentLoader    │   │     ExamLoader     │   │ OutcomeInferencer  │   │
│   │────────────────────│   │────────────────────│   │────────────────────│   │
│   │ _ensure_student    │   │ _ingest_*          │   │ infer_outcomes_*   │   │
│   │ _deactivate_*      │   │ _ingest_*          │   │ _from_exam_data    │   │
│   └────────────────────┘   └────────────────────┘   └────────────────────┘   │
│             │                         │                        │             │
│             └───────────────┬─────────┴───────────┬────────────┘             │
│                             ▼                     ▼                          │
│        ┌──────────────────────────────────────────────────────────────┐      │
│        │                InterventionBackfiller                        │      │
│        │        backfill_intervention_outcomes()                      │      │
│        └──────────────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                          Database — SQLite / PostgreSQL                                                       │
│                                                                                                               │
│   ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐ │
│   │        students        │ │      enrollments       │ │   graded_components    │ │      exam_records      │ │
│   │────────────────────────│ │────────────────────────│ │────────────────────────│ │────────────────────────│ │
│   │ - id (PK)              │ │ - id                   │ │ - id                   │ │ - id                   │ │
│   │ - org_id               │ │ - student_id           │ │ - student_org_id       │ │ - student_id           │ │
│   │ - email                │ │ - course_code          │ │ - component_type       │ │ - course_code          │ │
│   │ - dept                 │ │ - semester             │ │ - score                │ │ - marks                │ │
│   └────────────────────────┘ └────────────────────────┘ └────────────────────────┘ └────────────────────────┘ │
│                                                                                                               │
│   ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐ ┌────────────────────────┐ │
│   │    risk_snapshots      │ │   intervention_logs    │ │ engineered_features    │ │        course_*        │ │
│   │────────────────────────│ │────────────────────────│ │────────────────────────│ │────────────────────────│ │
│   │ - id                   │ │ - id                   │ │ - id                   │ │ - id                   │ │
│   │ - student_id           │ │ - student_org_id       │ │ - student_id           │ │ - code                 │ │
│   │ - score                │ │ - reviewed             │ │ - computed_at          │ │ - name                 │ │
│   │ - timestamp            │ │ - dismissed            │ │ - quiz_score           │ │ - calendar             │ │
│   └────────────────────────┘ └────────────────────────┘ └────────────────────────┘ └────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Feature Engineering                                   │
│                                                                              │
│  CalendarAwareScorer (optional) + RiskScorer                                 │
│  - Computes engagement features from raw LMS data                            │
│  - Applies calendar-aware adjustments (10 courses only)                      │
│  - Produces 0–100 risk score via weighted formula                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│            Decision Engine — Intervention Router                             │
│                                                                              │
│  get_intervention_recommendation(score, pattern, flags)                      │
│  → ghost / disengaged / struggling / at_risk / on_track                      │
│  → gentle_reminder / mentor_outreach / urgent / none                         │
└──────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│               FastAPI REST API (100+ endpoints)                              │
│  JWT authentication + Role-based access control                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│           React Frontend — Advisor Dashboard                                 │
│  Intervention queue, student profiles, risk trends                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Ingestion Pipeline:** Handles idempotent upsert of student records, exam marks, and attendance data. Automatically deactivates students not present in the latest export (soft delete). Pseudonymises identifiers in audit logs.

**Feature Engineering:** Raw LMS counters (logins, content views, quiz attempts) are normalised to 0–100 engagement scores. The CalendarAwareScorer applies deadline-proximity multipliers for 10 specifically configured courses.

**Risk Scoring:** A deterministic weighted formula across seven features (content completion, login consistency, quiz engagement, assignment submission, time investment, discussion participation, calendar proximity). Output is a 0–100 score with 1 decimal precision.

**Decision Engine:** Maps risk scores and engagement patterns to intervention types. Ghost students (zero logins) trigger "activation outreach". Disengaged students (low login consistency) trigger "mentor outreach". Struggling students (low quiz scores) trigger "academic support".

---

## Risk score interpretation

### How the score is computed

The 0–100 risk score is a weighted aggregation of seven engagement features:

| Feature | Weight | Description |
|---------|--------|-------------|
| Content completion rate | 0.25 | Percentage of course content visited |
| Login consistency | 0.20 | Regularity of LMS logins (streak-based) |
| Quiz engagement | 0.20 | Quiz attempts and scores |
| Assignment submission | 0.15 | On-time submission rate |
| Time investment | 0.10 | Hours spent in LMS per week |
| Discussion participation | 0.10 | Forum posts and replies |
| Calendar proximity | variable | Days until next deadline (10 courses only) |

Weights are configured in `FEATURE_WEIGHTS` and validated at startup (must sum to 1.0 ± 0.01).

### Intervention thresholds

| Score Range | Intervention Type | Risk Band |
|-------------|-------------------|-----------|
| 0–29 | No action | On track |
| 30–49 | Gentle reminder | At risk |
| 50–69 | Mentor outreach | Struggling |
| 70–89 | Urgent intervention | Disengaged |
| 90–100 | Critical alert | Ghost |

Thresholds are configured via `THRESHOLD_NO_ACTION`, `THRESHOLD_GENTLE`, `THRESHOLD_MENTOR`, `THRESHOLD_URGENT`.

### Engagement patterns

| Pattern | Trigger Condition |
|---------|-------------------|
| ghost | Zero logins in past 7 days |
| disengaged | Login consistency score < 30 |
| struggling | Quiz average < 40% AND content completion < 50% |
| on_track | Risk score < 30 AND all feature scores > 60 |

### Important caveats

**This is not a machine learning prediction.** The score is a deterministic weighted formula that has not yet been validated against historical dropout outcomes. The system uses rule-based thresholds, not a trained classifier. Use it as a prioritisation signal for advisor attention, not as a definitive prediction of student withdrawal. Run `python -m backend.ml.training.calibrate` after each trimester to compute recommended thresholds based on actual exam outcomes.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.12.x | Pinned in `.python-version` |
| Redis | 7.x | Required for distributed ingestion lock |
| SQLite | 3.35+ | Default database (development) |
| PostgreSQL | 15+ | Recommended for production |
| Node.js | 18+ | For frontend development only |
| System deps | - | `python-magic` for MIME validation |

---

## Installation and local setup

### Step 1 — Clone

```bash
git clone <repository-url>
cd ews-retention-platform
```

### Step 2 — Python environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### Step 3 — Install backend dependencies

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### Step 4 — Install frontend dependencies (optional)

```bash
cd frontend
npm install
cd ..
```

### Step 5 — Configure environment

```bash
cp .env.example .env
```

**Required values** (startup will fail if missing):

| Variable | Set to |
|----------|--------|
| `SECRET_KEY` | Random 32+ character string |
| `GEMINI_MODEL` | `gemini-1.5-pro-002` (pinned version) |

**Optional values** (system works without them, features degrade gracefully):

| Variable | Effect if missing |
|----------|-------------------|
| `GEMINI_API_KEY` | LLM features return mock responses |
| `CLAUDE_API_KEY` | Claude provider unavailable |
| `REDIS_URL` | Falls back to in-memory lock (single-process only) |
| `ALERT_WEBHOOK_URL` | Ingestion failure alerts disabled |

### Step 6 — Run database migrations

```bash
alembic upgrade head
```

### Step 7 — Seed local dev admin user

```bash
python -m backend.scripts.seed_dev_data
```

Creates:
- Username: `dev_admin`
- Password: `changeme_local_only`
- Roles: `admin`, `faculty`, `retention_team`

### Step 8 — Start Redis

```bash
# Docker
docker run -d -p 6379:6379 redis:alpine

# Or Homebrew (macOS)
brew install redis
redis-server
```

### Step 9 — Start the backend server

```bash
uvicorn backend.main:app --reload --port 8000
```

### Step 10 — Start the frontend (optional)

```bash
cd frontend
npm run dev
```

Frontend available at `http://localhost:3000`

### Step 11 — Verify with smoke test

```bash
bash scripts/smoke_test.sh
```

---

## Configuration reference

### Security

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SECRET_KEY` | string | — | **Yes** | JWT signing key (min 32 chars) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | 30 | No | JWT expiry time |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | 7 | No | Refresh token expiry |
| `INTEGRATION_API_KEY_HASH` | string | — | No | API key for external integrations |

### Database

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DATABASE_URL` | string | `sqlite:///./data/meridian.db` | No | SQLAlchemy connection string |

### Redis

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `REDIS_URL` | string | `redis://localhost:6379` | No | Redis connection for distributed lock |

### Server

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ENVIRONMENT` | string | `development` | No | `development` / `staging` / `production` |
| `DEBUG` | bool | `false` | No | Enable debug logging |
| `PORT` | int | 8000 | No | Server port |

### Ingestion

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `TRIMESTER_START_DATE` | date | — | No | Academic trimester start (YYYY-MM-DD) |
| `CURRENT_SEMESTER_NAME` | string | — | No | e.g., "T1-2025" |
| `MAX_UPLOAD_SIZE_MB` | int | 50 | No | Excel file size limit |
| `ENABLE_STUDENT_DEACTIVATION` | bool | `true` | No | Auto-deactivate missing students |

### Risk scoring thresholds

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `THRESHOLD_NO_ACTION` | float | 29.0 | No | Max score for "on track" |
| `THRESHOLD_GENTLE` | float | 49.0 | No | Max score for "gentle reminder" |
| `THRESHOLD_MENTOR` | float | 69.0 | No | Max score for "mentor outreach" |
| `THRESHOLD_URGENT` | float | 89.0 | No | Max score for "urgent" |
| `RISK_SPIKE_THRESHOLD` | float | 15.0 | No | Min delta for "spike" pattern |

### Feature weights

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `WEIGHT_CONTENT_COMPLETION` | float | 0.25 | No | Feature weight |
| `WEIGHT_LOGIN_CONSISTENCY` | float | 0.20 | No | Feature weight |
| `WEIGHT_QUIZ_ENGAGEMENT` | float | 0.20 | No | Feature weight |
| `WEIGHT_ASSIGNMENT_SUBMISSION` | float | 0.15 | No | Feature weight |
| `WEIGHT_TIME_INVESTMENT` | float | 0.10 | No | Feature weight |
| `WEIGHT_DISCUSSION_PARTICIPATION` | float | 0.10 | No | Feature weight |

**Validation:** Sum must equal 1.0 ± 0.01 (enforced by `validate_ml_config()` at startup).

### Calendar scorer

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CALENDAR_RISK_BLEND_WEIGHT` | float | 0.3 | No | Weight for calendar vs historical blend |
| `ENABLE_CALENDAR_SCORER` | bool | `true` | No | Enable calendar-aware risk adjustment |

### LLM features

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `GEMINI_API_KEY` | string | — | No | Gemini API key |
| `GEMINI_MODEL` | string | `gemini-1.5-pro-002` | **Yes** | Pinned model version |
| `CLAUDE_API_KEY` | string | — | No | Claude API key |
| `LLM_TIMEOUT_SECONDS` | int | 30 | No | LLM request timeout |
| `LLM_MAX_TOKENS` | int | 1024 | No | Max tokens in response |
| `LLM_TEMPERATURE` | float | 0.7 | No | Sampling temperature |
| `ENABLE_LLM_FEATURES` | bool | `true` | No | Enable LLM endpoints |

### CORS

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `CORS_ORIGINS` | string | `http://localhost:3000` | No | Comma-separated allowed origins |

### Logging

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `LOG_FILE` | string | `logs/meridian.log` | No | Log file path |
| `LOG_LEVEL` | string | `INFO` | No | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `LOG_ROTATION_MAX_BYTES` | int | 52428800 | No | 50MB per file |
| `LOG_ROTATION_BACKUP_COUNT` | int | 5 | No | Number of backup files |

### Alerts

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ALERT_WEBHOOK_URL` | string | — | No | Webhook for ingestion failure alerts |

### Feature flags

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ENABLE_CALENDAR_SCORER` | bool | `true` | No | Enable calendar-based risk adjustments |
| `ENABLE_LLM_FEATURES` | bool | `true` | No | Enable LLM-powered endpoints |
| `ENABLE_STUDENT_DEACTIVATION` | bool | `true` | No | Enable auto-deactivation |

### Testing

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `TESTING` | bool | `false` | No | Test mode (disables certain checks) |
| `SMOKE_TEST_USER` | string | `dev_admin` | No | Smoke test credentials |
| `SMOKE_TEST_PASS` | string | `changeme_local_only` | No | Smoke test credentials |

---

## Uploading weekly data (ops procedure)

### Step 1 — Export from Brightspace

1. Navigate to **Course Admin → Reports → Learner Usage**
2. Select date range: previous 7 days
3. Include columns: Username, Org Defined ID, First Name, Last Name, Last Login, Content Visits, Quiz Attempts, Assignment Submissions, Discussion Posts, Time in Content
4. Export as **Excel (.xlsx)**

### Step 2 — Upload via API

```bash
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

### Step 3 — Check task status

```bash
curl http://localhost:8000/api/v1/admin/ingest/status/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <admin_token>"
```

Status values:
- `pending` — Task queued, waiting for lock
- `running` — Ingestion in progress
- `success` — All records processed successfully
- `partial` — Some records failed (see `errors` array)
- `failed` — Critical error, no records processed

### Step 4 — Verify in audit log

```bash
curl http://localhost:8000/api/v1/admin/ingestion-runs \
  -H "Authorization: Bearer <admin_token>"
```

Check:
- `status` = `completed`
- `records_processed` matches expected count
- `errors` array is empty or acceptable
- `deactivated_count` reflects expected removals

### Step 5 — Troubleshooting failed/partial status

1. Check logs: `tail -f logs/meridian.log`
2. Review error details in ingestion-runs response
3. Common issues:
   - Corrupted Excel: Re-export from Brightspace
   - Missing columns: Verify export settings
   - Timeout: Split large files (>10k students)
4. Re-run ingestion (idempotent — safe to retry)

---

## API overview

**Note:** Full OpenAPI schema at `/openapi.json`. Committed snapshot at `docs/openapi.json`.

### Auth endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/api/v1/auth/login` | No | — | Username/password login |
| POST | `/api/v1/auth/refresh` | No | — | Refresh access token |
| GET | `/api/v1/auth/me` | Yes | — | Current user profile |

### Student endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/api/v1/students` | Yes | staff | List students with pagination |
| GET | `/api/v1/students/{id}` | Yes | staff | Student detail |
| GET | `/api/v1/students/{id}/weekly-summary` | Yes | staff | Weekly engagement summary |
| GET | `/api/v1/students/{id}/risk-trend` | Yes | staff | Risk score history |
| GET | `/api/v1/students/{id}/interventions` | Yes | staff | Intervention history |

### Intervention endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/api/v1/interventions` | Yes | staff | List interventions |
| POST | `/api/v1/interventions` | Yes | staff | Create intervention |
| PUT | `/api/v1/interventions/{id}` | Yes | staff | Update intervention |
| DELETE | `/api/v1/interventions/{id}` | Yes | admin | Delete intervention |
| POST | `/api/v1/interventions/{id}/act` | Yes | advisor | Mark acted upon |
| POST | `/api/v1/interventions/{id}/dismiss` | Yes | advisor | Dismiss recommendation |
| GET | `/api/v1/interventions/pending` | Yes | advisor | Pending queue |

### Admin — ingestion

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/api/v1/admin/ingest` | Yes | admin | Upload Excel file |
| GET | `/api/v1/admin/ingest/status/{task_id}` | Yes | admin | Check task status |
| GET | `/api/v1/admin/ingestion-runs` | Yes | admin | List ingestion history |

### Admin — data management

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/api/v1/admin/students` | Yes | admin | All students (including inactive) |
| POST | `/api/v1/admin/students/{id}/reactivate` | Yes | admin | Reactivate student |
| DELETE | `/api/v1/admin/students/{org_id}/erase` | Yes | admin | GDPR erasure |
| GET | `/api/v1/admin/students/{org_id}/data-export` | Yes | admin | GDPR export |

### Admin — monitoring

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/api/v1/admin/audit-log` | Yes | admin | FERPA audit trail |
| GET | `/api/v1/admin/system-metrics` | Yes | admin | Performance metrics |

### Admin — course registry

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/api/v1/admin/course-registry` | Yes | admin | List registered courses |
| POST | `/api/v1/admin/course-registry` | Yes | admin | Register course |
| PUT | `/api/v1/admin/course-registry/{id}` | Yes | admin | Update course |

### Admin — evaluation

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/api/v1/admin/evaluate-scorer` | Yes | admin | Trigger scorer evaluation |

### LLM / AI endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | `/api/v1/llm/risk-explanation` | Yes | staff | LLM risk summary |
| POST | `/api/v1/llm/intervention-suggestions` | Yes | staff | LLM intervention ideas |
| POST | `/api/v1/llm/report-narrative` | Yes | staff | LLM report generation |
| POST | `/api/v1/llm/what-if` | Yes | staff | LLM scenario simulation |
| GET | `/api/v1/llm/status` | Yes | — | LLM service health |

### Config endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/api/v1/config/thresholds` | Yes | admin | Get current thresholds |
| PUT | `/api/v1/config/thresholds` | Yes | admin | Update thresholds |
| GET | `/api/v1/config/feature-weights` | Yes | admin | Get feature weights |
| PUT | `/api/v1/config/feature-weights` | Yes | admin | Update weights |

### Health

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | `/health` | No | — | Service health check |
| GET | `/api/v1/health/detailed` | Yes | admin | Detailed health with ingestion staleness |

---

## Running tests

```bash
# Full test suite
pytest backend/tests/ -v

# Specific test files
pytest backend/tests/test_intervention_chain.py -v
pytest backend/tests/test_critical_paths.py -v
pytest backend/tests/test_department_assignment.py -v

# With coverage
pytest backend/tests/ --cov=backend --cov-report=html

# Type checking
mypy backend/

# Smoke test (requires running server)
bash scripts/smoke_test.sh
```

---

## Running the threshold calibration

Run after each trimester to calibrate risk thresholds against actual exam outcomes:

```bash
python -m backend.ml.training.calibrate
```

**When to run:**
- After T1/T2/T3 exam results are ingested
- Before configuring thresholds for next trimester
- When risk score distribution seems misaligned with actual outcomes

**What it does:**
1. Loads T1 students with known exam outcomes (completed/dropped/deferred)
2. Computes risk scores using current weights
3. Analyzes score distributions by outcome category
4. Suggests threshold values that maximise separation

**Output:**
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

Copy suggested values to `.env` and restart server.

---

## Deployment

### Docker deployment

```bash
# Build
docker build -f docker/Dockerfile -t meridian-ews .

# Run (single worker — REQUIRED)
docker run -p 8000:8000 --env-file .env meridian-ews
```

**Important constraint:** The application must run as a single uvicorn worker. The ingestion lock is an in-process Redis distributed lock that serialises concurrent ingestion runs. Running multiple workers without a coordinated lock strategy will cause race conditions. See `docs/architecture.md` for the multi-worker upgrade path.

### Production checklist

- [ ] `SECRET_KEY` set to random 32+ character value
- [ ] `ENVIRONMENT=production`
- [ ] `CORS_ORIGINS` set to exact production frontend URL (no localhost)
- [ ] `DATABASE_URL` set to PostgreSQL (SQLite not recommended)
- [ ] `REDIS_URL` set to production Redis instance
- [ ] `ALERT_WEBHOOK_URL` set for ingestion failure notifications
- [ ] `LOG_FILE` path writable with log rotation configured
- [ ] `alembic upgrade head` run before first start
- [ ] `python -m backend.scripts.seed_dev_data` NOT run in production
- [ ] `GEMINI_MODEL` pinned to specific version (not `latest`)
- [ ] Data Processing Agreement signed with LLM provider (if `ENABLE_LLM_FEATURES=true`)

---

## Data privacy and GDPR

### Data collected

- Student names, email addresses, BITS IDs (org_defined_id)
- LMS engagement metrics (logins, content views, quiz attempts, scores)
- Exam marks and attendance records
- Risk scores and intervention recommendations
- Advisor actions and notes

### Data retention

| Data type | Retention | Automated purge |
|-----------|-----------|-----------------|
| RiskSnapshot | 12 months | Scheduler job monthly |
| InterventionLog | 24 months | Scheduler job monthly |
| RawEvent | 6 months | Scheduler job monthly |
| AuditLog | 36 months | Manual review |

### Right to erasure

```bash
# Delete student and all related data
curl -X DELETE http://localhost:8000/api/v1/admin/students/2025EB1100001/erase \
  -H "Authorization: Bearer <admin_token>"
```

This permanently deletes:
- Student record
- All enrollments, exam records, graded components
- All risk snapshots, intervention logs, predictions
- All raw events, engineered features, responses

### Subject access requests

```bash
# Export all data for a student
curl http://localhost:8000/api/v1/admin/students/2025EB1100001/data-export \
  -H "Authorization: Bearer <admin_token>" \
  --output student_export.json
```

Returns JSON with all student data in machine-readable format.

### LLM data protection

Student identifiers are pseudonymised before any LLM API call:
- `student_id` → SHA-256 hash prefix
- `org_defined_id` → First 4 characters + "…"
- Names replaced with "Student A", "Student B" etc.

**Requirement:** A Data Processing Agreement must be executed with the LLM provider (Google for Gemini, Anthropic for Claude) before enabling LLM features in production (`ENABLE_LLM_FEATURES=true`).

### Legal basis

**To be confirmed with legal counsel.** Document the specific legal basis for processing (likely legitimate interest or contractual necessity) before production deployment.

---

## Known limitations

1. **Rule-based scoring only:** The risk formula has not been validated against historical dropout outcomes. Run `backend/ml/training/calibrate.py` after each trimester to calibrate thresholds against actual exam results.

2. **Course calendar coverage:** The CalendarAwareScorer only covers 10 specifically configured courses (see `calendar_scorer.py` `COURSE_CALENDAR` dict). All other courses receive no calendar-based risk adjustment. Pre-start weeks return `None` (no adjustment) rather than 0 (low risk).

3. **SQLite in development:** The default `DATABASE_URL` uses SQLite. For production with >500 concurrent users, migrate to PostgreSQL.

4. **Single-worker constraint:** The asyncio/Redis ingestion lock requires single-process deployment. Multi-worker scaling requires the Redis distributed lock architecture documented in `docs/adr/ADR-002.md`.

5. **LLM features require DPA:** LLM features must not be enabled in production without a signed Data Processing Agreement with the LLM provider.

6. **No trained ML model:** XGBoost and scikit-learn are listed in requirements as optional dependencies for future use. No trained model file exists in the repository. The "ML" label in legacy code is a misnomer — the system uses a rule engine.

7. **Frontend authentication:** The React frontend uses hardcoded demo credentials. Production requires JWT integration with the backend auth system.

---

## Troubleshooting

### SYMPTOM: All students show 0% content completion

**Root cause:** Ingestion failed to process content visit data from Excel.

**Fix:**
1. Check ingestion status: `GET /api/v1/admin/ingestion-runs`
2. Verify Excel has "Content Visits" column
3. Re-export from Brightspace with correct columns
4. Re-run ingestion

### SYMPTOM: Student list returns empty when filtering by risk range

**Root cause:** No risk snapshots exist for the current week.

**Fix:**
1. Trigger prediction run: `POST /api/v1/admin/run-predictions`
2. Or wait for scheduled 03:00 UTC job
3. Check `risk_snapshots` table has records with current week

### SYMPTOM: Ingestion returns 202 but task never reaches "success"

**Root cause:** Redis lock contention or worker crash.

**Fix:**
1. Check logs: `tail -f logs/meridian.log | grep ingestion`
2. Verify Redis connection: `redis-cli ping`
3. Check for zombie locks: `redis-cli KEYS "*ingestion*"`
4. Clear lock if stuck: `redis-cli DEL "ews_ingestion_lock"`

### SYMPTOM: All students showing "urgent intervention"

**Root cause:** Thresholds misconfigured (likely all at 0 or 100).

**Fix:**
1. Check current thresholds: `GET /api/v1/config/thresholds`
2. Verify `FEATURE_WEIGHTS` sum to 1.0 in logs at startup
3. Run calibration: `python -m backend.ml.training.calibrate`
4. Update `.env` with sensible defaults

### SYMPTOM: LLM features return 500 errors

**Root cause:** API key missing or invalid model version.

**Fix:**
1. Verify `GEMINI_API_KEY` or `CLAUDE_API_KEY` set
2. Check `GEMINI_MODEL` is pinned version (not `latest`)
3. Test provider status: `GET /api/v1/llm/status`
4. Check logs for rate limit or quota errors

### SYMPTOM: Ghost student alerts remain after student activates

**Root cause:** `_rescind_stale_ghost_alerts()` not triggered or failed.

**Fix:**
1. Verify student has `last_login` timestamp in recent ingestion
2. Check logs for "rescind" operations
3. Manually dismiss via UI or `POST /api/v1/interventions/{id}/dismiss`
4. Verify `activation_outreach` intervention type is configured

### SYMPTOM: Dashboard shows >100% completion for some courses

**Root cause:** Content item count mismatch between course registry and actual data.

**Fix:**
1. Update course registry: `PUT /api/v1/admin/course-registry/{id}`
2. Set correct `total_content_items` count
3. Re-ingest data for affected semester

---

## Contributing

### Branch naming

- `feature/description` — New features
- `fix/description` — Bug fixes
- `chore/description` — Maintenance tasks

### Before submitting a PR

```bash
# Run all checks
pytest backend/tests/ -v
mypy backend/
bash scripts/smoke_test.sh

# Verify no secrets leaked
git-secrets --scan
```

### Alembic migrations

Any model change must include a migration:

```bash
alembic revision --autogenerate -m "Add X to Y"
# Edit generated file to ensure downgrade() is implemented
alembic upgrade head
alembic downgrade -1  # Test reversibility
alembic upgrade head
pip install -r requirements.txt -r requirements-dev.txt
pytest backend/tests -v --tb=short
flake8 backend/ --count --statistics
bandit -r backend/
```

---

## Support

For questions or issues:
- Open a [GitHub Issue](../../issues)
- Review documentation in [`docs/`](./docs/):
  - [`API_REFERENCE.md`](./docs/API_REFERENCE.md) - API documentation
  - [`ARCHITECTURE.md`](./docs/ARCHITECTURE.md) - Design decisions
  - [`DEPLOYMENT.md`](./docs/DEPLOYMENT.md) - Deployment guide
- See [`SECURITY.md`](./SECURITY.md) for vulnerability reporting
- Check [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) for community guidelines

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full history.

### [1.1.0] — 2026-04-10

- **Three audit cycles completed:** 115 data integrity, security, and operational issues identified and fixed
- **D1-D12 fixes:** Excel error handling, pseudonymised logging, timezone-aware timestamps, threshold calibration
- **E1-E9 enhancements:** Calendar-aware scoring, LLM guardrails, feature store pre-computation, GDPR erasure/export

---

## Gaps found

The following gaps were identified while reading the codebase. These should be addressed before the README can be considered fully accurate:

1. **Missing `backend/routes/students.py` implementation:** File exists but appears to delegate to controllers. Need to verify actual endpoint implementations match the API table.

2. **Inconsistent user model:** `backend/database/models/user.py` shows minimal fields but auth endpoints reference `role` and `department` — verify full schema.

3. **Frontend package.json not read:** Could not locate frontend dependencies to confirm Node.js version requirements.

4. **Dockerfile CMD comment:** Need to verify the exact comment about single-worker constraint exists in the Dockerfile.

5. **Scripts directory:** Listed `smoke_test.sh` in root `scripts/` but need to verify contents and usage instructions.

6. **Decision engine threshold values:** Config shows threshold variables but actual default values need verification from running config.

7. **Calendar scorer course list:** Need to extract exact 10 courses from `COURSE_CALENDAR` dict.

8. **Alembic migration history:** Need to read migration files to confirm schema evolution.

9. **Test file locations:** Referenced `backend/tests/` but did not verify directory structure exists.

10. **CHANGELOG.md existence:** Referenced file but did not verify it exists or has content.

---

**Version:** 2.1.0  
**Last Updated:** April 2026
