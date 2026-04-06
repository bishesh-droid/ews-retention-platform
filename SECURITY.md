# Security Audit and Remediation Guide

## Scope

This assessment covers current backend and frontend behavior, including auth, authorization, request handling, data export paths, and operational defaults.

## 1) Authentication Model Assessment

## Backend

- JWT bearer auth implemented in `backend/api/deps.py` and `backend/core/auth.py`.
- `get_current_user` validates token signature and resolves DB user.
- `require_role` enforces role membership with superuser bypass.

## Frontend

- `frontend/src/context/AuthContext.js` uses demo credentials and `sessionStorage` flag.
- No JWT capture, storage, or Authorization header attachment by default.
- Protected frontend routes do not guarantee backend authorization.

Security effect:

- User can be "logged in" in UI while backend rejects protected calls.
- Frontend auth state is not a secure representation of backend identity.

## 2) Critical and High Severity Findings

## 2.1 Role-check bug in goals ownership enforcement (high)

- Location: `backend/routes/goals.py`.
- Pattern: compares role against `"Student"` while role checks are normalized lowercase in deps.
- Impact: student self-only guard can be bypassed for lowercase `"student"` role values.
- Fix:
  - compare lowercase roles consistently.
  - enforce owner check unconditionally for non-privileged roles.

## 2.2 Login content-type conflict with request validation middleware (high)

- Locations:
  - `backend/middleware/request_validation.py`
  - `backend/routes/auth.py` login endpoint (`OAuth2PasswordRequestForm`).
- Pattern: middleware expects JSON body for POST/PUT/PATCH requests while OAuth2 login uses form encoding.
- Impact: valid login requests can be rejected with unsupported media type behavior.
- Fix:
  - exempt auth login path from JSON-only rule, or
  - support form content types for auth endpoints.

## 2.3 Interventions mutation endpoints missing role restrictions (high)

- Location: `backend/routes/interventions.py`.
- Pattern: endpoints require authentication but not role constraints.
- Impact: any authenticated account can create/patch interventions.
- Fix:
  - apply role gates for write operations.
  - add ownership/tenant checks as needed.

## 2.4 Risk score unit inconsistency affecting policy enforcement (high)

- Locations:
  - `backend/services/ml_service.py`
  - `backend/services/student_service.py`
  - decision/business route/service layers.
- Pattern: some logic operates in 0-100, persisted values are 0-1.
- Impact: threshold comparisons may be applied in wrong units, causing wrong intervention severity.
- Fix:
  - standardize stored and computed units.
  - add typed wrappers/tests for threshold operations.

## 3) Medium Severity Findings

## 3.1 In-memory rate limiter limitations

- Location: `backend/middleware/security_logging.py`.
- Pattern: local in-process map with no cross-worker coordination and weak eviction.
- Impact: ineffective under multi-process deployment; potential memory growth.
- Fix:
  - move rate limit state to Redis or gateway-level limiter.
  - add bounded eviction.

## 3.2 Report download path trust model

- Location: `backend/routes/reports.py`.
- Pattern: file streaming path sourced from DB metadata.
- Impact: if privileged audit records are tampered, arbitrary file exposure risk for privileged users.
- Fix:
  - constrain file serving to approved directory root.
  - validate and normalize paths before streaming.

## 3.3 Insecure default development secret

- Location: `backend/config/__init__.py`.
- Pattern: hardcoded fallback `SECRET_KEY` allowed outside production mode.
- Impact: accidental non-prod environments may run with known key.
- Fix:
  - fail-fast when secret is default in any shared/staging environment.
  - enforce secret checks in startup health tests.

## 4) Additional Observations

- `seed_dummy_data.py` may hash passwords with settings not aligned to active backend auth stack.
- Integration endpoints use static key auth (`X-Integration-Key`) without JWT; ensure key rotation and auditability.
- Duplicate frontend API clients increase accidental exposure/mis-handled auth headers.

## 5) Recommended Remediation Plan

## Phase A (immediate)

1. Fix goals role-case logic.
2. Fix login middleware content-type handling.
3. Add role restrictions to intervention writes.
4. Standardize score units for threshold checks.

## Phase B (short term)

1. Replace frontend demo auth with backend JWT flow.
2. Consolidate frontend API client codepaths.
3. Add endpoint-level authorization tests for sensitive resources.

## Phase C (hardening)

1. Externalize rate limiting to shared store.
2. Restrict report file serving root and sanitize all file paths.
3. Enforce non-default secret policy across environments.
4. Add security regression tests in CI.

## 6) Verification Checklist

- [ ] Login endpoint accepts valid OAuth2 form payload.
- [ ] Student users cannot access other students' goal records.
- [ ] Unauthorized roles cannot create/update interventions.
- [ ] Thresholds produce expected categories with consistent score units.
- [ ] Frontend attaches valid JWT to protected backend requests.
- [ ] Report download endpoint rejects out-of-root file paths.
- [ ] Rate limiting behaves consistently in multi-worker deployment.

## 7) Residual Risks Until Fixed

- Access control bypass risk in role/ownership edge paths.
- Policy mismatch risk due to score-unit conversions.
- Operational auth confusion due to frontend/backend divergence.
- Drift risk from stale/dead code paths that still compile/import in some contexts.
