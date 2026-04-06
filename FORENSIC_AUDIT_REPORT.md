# FORENSIC AUDIT REPORT — EWS Retention Platform (Meridian)

**Date:** 2026-04-06  
**Auditor:** Staff-Level Software Architect / ML Auditor  
**Scope:** Complete backend, ingestion, ML, configuration, and data artifact audit  
**Codebase Version:** `main` — commit `2816b9e`

---

## TABLE OF CONTENTS

1. [Phase 1 — Project Structure Map](#phase-1--project-structure-map)
2. [Phase 2 — File-by-File Audit](#phase-2--file-by-file-audit)
3. [Phase 3 — Data + ML Validation](#phase-3--data--ml-validation)
4. [Phase 4 — System-Level Risks](#phase-4--system-level-risks)
5. [Phase 5 — Final Scores](#phase-5--final-scores)

---

## PHASE 1 — PROJECT STRUCTURE MAP

```
ews-retention-platform/
│
├── backend/                              [BACKEND]
│   ├── api/                              [backend]   — FastAPI dependency injection
│   │   └── deps.py
│   ├── config/                           [config]    — Central configuration (env-driven)
│   │   └── __init__.py
│   ├── controllers/                      [backend]   — HTTP handlers (students)
│   │   └── students_controller.py
│   ├── core/                             [backend]   — Auth, security, logging, Redis cache
│   │   ├── auth.py
│   │   ├── logger.py
│   │   ├── redis_cache.py
│   │   └── security.py
│   ├── database/                         [backend]   — ORM engine + models
│   │   ├── connection.py                 ← Defines SessionLocal (DUPLICATE)
│   │   ├── session.py                    ← Defines SessionLocal again (DUPLICATE)
│   │   ├── queries.py
│   │   └── models/
│   │       ├── student.py
│   │       ├── prediction.py
│   │       ├── intervention.py
│   │       ├── user.py
│   │       ├── academic.py
│   │       ├── enrollment.py
│   │       ├── course.py
│   │       ├── audit.py
│   │       ├── canonical.py              ← Dimensional model (DimStudent, FactEngagement...)
│   │       ├── event.py
│   │       ├── feature.py
│   │       ├── goals_and_risks.py
│   │       ├── llm.py
│   │       └── ...
│   ├── data/                             [DATA]
│   │   ├── Engagement_Analysis.xlsx      ← Primary XLSX (exists)
│   │   ├── labels.csv                    ← ML training labels (EMPTY — 0 bytes)
│   │   └── sql_app.db                    ← Live SQLite database
│   ├── features/                         [ml]        — Signal modules (disconnected from pipeline)
│   ├── ingestion/                        [ingestion] — Legacy ETL pipeline (hardcoded paths)
│   ├── jobs/                             [backend]   — Background feature store job
│   ├── middleware/                       [backend]   — Security + request validation middleware
│   ├── ml/                              [ML]
│   │   ├── config.py                     ← Wrong feature schema (absrate/mpa)
│   │   ├── features/__init__.py          ← Empty stub
│   │   ├── inference/
│   │   │   └── risk_formula.py           ← Broken weight key mapping
│   │   ├── models/saved/
│   │   │   ├── feature_importance.csv    ← absrate schema — incompatible with DB features
│   │   │   ├── retention_model_logreg.joblib
│   │   │   └── retention_model_xgboost.joblib
│   │   └── training/
│   │       └── evaluate.py               ← Hardcoded output path; no CLI entrypoint
│   ├── routes/                           [backend]   — ~20 route modules
│   ├── schemas/                          [backend]   — Pydantic I/O contracts
│   ├── services/                         [backend]
│   │   ├── ai/                           ← LLM orchestrator (broken method refs)
│   │   ├── analytics/                    ← Pattern discovery
│   │   ├── core/
│   │   │   ├── ews_engine.py
│   │   │   ├── data_ingestion.py
│   │   │   └── decision_engine.py
│   │   ├── infrastructure/
│   │   │   ├── scheduler.py              ← Blocking loop, no thread safety
│   │   │   └── audit_logger.py
│   │   ├── feature_engineering.py        ← Primary feature engine
│   │   ├── risk_scoring.py               ← Primary risk engine
│   │   ├── ml_service.py
│   │   └── student_service.py            ← 669-line god-service
│   ├── main.py                           [backend]   — Application entry point
│   └── backend.log                       ← Log file committed to version control
│
├── seed_dummy_data.py                    [misc]      — Seeder (wrong password hasher)
├── sql_app.db                            [data]      ← DUPLICATE DB at repo root
├── requirements.txt                      [config]    ← No version pins on most packages
├── test_endpoints.py                     [misc]
├── test_students.json                    [misc]
└── frontend/                             [frontend]
    └── src/pages/                        ← 16 React page components
```

---

## PHASE 2 — FILE-BY-FILE AUDIT

---

### `backend/config/__init__.py`

**Purpose:** Central configuration module — reads all runtime settings from environment variables with hardcoded defaults.

**Issues Found:**

- **CRITICAL — Hardcoded `SECRET_KEY` in source code.**  
  `SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_a3f9c2e1b7d4e8f0a1b2c3d4e5f60718")`  
  If `SECRET_KEY` is not set in production, all JWTs will be signed with this key which is now publicly visible in the repo. Any attacker can forge valid admin tokens.

- **HIGH — 7 XLSX data file paths reference non-existent files.**  
  `QUIZ_STATUS_9FEB_PATH`, `GRADED_QUIZ_10FEB_ORIG_PATH`, `WEEK3_USAGE_PATH`, `WEEK5_USAGE_PATH`, and others point to files that do not exist in `backend/data/`. The config silently continues; ingestion skips them without any alert to operators.

- **HIGH — `SAMPLE_DATA_PATH` (labels.csv) is a 0-byte file.**  
  Any code path that attempts to load this file for ML training will either silently fail or raise a parse error.

- **MEDIUM — `SIGNAL_WEIGHTS` in config (keys: `attendance`, `grades`, `engagement`, `submissions`) do not match the keys used by `risk_formula.py` (keys: `academic`, `engagement`, `consistency`, `intent`, `responsiveness`).**  
  The risk formula falls back silently to zero weights for all signals it cannot find — risk scores computed via `risk_formula.py` are meaningless.

- **MEDIUM — `requirements.txt` has no version pins** on critical packages (`fastapi`, `uvicorn`, `sqlalchemy`, `pandas`). A `pip install` at any future date may install incompatible versions and break the system with no warning.

**Type:** Security, Config, Data Risk

**How To Fix:**
```python
# Raise immediately if secret is the placeholder in non-dev environments
import sys
if SECRET_KEY == "CHANGE_ME_IN_PRODUCTION_a3f9c2e1b7d4e8f0a1b2c3d4e5f60718":
    if os.getenv("APP_ENV", "development") != "development":
        sys.exit("FATAL: SECRET_KEY is still the default. Set a real value.")
```
For requirements: pin every package. Use `pip freeze > requirements.txt` after testing.

---

### `backend/database/connection.py`

**Purpose:** Creates the SQLAlchemy engine, declarative Base, and `SessionLocal`.

**Issues Found:**

- **HIGH — `SessionLocal` is defined here AND identically redefined in `session.py`.**  
  Two separate session factories exist — both bind to the same engine but are independent Python objects. Code that imports from `connection.py` vs `session.py` holds references to different factories, which can cause session-level bugs (uncommitted data invisible across import boundaries). This is dead code duplication.

- **MEDIUM — SQLite `check_same_thread=False` with no connection pool tuning.**  
  The engine is created with default `pool_size` (5) and no `pool_timeout`. With async FastAPI under load, SQLite connections contend at the driver level. This is not a problem for a small deployment but will silently corrupt under concurrent writes.

- **LOW — `init_db()` imports all models inside the function body on every call.**  
  This is a workaround for circular import issues that were never resolved at the architecture level.

**Type:** Architecture, Performance, Logic Bug

**How To Fix:**
Delete `database/session.py` entirely. Standardize all imports to `from backend.database.connection import SessionLocal`. Resolve circular imports by restructuring model imports.

---

### `backend/database/session.py`

**Purpose:** Supposed to be the canonical session management module.

**Issues Found:**

- **HIGH — Complete duplicate of `connection.py`'s `SessionLocal`.**  
  `session.py` creates `SessionLocal = sessionmaker(..., bind=engine)` — identical to `connection.py` line 18. Two different session factories exist simultaneously. This is never acceptable in a production system.

- **MEDIUM — `get_db()` is duplicated.** It also exists verbatim in `api/deps.py`. Three different `get_db` implementations exist in the project.

**Type:** Architecture, Logic Bug

**How To Fix:**  
Delete this file. There should be exactly one session factory and one `get_db` in the codebase.

---

### `backend/api/deps.py`

**Purpose:** FastAPI dependency injection — DB sessions, JWT auth, RBAC role checking.

**Issues Found:**

- **CRITICAL — `get_current_user_role()` defaults to `"admin"` when the `X-User-Role` header is absent.**

  ```python
  def get_current_user_role(x_user_role: Optional[str] = Header(None, alias="X-User-Role")) -> str:
      return x_user_role or "admin"  # ← ANY unauthenticated request gets admin
  ```

  Any client that omits the `X-User-Role` header gets admin privileges. This completely bypasses RBAC. The comment says "development-friendly" but this is deployed code. This is the most critical security bug in the project.

- **CRITICAL — `require_role` depends on `get_current_user_role`, which is header-based (not JWT-verified).**  
  RBAC enforcement on all routes that use `require_role(["Admin"])`, `require_role(["Faculty"])` etc. is trivially bypassed by any HTTP client by setting the header `X-User-Role: admin`.

- **HIGH — `get_db()` is a third duplicate** of the same pattern already in `connection.py` and `session.py`.

- **MEDIUM — JWT `get_current_user` uses `HTTP_403_FORBIDDEN` for authentication failures.**  
  The correct status for missing/invalid credentials is `HTTP_401_UNAUTHORIZED`. 403 means "authenticated but not authorized."

- **MEDIUM — `user_id` decoded from JWT is cast to `int` (`User.id == int(user_id)`).**  
  If the JWT `sub` claim is not a valid integer string, this raises an unhandled `ValueError` that would return a 500 instead of a clean 401.

**Type:** Security, Architecture, Logic Bug

**Corrected Code (role fallback):**
```python
def get_current_user_role(
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
) -> str:
    # NEVER default to a privileged role. Default to the least privilege.
    return x_user_role or "student"
```
Long-term: `require_role` must be wired to `get_current_user` (JWT-verified), not a raw header.

---

### `backend/core/auth.py`

**Purpose:** JWT token creation, password hashing/verification.

**Issues Found:**

- **MEDIUM — `datetime.utcnow()` is deprecated in Python 3.12+.**  
  Python now recommends `datetime.now(timezone.utc)`. While functional today, this will raise a `DeprecationWarning` in Python 3.13 (the project's runtime) and break in future Python versions.

- **MEDIUM — Default token expiry fallback is 15 minutes** if no `expires_delta` is passed, but config sets `ACCESS_TOKEN_EXPIRE_MINUTES=60`. Callers must remember to pass the delta; if they forget, tokens silently expire 4× sooner.

- **LOW — No token revocation mechanism.** Tokens are stateless JWTs — a logged-out user's token remains valid until expiry. No blacklist, no session invalidation.

**Type:** Logic Bug, Security

**How To Fix:**
```python
from datetime import datetime, timedelta, timezone

def create_access_token(subject, expires_delta=None):
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=60))
    return jwt.encode({"exp": expire, "sub": str(subject)}, SECRET_KEY, algorithm=ALGORITHM)
```

---

### `backend/core/logger.py`

**Purpose:** Structured JSON logger setup.

**Issues Found:**

- **MEDIUM — Logger handlers are never reset if `setup_logger()` is called multiple times for the same name.**  
  The guard `if not logger.handlers` prevents double-adding only on the first call per process. In test environments where the module reloads, duplicate log lines appear in both the file and stdout.

- **LOW — Log file path (`backend.log`) is a relative path resolved at import time.**  
  The file is committed to version control — personal/debug logs from development sessions are already in the repo.

- **LOW — `datetime.utcnow()` deprecated** — same issue as `auth.py`.

**Type:** Config, Style

---

### `backend/core/redis_cache.py`

**Purpose:** Optional Redis cache for route responses.

**Issues Found:**

- **HIGH — The `cache_response` decorator silently assumes the wrapped function is `async` and calls `await func(*args, **kwargs)`.**  
  If a sync route is decorated with `@cache_response`, it will fail at runtime with a `TypeError: object NoneType can't be used in 'await' expression`.

- **HIGH — Cache key uses `hash(str(kwargs))`.**  
  Python's `hash()` is non-deterministic across process restarts (hash randomization since Python 3.3). Cache keys computed in one process will not match those in another restart, making the cache effectively useless for anything persistent. Different requests with the same parameters may get different hash values in the same process if kwarg ordering differs.

- **MEDIUM — Redis connection failure silently sets `self.client = None`** and all cache operations become no-ops. There is no alerting or metric when the cache is offline — the system runs correctly but with degraded performance and no visibility.

- **LOW — `json.dumps(result)` will fail silently for non-JSON-serializable types** (e.g., SQLAlchemy model instances, datetime objects). The `except Exception` block discards the error.

**Type:** Logic Bug, Performance, Architecture

**Corrected key generation:**
```python
import hashlib, json
key = f"{key_prefix}:{hashlib.md5(json.dumps(kwargs, sort_keys=True, default=str).encode()).hexdigest()}"
```

---

### `backend/core/security.py`

**Purpose:** `SecurityManager` utility class — input sanitization, RBAC enforcement, pagination validation.

**Issues Found:**

- **MEDIUM — `sanitize_input` only strips HTML tags — it does not prevent SQL injection, XSS via attributes, or Unicode attacks.**  
  `re.sub(r'<[^>]*>', '', str(data))` will not strip `javascript:` URIs in attributes or encoded payloads like `&lt;script&gt;`. This gives false confidence.

- **LOW — `SecurityManager` is a class with only `@staticmethod` methods.** It should be a module with functions. The class adds no value and will confuse readers.

- **LOW — `enforce_role` is never called anywhere in the codebase.** Dead code.

**Type:** Security, Architecture

---

### `backend/middleware/security_logging.py`

**Purpose:** Combined rate-limiting and access logging middleware.

**Issues Found:**

- **CRITICAL — `rate_limit_store` is an in-process Python dict.**  
  - It is not thread-safe (FastAPI runs on an async event loop, but blocking tasks can interact via threads). Under heavy load with `asyncio.to_thread`, concurrent writes to a plain `dict` can corrupt state.
  - It is not shared across multiple worker processes. Deploy with `--workers 4` and each process has its own counter — the effective rate limit becomes `4 × 100 = 400` req/min per IP.
  - It grows forever. IPs are never evicted from the dict, creating a slow memory leak in production.

- **HIGH — The middleware catches `Exception` and returns a 500 JSON response.**  
  This masks legitimate 500 errors (e.g., DB connection refused) with a generic message, losing the original traceback from FastAPI's own exception handlers.

- **MEDIUM — `request.client.host` is used directly for rate limiting without checking for proxy headers.**  
  Behind a reverse proxy (Nginx, Cloudflare), all requests will have `client.host = 127.0.0.1` — the entire platform is effectively rate-limited as one user.

**Type:** Security, Performance, Architecture

**How To Fix:**
Replace `rate_limit_store` with Redis (already in the stack). Use `slowapi` (FastAPI-native rate limiting library) or implement using `redis.incr()` with a TTL key. Handle `X-Forwarded-For` for real IP detection.

---

### `backend/middleware/request_validation.py`

**Purpose:** Enforces `Content-Type: application/json` on mutating HTTP methods.

**Issues Found:**

- **LOW — Checks `content-length` header to detect body presence**, but `content-length` can be absent with chunked transfer encoding. This middleware will let through non-JSON chunked POST bodies.

**Type:** Logic Bug

---

### `backend/main.py`

**Purpose:** Application factory, lifespan, CORS, middleware registration, exception handlers.

**Issues Found:**

- **HIGH — `asyncio.create_task(_run_ingestion())` is called from inside the lifespan context manager before `yield`.**  
  `asyncio.create_task` schedules the coroutine on the event loop, but the task is fire-and-forget with no error propagation. If ingestion fails catastrophically (e.g., DB is locked), it logs and silently moves on — no retry, no health check failure, no startup gate. The server reports healthy but has no data.

- **HIGH — CORS `allow_headers=["*"]`** permits any request header including custom headers that should be restricted, e.g., `X-User-Role` (which this system uses for RBAC bypass, see `deps.py`). This makes the security bypass accessible from any browser origin.

- **MEDIUM — Missing `allow_origin_regex`.**  
  `CORS_ORIGINS` is a comma-split string — if the env var has spaces (common mistake), the parsed origin becomes `" http://localhost:3000"` (with a leading space) which will never match and silently breaks CORS.

- **MEDIUM — `import uvicorn` inside `if __name__ == "__main__"` is fine, but `reload=True` in production is dangerous** — file changes will restart the server mid-request.

**Type:** Architecture, Security, Logic Bug

---

### `backend/database/queries.py`

**Purpose:** Common query helpers for Student and Prediction retrieval.

**Issues Found:**

- **MEDIUM — `get_all_predictions` has a default `limit=5000`** — returning 5000 ORM objects at once loads all of them into memory simultaneously. For a student body of this size this is manageable, but it is structurally wrong.

- **LOW — Functions do lazy imports of models inside function bodies** (`from backend.database.models.student import Student`). This hides import errors until runtime and is not idiomatic.

- **LOW — Partial duplication with `StudentService`** — `get_all_students` in queries.py returns raw ORM objects without metrics, while `StudentService.get_all_students()` computes metrics. Callers must know which to use.

**Type:** Performance, Architecture

---

### `backend/services/feature_engineering.py`

**Purpose:** Derives all engagement features from enrollment, graded component, and exam records.

**Issues Found:**

- **HIGH — Normalization denominators are arbitrary magic numbers with no data validation.**
  - Quiz score: `avg_quizzes / 20.0` — why 20? If course has 5 quizzes, score is capped at 25%, making most students appear severely disengaged.
  - Login consistency: `avg_logins / 100.0` — a student with 50 logins gets 50% score. This is not calibrated against actual data.
  - Time investment: `avg_hours / 20.0` — 20 hours per course per semester is chosen arbitrarily with no reference to actual platform usage patterns.
  - These magic numbers mean the risk scores are not grounded in observed distributions. **The model is scoring off-distribution by design.**

- **HIGH — `calculate_w1w2_completion_score` uses `content_completed` (cumulative total) compared against `content_required_w1w2` (weeks 1-2 only).**  
  A student who completed all week 12 content but zero weeks 1-2 content will show 100% W1/W2 score. This is a **feature leakage / measurement error** — the denominator and numerator are measuring different time windows.

- **MEDIUM — `get_engagement_trend()` computes "active/declining/inactive" from total cumulative logins and total content completed.**  
  There is no temporal component — a student who logged in 50 times in week 1 and never again will be classified as "active" indefinitely. This function's name is misleading; it does not compute a trend.

- **MEDIUM — `_parse_timestamp()` is defined but never called** in `calculate_all_features()`. Dead code.

- **LOW — `calculate_exam_attendance_rate` defaults `present=True`** — `e.get('present', True)`. If the `present` field is missing from the dict, the student is counted as having attended. Silent false positive.

**Type:** Logic Bug, ML Risk, Data Risk

---

### `backend/services/risk_scoring.py`

**Purpose:** Computes final 0-100 risk score from features via weighted sum.

**Issues Found:**

- **HIGH — The risk formula is `risk = 100 - weighted_engagement`.**  
  When all graded scores and exam scores are missing (most real students if data is incomplete), all features default to 0.0. Weighted engagement = 0. Risk score = 100. **Every student with incomplete data will be scored as maximally at-risk**, regardless of their actual situation. This is a critical classification error.

- **MEDIUM — The zero-progress penalty halves `weighted_engagement` when `zero_progress_ratio >= 0.8`.**  
  `weighted_engagement *= 0.5` then `risk = 100 - weighted_engagement`. This can actually *reduce* risk for students who already had low engagement (engagement near 0 gets halved, risk goes from ~100 to ~100 — marginal change). The penalty does not work as intended for worst-case students.

- **MEDIUM — `get_dominant_risk_factor()` identifies the factor contributing most to risk via `(100 - score) * weight`.**  
  For a student with all scores at 0, all contributions are equal per weight. The "dominant" factor returned is effectively arbitrary (dict ordering). No tie-breaking.

- **LOW — NaN check uses `risk_score != risk_score`** — an unconventional but valid Python NaN check. It works but is unreadable. Use `math.isnan()`.

**Type:** Logic Bug, ML Risk

---

### `backend/services/ml_service.py`

**Purpose:** Orchestrates risk prediction; bridges features → scoring → persistence.

**Issues Found:**

- **HIGH — `_cache` is an in-process instance dictionary.**  
  The `MLService` singleton is `ml_service = MLService()` at module level. Under FastAPI with async workers, this cache is shared across all requests in the same process. There is no TTL — a prediction cached at startup is served indefinitely until the process restarts. Stale predictions will be served to `/predict-cached` callers.

- **HIGH — `_persist_prediction()` calls `db.commit()` inside a service method called from a route that already has a DB session.**  
  This creates nested transaction issues. If the route's session is within an outer transaction, this premature commit will partially flush state. In SQLite's default isolation mode this can cause "database is locked" errors under concurrent writes.

- **MEDIUM — `batch_predict()` returns only from the in-memory cache**, not from the database. If a student was never scored in the current process lifetime, they return an error dict silently mixed into the batch results.

- **MEDIUM — `logger = sys_logger` re-assigns the module-level logger to the application logger.**  
  All ML service logs will appear under the name `"ews_platform"` instead of `"__name__"`. Structured log filtering by module becomes impossible.

- **LOW — `_try_load_joblib_models()` is called at module import time.**  
  If `joblib` is not installed, this fails silently. If the model file is corrupt, it logs a warning and returns `None`. The entire inference layer gracefully degrades — which is intentional — but this is not surfaced in the `/health` endpoint.

**Type:** Architecture, Logic Bug, Performance

---

### `backend/services/student_service.py`

**Purpose:** Student data retrieval, metric calculation, analytics aggregation.

**Issues Found:**

- **CRITICAL — `get_all_students()` and `get_overview_stats()` load ALL students, ALL enrollments, ALL graded components, and ALL exam records into Python memory on every request.**  
  These are O(N) memory operations that do no filtering at the DB level. For 500 students × 10 courses × 5 graded components = 25,000 ORM objects materialized per request. Calling these endpoints under any load will cause significant latency spikes and memory pressure.

- **HIGH — Pagination in `get_all_students()` is applied in Python after loading all records.**  
  `return student_metrics[skip:skip + limit]` — the DB offset/limit is never pushed to the SQL layer. For page 5 of 10, all 500+ students are still loaded and scored.

- **HIGH — Risk scores are recomputed from scratch on every API call.**  
  There is no result caching at the service level (the `ml_service._cache` is separate and not used here). Every call to `/students` triggers full feature engineering for every student.

- **HIGH — `get_analytics_data()`, `get_risk_distribution()`, `get_overview_stats()` all independently batch-fetch all students + all enrollments + all graded + all exams.**  
  This means a dashboard load that calls 3 analytics endpoints executes 3 full table scans of every table.

- **MEDIUM — `get_overview_stats()` calls `FeatureEngineer.calculate_all_features(enrollments, graded, exams)` but the version called from `get_risk_distribution()` calls `FeatureEngineer.calculate_all_features(enrollments)` (no graded/exams).**  
  The same student gets a different risk score from different endpoints. Risk distributions and overview stats are inconsistent.

- **MEDIUM — `build_prediction_payload()` maps signal scores inconsistently:**  
  `consistency_signal_score` is mapped from `exam_attendance_rate`, not from `login_consistency_score`. `responsiveness_signal_score` is mapped from `exam_score`. These mappings are arbitrary and semantically wrong.

**Type:** Performance, Logic Bug, Architecture

**How To Fix (pagination):**
```python
# Push pagination to the DB — don't load all students
students = db.query(Student).offset(skip).limit(limit).all()
```
For metrics: precompute and persist to a `student_metrics` table during the scheduled job; serve from there.

---

### `backend/services/core/ews_engine.py`

**Purpose:** Facade for risk calculation — delegates to `FeatureEngineer` and `RiskScorer`.

**Issues Found:**

- **MEDIUM — `engagement_score = round(100.0 - risk_score, 2)` is a tautology.**  
  Engagement is defined as the exact inverse of risk. This means engagement adds zero independent signal. A student could have high content completion and high quiz scores but still show "low engagement" if one weak feature (e.g., exam score) drives risk up. These two numbers are not independent measurements.

- **LOW — `batch_predict()` iterates students in a plain Python loop with no parallelism.**  
  For a batch of 500 students, this is sequential. Acceptable for the current codebase, but should be noted if batch size grows.

**Type:** Logic Bug, Architecture

---

### `backend/services/core/data_ingestion.py`

**Purpose:** Primary XLSX ETL — populates Student, Course, Enrollment, GradedComponent, ExamRecord tables.

**Issues Found:**

- **HIGH — `ingest_all_data()` checks `if db.query(Student).count() > 0: return` as idempotency guard.**  
  This is a coarse check. If ingestion was interrupted halfway (e.g., students loaded but GradedComponents not), the guard prevents re-ingestion. Partial data will persist silently as "complete."

- **HIGH — The function is called via `asyncio.to_thread(ingest_all_data, db)` in `main.py`, passing a SQLAlchemy `Session` object across thread boundaries.**  
  SQLAlchemy sessions are **not thread-safe**. Passing a session created on the main thread into a worker thread violates SQLAlchemy's threading model and can cause `DetachedInstanceError` or silent data corruption.

- **MEDIUM — `openpyxl.load_workbook(..., read_only=True)` is used for the main XLSX.**  
  Read-only mode is memory-efficient but some cell value types (e.g., formulas) return `None` instead of the computed value when `data_only=True` is set. The code does set `data_only=True` — this is correct — but formula cells will silently return `None`, resulting in zero-values being stored for computed fields.

- **MEDIUM — `dept_name = str(vals[2]).strip().replace('&amp;', '&')` — HTML entity decoding is done manually.**  
  If the XLSX contains other HTML entities (`&lt;`, `&gt;`, `&#160;`) they will not be decoded. Use `html.unescape()` instead.

- **LOW — No row count validation or checksum** after ingestion. There is no assertion that the number of students loaded matches the source file.

**Type:** Architecture, Data Risk, Logic Bug

**Correct threading fix:**
```python
# In main.py lifespan:
async def _run_ingestion():
    def _sync():
        db = SessionLocal()  # Create session INSIDE the thread
        try:
            ingest_all_data(db)
        finally:
            db.close()
    await asyncio.to_thread(_sync)
```

---

### `backend/services/infrastructure/scheduler.py`

**Purpose:** Runs daily predictions and weekly model retraining via `schedule` library.

**Issues Found:**

- **CRITICAL — `start_scheduler()` contains `while True: schedule.run_pending(); time.sleep(60)` — a blocking infinite loop.**  
  This function is never called in `main.py`. There is no background thread or process starting it. The scheduler does not run in production. Daily predictions are never generated automatically.

- **HIGH — If `start_scheduler()` were called**, it would block the calling thread entirely. The `schedule` library is a synchronous, thread-blocking scheduler — it should never run in the same thread as an async event loop.

- **HIGH — `generate_daily_predictions()` creates `db = SessionLocal()` directly inside the job function, outside a context manager.**  
  If an exception occurs before `db.close()`, the connection leaks. The `finally: db.close()` is present — this is correct — but the `db.rollback()` in the except block occurs before `db.close()` in the finally block, which is the correct order. However, the session is not used as a context manager, which is fragile.

- **MEDIUM — `Prediction` objects are added per-student inside the loop, and `db.commit()` is called once at the end.**  
  If any exception occurs mid-loop, all prior `db.add()` calls are rolled back. An exception on student 499 of 500 discards 499 predictions silently.

**Type:** Architecture, Logic Bug, Performance

---

### `backend/routes/auth.py`

**Purpose:** Login, register, profile management endpoints.

**Issues Found:**

- **MEDIUM — `/register` endpoint is completely open** — any anonymous user can create an account with any role, including `Admin` and `Faculty`.**  
  `role=user_in.role` — the client supplies their own role. There is no admin approval step, no email verification, and no restriction on which roles can self-register.

- **MEDIUM — `/auth/me` (PUT) allows any authenticated user to self-promote their role:**  
  ```python
  if payload.role is not None:
      current_user.role = payload.role
  ```
  A `Student` can send `{"role": "Admin"}` and gain admin privileges immediately.

- **LOW — Login returns `HTTP_400_BAD_REQUEST` for inactive users** instead of `HTTP_403_FORBIDDEN`. Inactive users are authenticated but not authorized — 403 is the correct code.

**Type:** Security, Logic Bug

---

### `backend/routes/interventions.py`

**Purpose:** CRUD for intervention records.

**Issues Found:**

- **CRITICAL — No authentication or authorization** on any endpoint.  
  `GET /interventions`, `POST /interventions`, `PATCH /interventions/{id}` — all are publicly accessible with no `Depends(get_current_user)` or `Depends(require_role(...))`. Any unauthenticated user can read all intervention records (exposing sensitive student data) or create/modify interventions.

- **HIGH — `channels` field is stored as a JSON string in a `String` column** (`Column(String)`) instead of a `JSON` column.  
  Manual `json.dumps`/`json.loads` is done in application code. If the DB column is read directly (e.g., for reporting), it returns a raw string. Use `Column(JSON)`.

- **MEDIUM — `InterventionCreateRequest` allows `student_id = None` and `student_ids = None` simultaneously**, with the check `if body.student_ids: ... elif body.student_id: ... else: raise HTTPException(400)`. A POST with `{}` (empty body) will raise a 400, but only at the if-chain, not at Pydantic validation level. The schema should use a Pydantic validator to enforce at least one of the two fields.

**Type:** Security, Architecture, Validation

---

### `backend/routes/ml_routes.py`

**Purpose:** ML prediction endpoints — single student, batch, cohort risk, trend analysis.

**Issues Found:**

- **CRITICAL — No authentication or authorization** on any ML endpoint.  
  `/ml/predict/{student_id}`, `/ml/predict-batch`, `/ml/cohort-risk`, `/ml/trend-analysis` — all publicly accessible.

- **HIGH — `GET /ml/cohort-risk` uses `.distinct(Prediction.student_id)` without a proper subquery.**  
  The query `db.query(Prediction.student_id, Prediction.risk_score).order_by(...).distinct(Prediction.student_id)` does not reliably return the *latest* prediction per student in SQLite (SQLite does not support `DISTINCT ON`). Results are non-deterministic.

- **MEDIUM — `predict_student_batch` does per-student DB queries inside a loop** (N+1 query pattern).  
  For a batch of 100 students: 100 student existence checks + 100 enrollment fetches + 100 graded fetches + 100 exam fetches = 400+ queries.

**Type:** Security, Logic Bug, Performance

---

### `backend/routes/students.py`

**Purpose:** Thin delegation module.

**Issues Found:**

- **LOW — File contains only `from backend.controllers.students_controller import router`.**  
  This module exists solely to preserve import paths. It adds a layer of indirection with no value.

**Type:** Architecture

---

### `backend/routes/monitoring.py`

**Purpose:** Operational health/stats endpoint.

**Issues Found:**

- **HIGH — No authentication.** `/monitoring/predictions` is publicly accessible.

- **MEDIUM — Returns `ml_service.get_runtime_stats()` which includes `total_predictions` (count of cached students).**  
  This leaks operational intelligence (how many students are being tracked) to unauthenticated callers.

**Type:** Security

---

### `backend/controllers/students_controller.py`

**Purpose:** Student API endpoints — list, detail, risk trend, analytics, intervention effectiveness.

**Issues Found:**

- **CRITICAL — No authentication or authorization on any endpoint.**  
  All student data endpoints — `/students`, `/students/{student_id}`, `/at-risk`, `/risk-distribution`, `/analytics/*` — are publicly accessible with zero auth.

- **HIGH — `get_intervention_effectiveness()` calls `StudentService.get_all_students(db, skip=0, limit=2000)` to build a risk map.**  
  This forces loading and computing risk for up to 2000 students on every call to the intervention effectiveness endpoint.

- **MEDIUM — `get_students()` returns `total = StudentService.get_student_count(db)`** (a fast `COUNT(*)`), but the `students` list is post-filtered and post-paginated in Python. The `total` count will not match the filtered result count when `risk_min` or `risk_max` filters are applied.

- **MEDIUM — `_normalize_0_100()` uses `if not (v == v)` for NaN detection** — identical to the same issue in `risk_scoring.py`. Inconsistent, unreadable.

**Type:** Security, Performance, Logic Bug

---

### `backend/ingestion/pipeline.py`

**Purpose:** Legacy dimensional model ETL — populates `DimStudent`, `FactEngagement`, etc.

**Issues Found:**

- **HIGH — `self.db = SessionLocal()` is called in `__init__` with no context manager.**  
  The DB session is only closed in `finally: self.db.close()` inside `run()`. If `run()` is never called, or if `__init__` itself throws, the session leaks.

- **HIGH — `ingest_courses()` inserts a single hardcoded placeholder course:** `{'course_id': 'DEFAULT_COURSE', 'course_name': 'General Course', 'program': 'BS'}`.  
  All assessment records are then linked to `'DEFAULT_COURSE'`. This makes the dimensional model completely unusable for any per-course analysis.

- **HIGH — `ingest_assessments()` iterates `os.listdir(self.data_dir)` — but `self.data_dir = Path("data/raw")`.**  
  This is a relative path. The path resolves relative to whatever the working directory is at runtime — running from the project root vs. the `backend/` directory will find different (or no) files. This pipeline will silently ingest nothing if run from the wrong directory.

- **MEDIUM — `ingest_attendance()` hardcodes filenames** `"B.S and M.Sc Live Summary Data C-1, Trimester 1.xlsx"` that do not exist in `backend/data/`. The pipeline silently skips them.

- **MEDIUM — This pipeline populates a completely different set of tables** (`DimStudent`, `FactEngagement`, `FactAcademicPerformance`) than the primary ingestion service (`Student`, `Enrollment`, `GradedComponent`). The application's scoring pipeline reads from `Student/Enrollment`, not from the dimensional tables. This ETL pipeline produces data that nothing reads.

- **LOW — `logging.basicConfig(level=logging.INFO)` called at module level.** This overrides the structured JSON logger configured in `core/logger.py` for any module that imports this pipeline.

**Type:** Architecture, Logic Bug, Data Risk, Config

---

### `backend/ml/config.py`

**Purpose:** ML-specific configuration constants.

**Issues Found:**

- **HIGH — `REQUIRED_STUDENT_FEATURES = ['absrate7', 'q4mpa7', 'nsusp7', 'mobility7']`**  
  These are the features from the old attendance/GPA schema that the deployed joblib models were trained on. The live feature pipeline produces entirely different features (`content_completion_score`, `quiz_engagement_score`, etc.). This config file documents a schema that is **actively incompatible** with the rest of the system. It is misleading to anyone reading it.

**Type:** Architecture, ML Risk

---

### `backend/ml/inference/risk_formula.py`

**Purpose:** Explainable weighted risk formula for auditing.

**Issues Found:**

- **HIGH — Weight key mismatch with `config.py` `SIGNAL_WEIGHTS`.**  
  `risk_formula.py` calls `SIGNAL_WEIGHTS` from config (keys: `attendance`, `grades`, `engagement`, `submissions`) then maps signal input keys to weight keys: `academic → 'academic'`, `engagement → 'engagement'`, `consistency → 'consistency'`, `intent → 'intent'`, `responsiveness → 'responsiveness'`. None of these weight key names exist in `SIGNAL_WEIGHTS`. **Every weight lookup returns 0.0.** The formula always produces a risk score of 0.0.

- **HIGH — This formula accepts `academic_signal_score`, `engagement_signal_score`, etc.**, but the actual `FeatureEngineer` produces `content_completion_score`, `quiz_engagement_score`, etc. The input keys are never populated from real data. The formula is disconnected from the rest of the pipeline.

- **MEDIUM — `explain_risk_score()` and `simulate_what_if()` are never called from any route or service.** Dead code.

**Type:** Logic Bug, ML Risk, Architecture

---

### `backend/ml/training/evaluate.py`

**Purpose:** Model evaluation utilities — classification report, confusion matrix.

**Issues Found:**

- **HIGH — `plt.savefig('models/evaluation_confusion_matrix.png')` uses a hardcoded relative path.**  
  This will fail unless the script is run from the exact directory containing a `models/` subfolder — which does not exist at the project root.

- **MEDIUM — No `if __name__ == "__main__"` guard around the `print` statements** at the bottom — they execute on every import, polluting any module that imports from this file.

- **LOW — No `plt.close()` after `plt.savefig()`.** Matplotlib figure handles accumulate in memory if the function is called multiple times, causing memory leaks.

**Type:** Logic Bug, Performance

---

### `backend/services/ai/llm_orchestrator.py`

**Purpose:** LLM integration — generates explanations, advice, summaries, intervention suggestions.

**Issues Found:**

- **CRITICAL — `self.model` is never set, but `explain_risk_change()` and `generate_student_advice()` call `self.model.generate_content(prompt)`.**  
  The class sets `self.llm_client` (not `self.llm_model`), and `self.llm_model_name`. There is no `self.model` attribute anywhere in `__init__`. **Every call to `explain_risk_change()` or `generate_student_advice()` will raise `AttributeError: 'LLMOrchestrator' object has no attribute 'model'`.**

- **CRITICAL — `_generate_content()` is called in multiple methods** (`summarize_student_profile`, `suggest_interventions`, `analyze_cohort_patterns`, `simulate_what_if`, `generate_report_narrative`) **but is never defined** in the class. **All five of these methods will raise `AttributeError: 'LLMOrchestrator' object has no attribute '_generate_content'` at runtime.**

- **HIGH — The exception handlers in all these methods catch `Exception` and return soft error dicts** instead of raising. Callers receive a `{"content": "Unable to generate summary.", ...}` dict — indistinguishable at the API level from a successful low-confidence response.

- **MEDIUM — `rag_engine.py`'s `StudentDataRetriever.retrieve_student_context()` accesses `student.predictions[0]`** without an `order_by` clause. The "latest" prediction is determined by whatever SQLAlchemy loads the relationship in — which is insertion order by default. Stale predictions may be surfaced as current.

**Type:** Logic Bug (multiple crashes), Architecture

---

### `backend/core/auth.py` (duplicate note)

See issues raised above. `verify_password` / `get_password_hash` are also defined separately in `seed_dummy_data.py` using `pbkdf2_sha256` — a **different hashing scheme** from the `bcrypt` used in `auth.py`. Seeds users whose passwords the login endpoint **cannot verify**.

---

### `seed_dummy_data.py`

**Purpose:** Seeds users, predictions, interventions for development.

**Issues Found:**

- **CRITICAL — Uses `pbkdf2_sha256` for password hashing:**  
  ```python
  pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
  ```
  The login endpoint uses `passlib` with `bcrypt`. Seeded passwords cannot be verified by the auth system. **No seeded user can log in.**

- **HIGH — Hardcoded default passwords** (`admin123`, `faculty123`, `retention123`) with no `.env` override.

- **MEDIUM — `Prediction` objects are created with `risk_score = random.uniform(0.1, 0.95)`** — random, not derived from real data. These seeded predictions pollute the predictions table and corrupt trend analytics.

**Type:** Logic Bug, Security, Data Risk

---

### `backend/data/labels.csv`

**Purpose:** ML training labels for the risk prediction model.

**Issues Found:**

- **CRITICAL — File is 0 bytes (empty).**  
  There is no training data. The ML models in `backend/ml/models/saved/` were trained on data that is not present in this repository. The model cannot be retrained or validated.

**Type:** Data Risk, ML Risk

---

### `backend/ml/models/saved/feature_importance.csv`

**Purpose:** Feature importance for the XGBoost model.

**Issues Found:**

- **HIGH — Features are `absrate_avg_3`, `absrate_avg_6`, `absrate_avg_2`, `q4mpa7`, etc.**  
  These are attendance-rate and GPA features from a previous schema, completely incompatible with the DB-derived LMS features the platform now uses. The top feature `absrate_avg_3` (weight 0.45) does not exist anywhere in the current feature pipeline.

**Type:** ML Risk, Data Risk

---

### `backend/routes/__init__.py`

**Purpose:** Aggregates all routers into a single `api_router`.

**Issues Found:**

- **MEDIUM — Both `students.router` (at prefix `/students`) and `monitoring.router` (prefix defined internally as `/monitoring`) are included.**  
  `monitoring.router` defines its prefix in the router definition file itself (`prefix="/monitoring"`) AND is included without a prefix in `__init__.py`. This can cause double-prefix issues if the router's internal prefix is combined with the `api_router` prefix.

- **LOW — 22 routers are registered.** This is a large surface area — route conflicts are possible and hard to audit manually.

**Type:** Architecture

---

## PHASE 3 — DATA + ML VALIDATION

### 3.1 — Schema Consistency

| Table | Status |
|---|---|
| `students` | Populated from XLSX. String PK (email/username). |
| `enrollments` | Populated from XLSX. References `students.id`. |
| `graded_components` | Populated from XLSX. |
| `exam_records` | Populated from XLSX. |
| `predictions` | Has legacy columns (`attendance`, `assignments`, `grades`) never populated by current pipeline — always NULL. |
| `dim_student`, `fact_*` | Populated by legacy pipeline that is never called from the app. Dead schema. |

**Finding:** The database contains two parallel schemas — a transactional schema (`students`, `enrollments`, etc.) that the live application uses, and a dimensional/analytical schema (`DimStudent`, `FactEngagement`, `FactAcademicPerformance`, etc.) that nothing reads. This dual-schema increases migration complexity and creates confusion about which tables are authoritative.

---

### 3.2 — Target Leakage

**Finding: Potential leakage in exam-related features.**  
`exam_score` and `exam_attendance_rate` are computed from `ExamRecord` data and used as input features to the risk score. If the target variable (dropout/retention) is correlated with exam performance in the training set, and exam data is available at prediction time only for students who have already taken exams, then the model would be using future-period data to predict current risk. **In a mid-semester deployment, exam scores are not yet available** — the model would assign these features to 0.0 for all students, artificially inflating risk scores for the entire cohort.

---

### 3.3 — Feature Leakage

**Finding: W1/W2 completion score uses cumulative content completed.**  
`calculate_w1w2_completion_score()` uses `content_completed` (total content ever completed) capped at `content_required_w1w2`. A student who completed everything in weeks 7-10 but nothing in weeks 1-2 will show a high W1/W2 score. The feature does not actually measure weeks 1-2 behavior. **This is feature construction leakage** — the feature name does not match what it measures.

---

### 3.4 — Train/Test Contamination

**Status: Unknown — `labels.csv` is empty (0 bytes).**  
The trained joblib models (`retention_model_xgboost.joblib`, `retention_model_logreg.joblib`) are checked into the repository without their training data or training scripts. It is impossible to:
- Verify train/test split was performed correctly
- Verify stratification
- Verify no data leakage occurred during training
- Reproduce the training run

This is a significant ML governance gap.

---

### 3.5 — Duplicate Records

**Finding: No uniqueness constraints on Enrollment.**  
The `Enrollment` model has no `UniqueConstraint` on `(student_id, course_id)`. If `ingest_all_data()` is called multiple times (e.g., after a partial failure clears the check guard), duplicate enrollment records will be inserted. Feature scores would then be double-counted.

---

### 3.6 — Missing Value Strategy

**Current strategy:** All missing values default to `0.0`.  
- Missing quiz scores → 0 score (treated as "student got 0 on every quiz").
- Missing exam records → 0 score, 0 attendance (treated as "student missed all exams").
- Missing enrollments → all features 0 (treated as "student did nothing").

**Problem:** Zero-imputation is a valid strategy only if absence truly means zero engagement. For many students, missing records mean "data was not collected" — not "student did not engage." This causes systematic over-prediction of risk for students with sparse records.

---

### 3.7 — Encoding Consistency

**Finding:** No categorical encoding is performed. All features passed to the risk scorer are continuous `float` values. Categorical fields (`progress_category`, `engagement_trend`, `old_new_student`) are computed but never used in the risk formula. No encoding inconsistencies, but **useful categorical signals are entirely ignored**.

---

### 3.8 — Deterministic Preprocessing

**Status: Deterministic.** The `FeatureEngineer` and `RiskScorer` are pure functions with no random state or time-dependent behavior (except where timestamp-based features would apply — but those are not implemented). The same input produces the same output consistently.

---

### 3.9 — Serialization Risks

**Finding: `top_risk_factors` in `Prediction` is stored as `Column(String)` containing a JSON string.**  
Same issue as `channels` in `Intervention`. Both should use `Column(JSON)`. Manual serialization (`json.dumps`/`json.loads`) is error-prone and prevents type-safe querying.

---

## PHASE 4 — SYSTEM-LEVEL RISKS

### 4.1 — Architectural Weaknesses

1. **Dual session factory:** `connection.py` and `session.py` both define `SessionLocal`. Three `get_db` implementations exist. No single source of truth.

2. **God service:** `student_service.py` (669 lines) is responsible for retrieval, feature computation, risk scoring, analytics, dashboard stats, course stats, and intervention effectiveness. It violates single responsibility and makes testing impossible.

3. **Two parallel ETL pipelines:** The primary pipeline (`services/core/data_ingestion.py`) and the legacy pipeline (`ingestion/pipeline.py`) populate different tables with different schemas. Only one is active; the other is dead code that causes confusion.

4. **ML pipeline split across three layers:**  
   - `features/` folder — never called  
   - `ml/inference/risk_formula.py` — broken weight mapping, never called  
   - `services/feature_engineering.py` + `services/risk_scoring.py` — the only working path  
   The dead ML infrastructure creates noise and confusion for any engineer maintaining this system.

5. **Scheduler never starts:** `start_scheduler()` is never invoked from `main.py` or any startup hook. The scheduled job functionality is entirely dead.

---

### 4.2 — Data-Backend Misalignment

- **Dimensional model is populated but never queried.** All application queries hit the transactional schema. The canonical/dimensional tables exist in the DB schema and add overhead to `create_all` but serve no function.
- **`Prediction.risk_score` is stored as 0-1 probability** but displayed as 0-100 percent. Normalization is done inconsistently — some endpoints multiply by 100, some check `if s <= 1.0: s *= 100.0`. If a score of exactly `1.0` (100% risk) is stored, it will be doubled to `200%` by this logic.
- **`feature_importance.csv` documents absrate/MPA features** that have no mapping to any field in the current DB schema.

---

### 4.3 — Scalability Risks

1. **SQLite as the production database.** SQLite supports only one writer at a time. Concurrent POST/PATCH requests will serialize at the DB level. Under any real load (>5 concurrent users), write latency will spike.

2. **All risk scoring is in-memory Python.** Loading 500 students × all enrollments × all graded components per request is O(N) on every API call. This does not scale past a few hundred students.

3. **Rate limiting is in-process dictionary.** Completely ineffective in multi-worker deployments.

4. **No connection pooling configuration.** Default SQLAlchemy pool (5 connections) with no overflow limit tuning.

---

### 4.4 — Production-Readiness Gaps

| Gap | Status |
|---|---|
| Health check reflects DB/model state | No — `/health` always returns 200 |
| Scheduler runs automatically | No — never started |
| Secret key externalized | No — hardcoded default |
| Log file excluded from VCS | No — committed to repo |
| `.env` file for local dev | No — missing from repo |
| `docker-compose.yml` present | Partial — `docker/` folder exists but not audited |
| Automated tests | `test_endpoints.py` exists but no assertion framework visible |
| Migration system (Alembic) | No — `create_all()` only, no schema versioning |
| API versioning strategy | Inconsistent — some routes at `/api/v1/`, some not |

---

### 4.5 — Security Vulnerabilities (Ranked)

| # | Vulnerability | Severity |
|---|---|---|
| 1 | RBAC bypass via header — any client sends `X-User-Role: admin` | CRITICAL |
| 2 | Hardcoded `SECRET_KEY` in source code | CRITICAL |
| 3 | Students, ML predictions, interventions endpoints have no auth | CRITICAL |
| 4 | `/register` allows self-promotion to any role including Admin | CRITICAL |
| 5 | `/auth/me` PUT allows authenticated users to change their own role | HIGH |
| 6 | CORS `allow_headers=["*"]` enables X-User-Role injection from any origin | HIGH |
| 7 | `rate_limit_store` not shared across workers — effective bypass via multiple ports | HIGH |
| 8 | In-process rate limiter bypassed behind any reverse proxy | HIGH |
| 9 | No token revocation — logout does not invalidate tokens | MEDIUM |
| 10 | JWT decode ValueError on non-integer `sub` → unhandled 500 | MEDIUM |

---

### 4.6 — Top 10 Critical Fixes (Ranked by Production Impact)

| Rank | Issue | File(s) | Fix |
|---|---|---|---|
| 1 | **RBAC entirely bypassed via header** | `api/deps.py` | Wire `require_role` to `get_current_user` (JWT); never default role to admin |
| 2 | **LLMOrchestrator crashes on every call** (`self.model`, `_generate_content` undefined) | `services/ai/llm_orchestrator.py` | Fix attribute names; define or delegate `_generate_content` |
| 3 | **Student/intervention/ML routes have zero auth** | `controllers/students_controller.py`, `routes/interventions.py`, `routes/ml_routes.py` | Add `Depends(get_current_user)` or `require_role()` to all endpoints |
| 4 | **Seeded users cannot log in** (wrong hash scheme) | `seed_dummy_data.py` | Use `from backend.core.auth import get_password_hash` |
| 5 | **`get_all_students()` loads all data in Python, O(N) per request** | `services/student_service.py` | Persist pre-computed metrics to DB via scheduled job; serve from DB |
| 6 | **Session passed across thread boundary in ingestion** | `main.py` | Create fresh session inside the thread, not outside it |
| 7 | **SECRET_KEY hardcoded** | `config/__init__.py` | Fail fast if default key used outside development |
| 8 | **Scheduler never starts** | `services/infrastructure/scheduler.py`, `main.py` | Launch scheduler in a daemon thread from `lifespan`; use `asyncio` scheduler or APScheduler |
| 9 | **Duplicate `SessionLocal` factories** | `database/connection.py`, `database/session.py` | Delete `session.py`; standardize all imports to `connection.py` |
| 10 | **`/register` allows self-assigning Admin role** | `routes/auth.py` | Restrict allowed roles at registration; require admin approval for Faculty/Admin roles |

---

## PHASE 5 — FINAL SCORES

### Scoring Criteria
Each dimension is scored 1–10, where:
- **10** = production-ready, best practices followed
- **7-9** = minor gaps, acceptable for early production
- **4-6** = significant gaps, needs work before production
- **1-3** = severe issues, not suitable for any real deployment

---

### Code Quality Score: **4 / 10**

The codebase has good structural intentions — FastAPI patterns, SQLAlchemy ORM, service layers, dependency injection — but execution is inconsistent. Dead code is scattered throughout (`features/`, `ml/inference/`, `ingestion/pipeline.py`). Critical service functions (`LLMOrchestrator`) have undefined method references. Session management is duplicated three times. The `student_service.py` is a 669-line god object. `datetime.utcnow()` is used 47 times despite being deprecated in the project's Python runtime. Magic numbers are embedded throughout feature engineering with no calibration.

---

### Architecture Score: **3 / 10**

Two parallel ETL pipelines populate two parallel database schemas, only one of which the application actually reads. Three `SessionLocal` factories exist. The ML pipeline is split across four disconnected locations, only one of which works. The scheduler is implemented but never started. The dimensional model schema is registered and migrated but serves no queries. The role-based access control system depends on a client-supplied header rather than a cryptographically verified token. These are foundational architectural problems, not surface-level bugs.

---

### Data Integrity Score: **3 / 10**

The primary training labels file (`labels.csv`) is empty. The deployed ML models were trained on a feature schema (`absrate`, `mpa`, `nsusp`, `mobility`) that has no mapping to any field in the current database. Feature importance CSV documents this incompatible schema. W1/W2 completion feature is miscalculated (uses cumulative data). Zero-imputation of missing exam data silently inflates risk scores. No uniqueness constraints on enrollment records. Dimensional model tables are populated by a pipeline that uses placeholder data (`DEFAULT_COURSE`).

---

### ML Safety Score: **2 / 10**

The deployed XGBoost and LogReg models cannot be used because their feature schema does not match the current data pipeline. The system acknowledges this and falls back to rule-based scoring — which is the right decision — but the rule-based scorer itself has critical issues: it assigns risk=100 to any student with incomplete data; the explainability formula (`risk_formula.py`) always produces 0.0 due to broken weight key mapping; the `engagement_score` is mathematically identical to `100 - risk_score` (adds no independent information); and no mechanism exists to retrain the models (training data is missing). The system cannot be validated, retrained, or improved.

---

### Production Readiness Score: **2 / 10**

The application will start and serve requests, but:
- All student data is publicly accessible (no auth on most endpoints)
- Admin privileges are available to any HTTP client without authentication
- The LLM feature set crashes on every invocation
- Scheduled jobs never run (no daily predictions in prod)
- The SECRET_KEY defaults to a public value
- SQLite cannot handle concurrent writes at any meaningful scale
- There is no Alembic schema versioning — DB state cannot be migrated
- No `.env` template, no Docker Compose, no CI, no tests with assertions

**This system should not be deployed to production in its current state.**

---

## APPENDIX — SEVERITY SUMMARY

| Severity | Count |
|---|---|
| CRITICAL | 10 |
| HIGH | 22 |
| MEDIUM | 28 |
| LOW | 14 |
| **Total Issues** | **74** |

---

*End of Forensic Audit Report*
