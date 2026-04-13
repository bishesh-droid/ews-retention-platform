# EWS RETENTION PLATFORM — FULL PRE-INTEGRATION AUDIT

**Date:** 2026-04-13  
**Auditor:** Senior Software Engineer  
**Scope:** Complete codebase audit for AI Academic Advisor integration readiness

---

## EXECUTIVE SUMMARY

The EWS Retention Platform is a FastAPI-based student risk-scoring system with 25 route modules, 25+ SQLAlchemy models, and a rule-based ML pipeline. The codebase has undergone significant security hardening since initial development but presents several integration blockers that must be addressed before SOA unification.

**Overall Assessment:** The platform is structurally sound but requires targeted remediation in async consistency, PostgreSQL migration readiness, and API contract standardization before integration.

---

## 1. SECURITY

### 1.1 JWT Implementation
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **SEC-001** | LOW | `backend/core/auth.py:68-75` | JWT claims are correctly implemented with `iss`, `aud`, `jti`, `nbf`, `iat`, `exp`, `sub`, `role`, `type`. Token validation requires all claims. |
| **SEC-002** | INFO | `backend/config/__init__.py:137` | Algorithm is configurable via env (default HS256) but should be restricted to asymmetric algorithms (RS256) in production for multi-service trust. |
| **SEC-003** | LOW | `backend/config/__init__.py:138` | Token expiry defaults to 60 minutes (configurable). No sliding session mechanism implemented. |

**Status:** JWT implementation is production-ready with proper claims and validation.

### 1.2 Token Refresh & Revocation
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **SEC-004** | INFO | `backend/routes/auth.py:97-173` | Refresh token endpoint implemented with httpOnly cookie rotation. Proper token type validation enforced. |
| **SEC-005** | INFO | `backend/routes/auth.py:179-227` | Logout endpoint correctly revokes tokens via JTI blocklist in `revoked_tokens` table. |
| **SEC-006** | MEDIUM | `backend/api/deps.py:96-103`, `168-179` | Token revocation check implemented in both sync and async auth dependencies. Blocklist query adds ~5-10ms latency per request. |
| **SEC-007** | INFO | `backend/services/infrastructure/scheduler.py:307-317` | Expired revoked tokens purged nightly via scheduled job. |

**Status:** Token lifecycle management is complete and operational.

### 1.3 Password Security
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **SEC-008** | INFO | `backend/core/auth.py:82-83` | bcrypt rounds explicitly set to 12 — meets OWASP recommendations. |

**Status:** Password hashing is correctly configured.

### 1.4 RBAC & Authorization
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **SEC-009** | MEDIUM | `backend/api/deps.py:208-242` | `require_role` dependency factory correctly validates JWT-embedded roles. Superuser bypass documented. |
| **SEC-010** | HIGH | `backend/api/deps.py:245-316` | `ResourceOwnershipChecker` enforces FERPA compliance with staff/student ownership logic. **Issue:** Uses sync DB query inside dependency which may block async event loop. |
| **SEC-011** | LOW | Multiple routes | Most admin routes correctly use `require_role([Role.ADMIN])`. Some use string literals instead of constants (e.g., `require_role(["admin"])`). |

**Status:** RBAC is functionally correct but has async consistency issues.

### 1.5 SQL Injection & ORM Safety
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **SEC-012** | INFO | All models | SQLAlchemy ORM used consistently. No raw SQL with string interpolation detected. |
| **SEC-013** | MEDIUM | `backend/routes/admin_v1.py:115-178` | `update_course_registry` accepts arbitrary dict payload without Pydantic validation. Potential for unexpected key injection. |

### 1.6 Rate Limiting
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **SEC-014** | MEDIUM | `backend/core/rate_limiting.py` | Global limiter uses IP-based keys. Many routes lack explicit `@limiter.limit()` decorators, falling back to default 200/minute. |
| **SEC-015** | INFO | `backend/routes/auth.py:38`, `backend/routes/admin_ingest.py:40` | Critical endpoints (login, ingest) have explicit rate limits: 5/minute for login, 10/hour for ingest. |
| **SEC-016** | LOW | `backend/core/rate_limiting.py:44-118` | LLM-specific rate limiting implemented (5/min, 20/hour per user). |

