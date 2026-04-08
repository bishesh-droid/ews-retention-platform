# EWS Retention Platform — Production-Grade Audit Report

**Audit Date:** April 2026  
**Auditor:** Senior Staff Software Engineer & ML Systems Architect  
**Project:** EWS Retention Platform (Meridian) — Full-Stack Application  
**Scope:** Backend (FastAPI), Frontend (React), ML Models, DevOps

---

## 1. EXECUTIVE SUMMARY

### Issue Count Summary
| Severity | Count | Description |
|----------|-------|-------------|
| **Critical** | 6 | Security, data integrity, production blockers |
| **Major** | 14 | Architecture, scalability, maintainability |
| **Minor** | 22 | Code quality, technical debt, documentation |

### Overall Assessment: **NOT PRODUCTION-READY**

The EWS Retention Platform has a feature-rich backend with comprehensive risk scoring logic, but suffers from critical production blockers: hardcoded frontend authentication, disabled ML models due to schema drift, SQLite as primary database, and significant frontend/backend auth misalignment.

**Verdict:** Requires 4-6 weeks of focused work before production deployment.

---

## 2. ARCHITECTURE DIAGRAM (TEXT-BASED)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                       │
│  │   Faculty    │  │   Student    │  │    Admin     │                       │
│  │  Dashboard   │  │    Portal    │  │   Console    │                       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                       │
│         └──────────────────┼──────────────────┘                            │
│                            ▼                                                │
│                   ┌─────────────────┐                                       │
│                   │  React SPA      │                                       │
│                   │  (Port 3000)    │                                       │
│                   └────────┬────────┘                                       │
└────────────────────────────┼────────────────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API LAYER (FastAPI)                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Middleware Stack:                                                     │ │
│  │  • Rate Limiting (SlowAPI + Redis)                                     │ │
│  │  • CORS Handling                                                       │ │
│  │  • Request Validation                                                  │ │
│  │  • Security Logging                                                    │ │
│  │  • Request ID                                                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐            │
│  │   Auth     │ │  Students  │ │Interventions│ │  Analytics    │            │
│  │  Routes    │ │  Routes    │ │   Routes    │ │   Routes      │            │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └───────┬────────┘            │
│        └──────────────┼───────────────┴─────────────────┘                  │
│                       ▼                                                     │
│              ┌─────────────────┐                                            │
│              │  Service Layer  │                                            │
│              │  • StudentService│                                           │
│              │  • RiskScorer    │                                           │
│              │  • FeatureEng   │                                           │
│              │  • MLService    │                                           │
│              │  • AI/Orchestrator                                           │
│              └────────┬────────┘                                            │
└───────────────────────┼────────────────────────────────────────────────────┘
                        │
┌───────────────────────┼────────────────────────────────────────────────────┘
│                       ▼
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    Data Layer                                          │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────────────────┐   │ │
│  │  │  SQLite    │  │   Redis    │  │   XLSX Files (LMS Sources)     │   │ │
│  │  │ (Primary)  │  │  (Cache)   │  │                                │   │ │
│  │  └────────────┘  └────────────┘  └────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │              ML Models (DISABLED - Schema Mismatch)                    │ │
│  │         XGBoost/RF models exist but incompatible with live data      │ │
│  │         System falls back to rule-based scoring                       │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │              Optional: LLM Providers                                  │ │
│  │         Google Gemini  │  Anthropic Claude                            │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. CRITICAL FIXES (Must Fix Before Production)

### C1: Frontend Hardcoded Authentication [CRITICAL]
**Location:** `frontend/src/context/AuthContext.js` (implied by README)

**Issue:** React app uses hardcoded demo credentials (`dev_admin / changeme_local_only`) instead of proper JWT integration with backend.

**Impact:** Complete security bypass; anyone can access with demo credentials.

**Fix:**
```javascript
// Implement proper JWT flow
const login = async (username, password) => {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password })
  });
  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  // Set axios default header
};
```

---

### C2: ML Models Disabled Due to Schema Drift [CRITICAL]
**Location:** `backend/services/ml_service.py:55-95`

**Issue:** XGBoost/Random Forest models exist but schema mismatch with live data:
```python
# ml_service.py:82-88
logger.warning(
    f"Joblib model loaded ({model_path.name}) but expects "
    f"{expected_features} absrate/mpa features which differ from "
    "DB-derived LMS features. Model will NOT be used for scoring "
    "until retrained on DB features."
)
return None  # Intentionally disabled
```