**Gap Analysis:** Rate limiting coverage is incomplete. The following route modules lack explicit limits:
- `student_v1.py` — student self-service endpoints
- `faculty_v1.py` — faculty queries
- `interventions.py` — intervention CRUD
- `reports.py` — report generation (potentially expensive)

### 1.7 CORS Configuration
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **SEC-017** | MEDIUM | `backend/main.py:232-254` | CORS allows `allow_credentials=True` with configurable origins. Production validation blocks localhost origins. |
| **SEC-018** | INFO | `backend/config/__init__.py:30-33` | Origins parsed from comma-separated env var with deduplication. |

**Status:** CORS is appropriately configured for pre-integration phase.

### 1.8 Secrets Management
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **SEC-019** | CRITICAL | `backend/config/__init__.py:65` | `SECRET_KEY` loaded from env without file-based secret fallback. **Live API key detected in .env** — Claude API key present at line 7. |
| **SEC-020** | HIGH | `backend/config/__init__.py:109-114` | Configuration validation detects live Anthropic keys and raises RuntimeError in non-dev environments. |

**Immediate Action Required:** Remove live API key from `.env` and rotate the exposed key.

### 1.9 Dependency Security
| Finding | Severity | Details |
|---------|----------|---------|
| **SEC-021** | INFO | Dependencies pinned in `requirements.txt`. FastAPI 0.119.0 is current. PyJWT 2.12.0 has no known CVEs. |
| **SEC-022** | LOW | slowapi 0.1.9 is stable but less actively maintained. Consider migrating to `fastapi-limiter` for better Redis Cluster support. |

---

## 2. DATABASE INTEGRITY

### 2.1 SQLite → PostgreSQL Migration Blockers
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **DB-001** | HIGH | `backend/database/connection.py:18-37` | SQLite-specific pragmas (`foreign_keys = ON`, `check_same_thread`) are conditional but schema uses `String` columns without length limits — incompatible with PostgreSQL strict mode. |
| **DB-002** | MEDIUM | `backend/database/models/*.py` | Multiple models use `String` columns without `length` parameter. PostgreSQL requires explicit lengths for VARCHAR. |
| **DB-003** | MEDIUM | `backend/database/connection.py:52-64` | Async engine uses `aiosqlite` for SQLite but PostgreSQL path doesn't validate `asyncpg` availability. |

**Affected Models:**
- `user.py` — `username`, `email`, `hashed_password`, `role`, `department` all unbounded String
- `student.py` — `first_name`, `last_name`, `org_defined_id` unbounded
- `intervention.py` — multiple String columns without length

### 2.2 Missing Indexes
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **DB-004** | MEDIUM | `backend/database/models/prediction.py` | `student_id` is FK but no explicit index defined (relies on implicit FK index which varies by dialect). |
| **DB-005** | LOW | `backend/database/models/enrollment.py` | `student_id` + `course_id` composite queries likely without covering index. |
| **DB-006** | INFO | `backend/database/models/student.py:33-39` | Good coverage: indexes on `department`, `org_id`, `is_active`, composite `dept+active`. |

### 2.3 Nullable Column Issues
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **DB-007** | MEDIUM | `backend/database/models/user.py:17` | `department` nullable with no default — fine for students, but faculty without department may bypass department-scoped queries. |
| **DB-008** | LOW | Multiple models | `created_at` columns use `default=datetime.utcnow` but should use `server_default=func.now()` for DB-level consistency. |

### 2.4 Missing Unique Constraints
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **DB-009** | HIGH | `backend/database/models/enrollment.py` | No unique constraint on `(student_id, course_id, semester_name)` — allows duplicate enrollment records. |
| **DB-010** | MEDIUM | `backend/database/models/graded_component.py` | No unique constraint on `(student_id, component_type, component_number, course_id)` — allows duplicate grade entries. |

### 2.5 Cascade Delete Correctness
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **DB-011** | INFO | `backend/database/models/student.py:56-103` | Comprehensive cascade rules defined on all relationships. `cascade="all, delete-orphan"` present. |
| **DB-012** | MEDIUM | `backend/database/models/revoked_token.py:31` | FK to `users.id` with `ondelete="CASCADE"` — token cleanup on user deletion. Good. |

### 2.6 Alembic Migration Chain
| Finding | Severity | Details |
|---------|----------|---------|
| **DB-013** | INFO | 10 migration files present with sequential numbering (001-010). |
| **DB-014** | MEDIUM | Migration `009_add_revoked_tokens_table.py` defines `user_id` as String but `users.id` is Integer — type mismatch. |
| **DB-015** | LOW | No downgrade implemented in migrations 001-010 — rollback not possible without manual intervention. |

### 2.7 N+1 Query Risks
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **DB-016** | HIGH | `backend/routes/admin_v1.py:27-35` | `list_users` returns all users without pagination — unbounded result set. |
| **DB-017** | MEDIUM | `backend/services/scheduler.py:76-247` | `generate_daily_predictions` uses batch processing (BATCH_SIZE=100) with keyset pagination — good. But nested loops query relationships without eager loading. |
| **DB-018** | MEDIUM | `backend/routes/interventions.py:101-130` | `list_interventions` joins Student but doesn't eagerly load — N+1 risk in `_to_dict()` serialization. |

### 2.8 Transaction Boundaries
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **DB-019** | MEDIUM | `backend/routes/auth.py:230-264` | `register` endpoint uses sync session in what should be async context (route is sync). Commit without explicit rollback on exception. |
| **DB-020** | INFO | `backend/database/connection.py:92-101`, `104-125` | Dependencies provide proper rollback in `finally` blocks. |

---

## 3. ASYNC CORRECTNESS

### 3.1 Sync DB Calls in Async Routes
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ASYNC-001** | CRITICAL | `backend/api/deps.py:245-316` | `ResourceOwnershipChecker.__call__` uses `with get_db() as db:` inside async dependency. This blocks the event loop. |
| **ASYNC-002** | HIGH | `backend/routes/auth.py:230-264` | `register` endpoint is sync but called from async context. Uses `db.query().filter().first()` pattern. |
| **ASYNC-003** | MEDIUM | `backend/routes/auth.py:267-274`, `277-311` | `get_current_profile` and `update_current_profile` are sync endpoints. |
| **ASYNC-004** | HIGH | `backend/routes/admin_v1.py:27-35` | `list_users` is sync endpoint with unbounded query. |

**Pattern Analysis:** Many routes use sync SQLAlchemy patterns (`db.query()`) instead of async (`await db.execute(select(...))`). This creates blocking I/O in the async event loop.

### 3.2 Blocking I/O in Async Paths
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ASYNC-005** | MEDIUM | `backend/routes/admin_ingest.py:80` | `magic.from_buffer()` call may block on large files. |
| **ASYNC-006** | MEDIUM | `backend/services/ml_service.py:90` | `joblib.load()` blocks when loading large model files. |
| **ASYNC-007** | LOW | `backend/services/scheduler.py:355` | `asyncio.to_thread()` correctly offloads blocking prediction work, but `generate_daily_predictions` itself does sync DB operations. |

### 3.3 Missing `await` on Coroutines
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ASYNC-008** | INFO | Codebase scan | No obvious missing `await` detected. All async dependencies properly awaited. |

### 3.4 Background Task Correctness
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ASYNC-009** | MEDIUM | `backend/routes/admin_ingest.py:119-146` | `run_ingestion` background task creates new `SessionLocal()` but doesn't properly handle async-to-sync boundary. Uses `await ingest_all_data()` but session is sync. |
| **ASYNC-010** | INFO | `backend/services/infrastructure/scheduler.py:442-473` | Scheduler uses `asyncio.create_task()` with proper cancellation handling. `asyncio.to_thread()` for sync work. |

### 3.5 Async Context Managers
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ASYNC-011** | INFO | `backend/database/connection.py:104-125` | `get_db_async()` correctly uses `async with AsyncSessionLocal()`. |
| **ASYNC-012** | MEDIUM | `backend/database/connection.py:116-118` | Async pragma execution creates extra connection context — minor overhead. |

---

## 4. ML PIPELINE