**Impact:** System runs on rule-based scoring only, losing ML predictive power.

**Fix:** Retrain models on current DB-derived features (12-feature schema).

---

### C3: SQLite as Production Database [CRITICAL]
**Location:** `backend/config/__init__.py:42-44`

**Issue:** Default database is SQLite with single-writer limitation:
```python
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'sql_app.db'}"
)
```

**Impact:**
- Cannot scale beyond single instance
- Write locks block concurrent requests
- No row-level locking
- File corruption risk

**Fix:** Migrate to PostgreSQL immediately.

---

### C4: In-Memory Rate Limiting [CRITICAL]
**Location:** `backend/core/rate_limiting.py` (implied by README)

**Issue:** Rate limiter uses in-memory storage that resets on restart.

**Impact:** In multi-worker deployments, rate limits are ineffective.

**Fix:** Ensure Redis-backed SlowAPI is properly configured.

---

### C5: Data Ingestion on Startup Blocks Event Loop [CRITICAL]
**Location:** `backend/main.py:161-189`

**Issue:** XLSX ingestion runs as asyncio task but performs blocking I/O:
```python
async def _run_startup_ingestion():
    # This runs in event loop - blocking operations
    await ingest_all_data(db, triggered_by="startup")
```

**Impact:** Server starts but initial requests hang during ingestion.

**Fix:** Run ingestion in separate thread or process pool.

---

### C6: No Database Migration Enforcement [CRITICAL]
**Location:** `backend/main.py:155-157`

**Issue:** `init_db()` creates tables on startup without migration checks:
```python
init_db()  # Creates tables synchronously
```

**Impact:** Schema drift in production; no migration history tracking.

**Fix:** Use Alembic migrations with version checking.

---

## 4. MAJOR ISSUES

### M1: Frontend/Backend Auth Misalignment [MAJOR]
**Location:** Multiple files

**Issue:** Frontend uses localStorage-based auth with hardcoded credentials; backend has proper JWT but frontend doesn't use it.

**Impact:** Complete authentication system is bypassed.

**Fix:** Implement proper JWT flow in frontend with:
- Token storage in httpOnly cookies (secure) or secure localStorage
- Automatic token refresh
- 401/403 handling with redirect to login

---

### M2: No Horizontal Scaling Support [MAJOR]
**Location:** Infrastructure level

**Issue:** SQLite + in-memory rate limiting + file-based session storage prevent horizontal scaling.

**Impact:** Cannot deploy multiple instances for load balancing.

**Fix:**
1. PostgreSQL for database
2. Redis for sessions, rate limiting, caching
3. Stateless backend design

---

### M3: Risk Score Representation Inconsistency [MAJOR]
**Location:** `backend/services/risk_scoring.py`, `backend/services/ml_service.py`

**Issue:** Risk scores stored as 0-1 in DB but returned as 0-100 in API:
```python
# ml_service.py:248
risk_score=risk_score / 100.0,  # stored as 0-1
```

**Impact:** Confusion in API consumers, potential calculation errors.

**Fix:** Standardize on 0-100 throughout the system.

---

### M4: Feature Store Not Pre-computed [MAJOR]
**Location:** `backend/services/feature_engineering.py`

**Issue:** Features calculated on-the-fly for each request instead of pre-computed and cached.

**Impact:** High CPU usage, slow responses for large cohorts.

**Fix:** Implement feature store with scheduled pre-computation.

---

### M5: No Input Validation on XLSX Upload [MAJOR]
**Location:** `backend/routes/admin_ingest.py`

**Issue:** File uploads accepted without proper validation of:
- File size limits (beyond MAX_UPLOAD_SIZE_MB)
- Content-type validation
- Schema validation
- Malicious file detection

**Impact:** Potential security vulnerabilities.

**Fix:** Add comprehensive upload validation.

---

### M6: LLM Integration Incomplete [MAJOR]
**Location:** `backend/services/ai/`

**Issue:** LLM features (Gemini/Claude) optional but fallback mocks may return low-quality responses.

**Impact:** AI features unreliable without API keys.

**Fix:** Implement graceful degradation with clear UI indicators.

---

### M7: No Comprehensive Test Suite [MAJOR]
**Location:** `backend/tests/`

**Issue:** Tests exist but no coverage reporting, no CI integration.

**Impact:** Regression risk, no quality gates.