### 4.1 XGBoost Status
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ML-001** | INFO | `backend/services/ml_service.py:56-127` | XGBoost model loading attempted but feature count validation prevents use. Rule-based scoring is primary path. |
| **ML-002** | INFO | `backend/services/ml_service.py:280-293` | When XGBoost is available, predictions are blended 30% model / 70% rule-based. |
| **ML-003** | MEDIUM | `backend/services/ml_service.py:67-70` | Model path hardcoded: `ml/models/saved/retention_model_xgboost.joblib`. No env override. |

### 4.2 Joblib Model Loading
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ML-004** | MEDIUM | `backend/services/ml_service.py:74-90` | Missing model file handled gracefully (returns None). No fallback if `feature_names.json` missing. |
| **ML-005** | LOW | `backend/services/ml_service.py:125-127` | Exception in model loading logged but doesn't crash service. |

### 4.3 Feature Engineering
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ML-006** | MEDIUM | `backend/services/feature_engineering.py` | Module deprecated but still imported. Warnings emitted. New modular structure at `backend/services/features/`. |
| **ML-007** | INFO | `backend/services/risk_scoring.py:21-29` | Hardcoded feature key mapping in `_LOGICAL_TO_FEATURE_KEY`. |
| **ML-008** | INFO | `backend/config/__init__.py:200-208` | Feature weights configurable via environment. Validation ensures sum ≈ 1.0. |

### 4.4 Rule-Based Scoring Logic
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ML-009** | INFO | `backend/services/risk_scoring.py:102-127` | Handles missing values by skipping (not defaulting to 0). Self-directed learning correctly inverted. |
| **ML-010** | MEDIUM | `backend/services/risk_scoring.py:156-306` | `calculate_risk_score` has complex control flow with academic flags override. **Ghost student override at line 256 forces risk to 95.0** — may be too aggressive. |
| **ML-011** | LOW | `backend/services/risk_scoring.py:252-259` | Ghost detection override happens after all calculations — cannot be diluted by other factors. |

### 4.5 Model Versioning
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ML-012** | INFO | `backend/config/__init__.py:133` | `RISK_MODEL_VERSION` env-configurable, defaults to "rule-based-v1.0". Stored with every prediction. |
| **ML-013** | INFO | `backend/services/ml_service.py:265-266`, `396-401` | Model version propagated to features and stored in prediction records. |

### 4.6 Inference Latency Risk
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ML-014** | MEDIUM | `backend/services/ml_service.py:225-344` | `predict_student` runs synchronously. No async model inference. At scale, this blocks request handling. |
| **ML-015** | INFO | `backend/services/scheduler.py:76-247` | Batch predictions run in background job — appropriate for heavy workload. |

### 4.7 Prediction Logging
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ML-016** | INFO | `backend/services/risk_scoring.py:395-435` | `_log_prediction` writes to `PredictionLog` table. Best-effort (swallows exceptions). |
| **ML-017** | MEDIUM | `backend/database/models/prediction_log.py` | Model exists but not imported in `connection.py` init. **Missing from init_db model imports.** |

### 4.8 Feature Store
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **ML-018** | INFO | `backend/services/feature_store_service.py` | Feature store service exists but is thin abstraction over DB queries. |
| **ML-019** | MEDIUM | No centralized feature store. Features computed on-demand from enrollment/graded/exam records. Caching limited to in-process dict in MLService. |

---

## 5. API CONTRACT

### 5.1 Response Schema Consistency
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **API-001** | MEDIUM | `backend/utils/api.py:72-92` | `success_response()` provides standard envelope: `{success, message, data, meta}`. Widely used. |
| **API-002** | HIGH | `backend/routes/admin_v1.py:69-84`, `171-178` | Some endpoints return raw dicts/lists without `success_response()` wrapper. Inconsistent with standard. |
| **API-003** | MEDIUM | `backend/routes/auth.py:91-94` | Login returns `{access_token, token_type}` without success wrapper. Special case (OAuth2) but inconsistent. |

**Inconsistent Endpoints:**
- `GET /api/v1/admin/ingestion-runs` — returns raw list
- `PUT /api/v1/admin/course-registry/{code}` — returns raw dict
- `POST /api/v1/admin/ingest` — returns raw dict

### 5.2 Missing Response Models
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **API-004** | MEDIUM | `backend/routes/admin_v1.py:115-178` | `update_course_registry` accepts `request: dict` — no Pydantic validation. |
| **API-005** | MEDIUM | `backend/routes/admin_ingest.py:148-153` | `trigger_ingestion` returns raw dict without response model. |

### 5.3 HTTP Status Codes
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **API-006** | LOW | `backend/routes/auth.py:230` | Register returns 201 (correct). |
| **API-007** | LOW | `backend/routes/admin_ingest.py:39` | Ingest returns 202 Accepted (correct for async). |
| **API-008** | INFO | `backend/routes/interventions.py:133` | Create intervention returns 200 (should be 201). |
| **API-009** | INFO | `backend/routes/interventions.py:177` | Update intervention returns 200 (should be 200 or 204). |

### 5.4 Error Response Format
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **API-010** | INFO | `backend/core/errors.py:39-79` | Unified SOA error format implemented: `{error: {code, message, details, request_id, timestamp}}`. |
| **API-011** | HIGH | `backend/utils/api.py:95-105` | `error_response()` uses old format `{success: false, message, data}` — **inconsistent with SOA standard**. |

**Dual Error Formats Detected:**
- `backend/core/errors.py` — SOA unified format (new)
- `backend/utils/api.py` — Legacy format (old)
- Routes mix both depending on which utility they import

### 5.5 Pagination
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **API-012** | MEDIUM | `backend/routes/interventions.py:101-130` | `list_interventions` has `skip`/`limit` but uses offset pagination (inefficient for large tables). |
| **API-013** | GOOD | `backend/routes/admin_v1.py:49-84` | `list_ingestion_runs` has proper pagination with skip/limit. |
| **API-014** | MISSING | `backend/routes/admin_v1.py:27-35` | `list_users` has no pagination — unbounded. |

### 5.6 Route Naming & Versioning
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **API-015** | INFO | `backend/routes/__init__.py:42-71` | Auth routes correctly at `/auth/*` (per API-2 comment). API v1 routes at `/api/v1/*`. |
| **API-016** | LOW | `backend/main.py:299-300` | Router inclusion slightly confusing — `api_router` has prefix `/api/v1`, but `ingest_router` also added with same prefix. |
| **API-017** | MEDIUM | Multiple routes | Inconsistent tag naming: "AI Academic Advisor" vs "llm" vs "Machine Learning". |

### 5.7 Request Validation
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **API-018** | GOOD | `backend/schemas/common.py:86-94` | `STUDENT_ID_FIELD` with regex validation for FERPA compliance. |
| **API-019** | MEDIUM | `backend/routes/admin_v1.py:49-55` | Query params `limit`/`skip` have validation but `semester`/`program` strings have no validation. |

---

## 6. CODE QUALITY

### 6.1 Dead Code
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **CODE-001** | LOW | `backend/routes/__init__.py:16-24` | Dead route audit comments list disabled routes: predictions, events, feedback. |
| **CODE-002** | LOW | `backend/routes/predictions.py` | File exists but not included in router (2 matches only — minimal content). |
| **CODE-003** | LOW | `backend/routes/events.py` | Disabled in router but file present (7 route functions defined). |
| **CODE-004** | LOW | `backend/routes/feedback.py` | Disabled in router but file present (4 route functions defined). |
| **CODE-005** | INFO | `backend/services/feature_engineering.py:38-43` | Deprecation warning emitted on import. Delegates to new modular structure. |

### 6.2 God Functions / Service Layer
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **CODE-006** | MEDIUM | `backend/services/feature_engineering.py` | 955 lines — feature engineering logic mixed in single file. Being refactored to `backend/services/features/`. |
| **CODE-007** | MEDIUM | `backend/services/risk_scoring.py:156-306` | `calculate_risk_score` is 150+ lines with multiple responsibilities: sanitization, weighting, calendar blending, overrides. |
| **CODE-008** | MEDIUM | `backend/routes/admin_v1.py` | 576 lines — admin routes mixed with business logic (intervention effectiveness queries). |