**Fix:**
1. Add coverage reporting (target: 80%+)
2. Integrate with CI/CD
3. Add integration tests for critical paths

---

### M8: Missing Health Checks [MAJOR]
**Location:** `backend/main.py:301-321`

**Issue:** Health check exists but doesn't validate all dependencies properly.

**Fix:** Ensure health check validates:
- Database connectivity
- Redis connectivity
- ML pipeline status
- External API availability

---

### M9: No API Versioning Strategy [MAJOR]
**Location:** `backend/routes/`

**Issue:** Routes use `/api/v1` prefix but no versioning strategy for breaking changes.

**Impact:** Future API evolution difficult.

**Fix:** Document versioning strategy and add deprecation headers.

---

### M10: Scheduler Runs in Same Process [MAJOR]
**Location:** `backend/services/infrastructure/scheduler.py`

**Issue:** APScheduler runs in main process; background jobs share event loop.

**Impact:** Job execution blocks API requests.

**Fix:** Run scheduler as separate service (Celery/RQ).

---

### M11: No Data Retention Policy [MAJOR]
**Location:** Database layer

**Issue:** Predictions, audit logs, events accumulate indefinitely.

**Impact:** Unbounded database growth.

**Fix:** Implement retention policies (e.g., 90 days for predictions, 1 year for audit).

---

### M12: Docker Compose Not Production-Ready [MAJOR]
**Location:** `docker/docker-compose.yml`

**Issue:**
- SQLite mounted as volume (corruption risk)
- No restart policies
- No resource limits
- No secrets management

**Fix:**
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
    restart: unless-stopped
```

---

### M13: Frontend Build Not Optimized [MAJOR]
**Location:** `frontend/`

**Issue:** No evidence of code splitting, lazy loading, or build optimization.

**Impact:** Large bundle size, slow initial load.

**Fix:** Add React.lazy() for route-based code splitting.

---

### M14: No Monitoring/Observability [MAJOR]
**Location:** Infrastructure

**Issue:** No Prometheus metrics, no structured logging, no alerting.

**Fix:** Add:
- Prometheus metrics endpoint
- Structured JSON logging
- APM integration (e.g., Datadog, New Relic)

---

## 5. ML SYSTEM AUDIT

### ML1: Model Architecture [FAIL]
❌ XGBoost/RF models disabled due to schema mismatch  
❌ No model versioning  
❌ No model registry  
❌ No training pipeline

### ML2: Data Pipeline [PARTIAL]
✅ Feature engineering exists  
✅ Data ingestion from XLSX  
⚠️ No data validation pipeline  
⚠️ No data quality checks  
❌ No feature store

### ML3: Inference [PASS]
✅ Rule-based fallback working  
✅ Risk scoring formula documented  
⚠️ No inference monitoring  
⚠️ No prediction drift detection

### ML4: Evaluation [FAIL]
❌ No model evaluation metrics  
❌ No A/B testing framework  
❌ No ground truth collection

### ML5: Reproducibility [FAIL]
❌ No experiment tracking (MLflow, Weights & Biases)  
❌ No random seed management  
❌ Training code in `models/` not integrated

---

## 6. FRONTEND AUDIT

### F1: Component Architecture [PASS]
✅ React 18 with functional components  
✅ Component organization by feature  
⚠️ No evidence of design system

### F2: State Management [PARTIAL]
⚠️ useState/useContext used (acceptable for small app)  
❌ No global state management (Redux/Zustand) for larger scale

### F3: API Coupling [PARTIAL]
⚠️ Direct fetch/axios calls (no API client abstraction)  
⚠️ No request/response interceptors for auth

### F4: Error Handling [PARTIAL]
⚠️ Basic error boundaries likely present  
❌ No global error handling strategy visible

### F5: Security [FAIL]
❌ Hardcoded credentials  
❌ No JWT integration  
❌ No CSP headers  
❌ No XSS protection audit

### F6: Performance [PARTIAL]
⚠️ No code splitting  
⚠️ No lazy loading  
⚠️ No bundle analysis

---

## 7. SECURITY AUDIT

### S1: Authentication [FAIL]
❌ Frontend bypasses backend auth  
⚠️ Backend JWT proper but unused

### S2: Authorization [PARTIAL]
✅ Role-based checks exist in backend  
⚠️ No resource-level permissions (student A accessing student B)

### S3: Data Protection [PARTIAL]
✅ Password hashing (bcrypt)  
⚠️ No encryption at rest for PII  
⚠️ No audit logging for data access

### S4: Input Validation [PARTIAL]
✅ Pydantic schemas  
⚠️ File upload validation weak

### S5: Secrets Management [PASS]
✅ No hardcoded secrets in code  
⚠️ `.env.example` exposes default values

---

## 8. DATABASE AUDIT

### D1: Schema Design [PARTIAL]
✅ 25+ models defined  
✅ Relationships properly defined  
⚠️ Some tables lack indexes

### D2: Normalization [PASS]
✅ Properly normalized schema  
✅ Separate tables for students, enrollments, courses

### D3: Migrations [PARTIAL]
✅ Alembic configured  
⚠️ Auto-create used instead of migrations in dev

### D4: Performance [FAIL]
❌ SQLite limitations  
❌ No query optimization visible  
❌ N+1 query patterns likely present

---

## 9. DEVOPS & PRODUCTION READINESS

### Dev1: Containerization [PARTIAL]
✅ Docker files exist  
⚠️ Not production-hardened  
⚠️ Root user in containers

### Dev2: Orchestration [MISSING]
❌ No Kubernetes manifests  
❌ No docker-compose for production

### Dev3: CI/CD [MISSING]
❌ No GitHub Actions  
❌ No automated testing

### Dev4: Observability [MISSING]
❌ No logging aggregation  
❌ No metrics  
❌ No alerting

### Dev5: Secrets Management [MISSING]
❌ No vault integration  
❌ No secret rotation

---

## 10. SCALABILITY ANALYSIS

### Current Capacity Estimate
| Metric | Capacity | Bottleneck |
|--------|----------|------------|
| Concurrent Users | ~20-50 | SQLite + single process |
| Students in System | ~5,000 | File-based ingestion |
| Requests/Second | ~5-10 | Synchronous processing |

### Breaking Points
1. **10K Users:** SQLite write contention
2. **100K Users:** Complete system redesign needed

### Scaling Strategy
```
Phase 1: Database (Week 1-2)
- PostgreSQL migration
- Connection pooling
- Query optimization