### 6.3 Service Layer Completeness
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **CODE-009** | MEDIUM | `backend/routes/admin_v1.py:195-247` | `get_intervention_effectiveness` constructs raw SQL-like queries inline. Should be in service layer. |
| **CODE-010** | GOOD | `backend/services/student_service.py` | Student operations properly abstracted. |

### 6.4 Dependency Injection
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **CODE-011** | GOOD | `backend/api/deps.py` | Well-structured dependencies for DB, auth, roles, ownership. |
| **CODE-012** | MEDIUM | `backend/routes/admin_v1.py:115-178` | `update_course_registry` imports models inside function — should be at module level. |

### 6.5 Duplicate Logic
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **CODE-013** | MEDIUM | `backend/api/deps.py:61-124`, `127-201` | `get_current_user` and `get_current_user_async` have nearly identical JWT validation code. Could be refactored to share validation logic. |
| **CODE-014** | LOW | `backend/services/risk_scoring.py:128-154`, `101-127` | Legacy and current weighted engagement calculations share structure but use different weight sources. |

### 6.6 Logging Quality
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **CODE-015** | GOOD | `backend/middleware/request_id.py` | Request ID propagation implemented. |
| **CODE-016** | MEDIUM | Multiple routes | Many routes don't include request_id in log context. Structured logging (JSON) not consistently used. |
| **CODE-017** | INFO | `backend/core/logger.py` (implied) | `sys_logger` used but not all modules import it consistently. |

### 6.7 Exception Handling
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **CODE-018** | GOOD | `backend/core/errors.py:130-141` | Unhandled exception handler provides safe generic message with request_id. |
| **CODE-019** | MEDIUM | `backend/routes/auth.py:351-371` | Audit logging in `admin_update_user` has broad `except Exception` that swallows and logs but doesn't re-raise. Appropriate for audit but may hide issues. |
| **CODE-020** | LOW | `backend/services/ml_service.py:342-344` | Prediction failure returns error dict with default values. Error not propagated to caller. |

### 6.8 Config Management
| Finding | Severity | Location | Details |
|---------|----------|----------|---------|
| **CODE-021** | GOOD | `backend/config/__init__.py` | Pydantic-style validation functions present. Environment variables with safe defaults. |
| **CODE-022** | MEDIUM | `backend/config/__init__.py:39-55` | DATABASE_URL handling complex with testing branch. Could use Pydantic BaseSettings for cleaner structure. |

---

## 7. TEST COVERAGE

### 7.1 Untested Routes
| Finding | Severity | Route Module | Test Status |
|---------|----------|--------------|-------------|
| **TEST-001** | HIGH | `admin_v1.py` | No dedicated test file. Only covered by integration tests. |
| **TEST-002** | HIGH | `faculty_v1.py` | No dedicated test file. |
| **TEST-003** | HIGH | `reports.py` | No dedicated test file. 11 route functions untested. |
| **TEST-004** | MEDIUM | `business.py` | No dedicated test file. 10 route functions untested. |
| **TEST-005** | MEDIUM | `integration.py` | Partial coverage in `test_integration_api.py` only. |
| **TEST-006** | MEDIUM | `decisions.py` | No dedicated test file. |
| **TEST-007** | MEDIUM | `recommendations.py` | No dedicated test file. |
| **TEST-008** | LOW | `analytics.py` | No dedicated test file. |
| **TEST-009** | LOW | `goals.py` | No dedicated test file. |

### 7.2 Existing Test Files
| Test File | Coverage | Notes |
|-----------|----------|-------|
| `test_auth.py` | Good | Login, register, logout, refresh, token revocation. 226 lines. |
| `test_critical_paths.py` | Good | End-to-end scenarios. 17303 lines — comprehensive. |
| `test_risk_scoring.py` | Good | Risk calculation logic. 13038 lines. |
| `test_security_headers.py` | Good | Security middleware. 5017 lines. |
| `test_idor.py` | Good | IDOR vulnerability tests. 9898 lines. |
| `test_student_ownership.py` | Good | FERPA ownership checks. 6613 lines. |
| `test_scheduler.py` | Good | Background job tests. 9043 lines. |
| `test_llm_services.py` | Medium | LLM integration tests. 8372 lines. |
| `test_monitoring.py` | Medium | Health checks. 2892 lines. |
| `test_integration_api.py` | Medium | External API tests. 4692 lines. |
| `test_validation_suite.py` | Good | Input validation. 8141 lines. |
| `test_prompt_injection.py` | Good | LLM security. 18268 lines. |

### 7.3 Missing Test Types
| Finding | Severity | Details |
|---------|----------|---------|
| **TEST-010** | HIGH | No async DB pattern tests — sync/async boundary not verified. |
| **TEST-011** | HIGH | No PostgreSQL compatibility tests — SQLite-only test suite. |
| **TEST-012** | MEDIUM | No ML inference load tests — latency under concurrent load unknown. |
| **TEST-013** | MEDIUM | No rate limiting integration tests — SlowAPI limits not verified. |
| **TEST-014** | MEDIUM | No Redis failure scenario tests — fallback to memory not tested. |
| **TEST-015** | LOW | No backup/scheduler failure recovery tests. |

### 7.4 Test Data & Fixtures
| Finding | Severity | Details |
|---------|----------|---------|
| **TEST-016** | MEDIUM | `conftest.py` only 2275 lines. Limited fixture reuse across test files. |
| **TEST-017** | MEDIUM | Tests use hardcoded user credentials ("testuser"/"testpassword123") scattered across files. |
| **TEST-018** | INFO | Factory pattern not used — test data creation is procedural. |

---

## INTEGRATION READINESS SUMMARY

### Blockers (Must Fix Before Integration)

| ID | Priority | Issue | Effort |
|----|----------|-------|--------|
| SEC-019 | P0 | Remove live Claude API key from `.env` | 5 min |
| ASYNC-001 | P0 | Fix `ResourceOwnershipChecker` sync DB in async context | 2-4 hrs |
| DB-002 | P1 | Add length limits to String columns for PostgreSQL | 4-6 hrs |
| API-011 | P1 | Standardize error response format (remove legacy format) | 2-3 hrs |
| ASYNC-002 | P1 | Convert critical sync routes to async | 4-8 hrs |
| DB-009 | P1 | Add unique constraints to prevent duplicate data | 2-3 hrs |

### Warnings (Fix During Integration)

| ID | Priority | Issue | Effort |
|----|----------|-------|--------|
| SEC-014 | P2 | Add rate limiting to unprotected routes | 2-3 hrs |
| API-002 | P2 | Standardize response envelope usage | 4-6 hrs |
| DB-016 | P2 | Add pagination to unbounded queries | 2-4 hrs |
| ML-014 | P2 | Make model inference async | 4-6 hrs |
| CODE-013 | P2 | Refactor duplicate auth validation | 2-3 hrs |
| TEST-001 | P2 | Add tests for untested admin routes | 6-10 hrs |

### Recommendations (Post-Integration)

| ID | Priority | Issue | Effort |
|----|----------|-------|--------|
| DB-001 | P3 | Complete SQLite→PostgreSQL migration | 8-16 hrs |
| ML-003 | P3 | Make model path configurable | 1-2 hrs |
| CODE-006 | P3 | Complete feature engineering modularization | 4-8 hrs |
| TEST-011 | P3 | Add PostgreSQL test suite | 4-6 hrs |

---

## APPENDIX: File Inventory

### Route Modules (25 total)
Enabled: auth, students, llm, features, decisions, recommendations, advisor, business, integration, student_v1, faculty_v1, admin_v1, retention_v1, analytics, goals, reports, ml_routes, monitoring, interventions, audit, admin_ingest

Disabled (dead code): predictions, events, feedback

### Database Models (25+ total)
`student`, `user`, `enrollment`, `course`, `prediction`, `intervention`, `graded_component`, `exam_record`, `audit_log`, `risk_snapshot`, `engineered_features`, `intervention_log`, `goal`, `llm_query`, `llm_insight`, `revoked_token`, `ingestion_run`, `course_content_registry`, `canonical` tables, `prediction_log`

### Test Files (18 total)
See section 7.2 for detailed listing.

### Key Configuration
- FastAPI: 0.119.0
- SQLAlchemy: 2.0.45
- Pydantic: 2.12.5
- PyJWT: 2.12.0
- bcrypt: 5.0.0 (12 rounds)

---

*End of Audit Report*