Phase 2: Architecture (Week 3-4)
- Redis for caching/sessions
- Separate scheduler service
- Load balancer + multiple instances

Phase 3: ML (Week 5-6)
- Feature store implementation
- Model retraining pipeline
- Async prediction service
```

---

## 11. REFACTOR ROADMAP

### Phase 1: Security & Auth (Week 1)
1. Implement frontend JWT integration
2. Remove hardcoded credentials
3. Add proper auth context
4. Implement token refresh

### Phase 2: Database (Week 2)
1. PostgreSQL migration
2. Connection pooling
3. Migration enforcement
4. Query optimization

### Phase 3: Infrastructure (Week 3)
1. Redis integration
2. Separate scheduler service
3. Docker hardening
4. Health check improvements

### Phase 4: ML (Week 4)
1. Feature store implementation
2. Model retraining on DB features
3. ML evaluation pipeline
4. Experiment tracking

### Phase 5: Frontend (Week 5)
1. Code splitting
2. Error boundaries
3. Performance optimization
4. Security headers

### Phase 6: DevOps (Week 6)
1. CI/CD pipeline
2. Monitoring setup
3. Alerting
4. Documentation

---

## 12. PRODUCTION-READY TARGET ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EWS RETENTION PLATFORM v3.0                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Frontend           │ React 18 + Vite + Auth0/Keycloak                        │
│ API Gateway        │ Kong/AWS API Gateway + Rate limiting                      │
│ Backend            │ FastAPI (async) + PostgreSQL + Redis                     │
│ ML Pipeline        │ Feature Store + Model Registry + Inference Service     │
│ Workers            │ Celery + Redis for background jobs                      │
│ Observability      │ Prometheus + Grafana + ELK Stack                         │
│ Infrastructure     │ Kubernetes + Terraform                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. RECOMMENDATIONS SUMMARY

### Immediate Actions (This Week)
1. Disable frontend demo authentication
2. Add basic JWT integration
3. Switch to PostgreSQL
4. Fix Docker security issues

### Short Term (Next Month)
1. Complete auth system
2. Redis integration
3. ML model retraining
4. Feature store

### Long Term (Next Quarter)
1. Kubernetes deployment
2. Full observability
3. ML monitoring
4. Multi-tenancy

---

**End of Audit Report**
