# Security & Compliance Architecture

## Overview

This document describes how all security and compliance features work together to protect sensitive student data and ensure FERPA compliance.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS (Defense in Depth)              │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 1: Perimeter                                                │
│  ├── Security Headers (HSTS, CSP, X-Frame-Options)                  │
│  └── Rate Limiting (SlowAPI + Redis)                               │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 2: Input Protection                                           │
│  ├── Input Sanitization (bleach.clean)                             │
│  ├── Encoding Bypass Protection (URL, Unicode, HTML entities)      │
│  └── Null Byte / Newline Stripping                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 3: Authentication & Authorization                             │
│  ├── JWT Authentication                                            │
│  ├── Role-Based Access Control (RBAC)                              │
│  └── Pydantic Validators (GPA, Attendance, Student ID regex)      │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 4: Data Protection                                            │
│  ├── PII Masking in Logs (emails, IDs, JWT tokens)                 │
│  ├── FERPA Audit Logging (who accessed what, when)                 │
│  └── Request ID Tracking (cross-log correlation)                   │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 5: Output Security                                            │
│  └── Security Headers on all responses                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Threat Model Overview

### Assets

| Asset | Sensitivity | Location | Protection Priority |
|-------|-------------|----------|-------------------|
| Student Educational Records (FERPA) | Critical | SQLite/PostgreSQL | Highest |
| Risk Scores and Predictions | Critical | predictions table | Highest |
| JWT Access Tokens | High | Redis, Client Memory | High |
| JWT Refresh Tokens | High | httpOnly Cookies | High |
| Audit Logs | High | audit_logs table | High |
| Intervention Records | High | interventions table | High |
| API Secrets (Gemini, Claude) | Critical | Environment Variables | Highest |
| Database Credentials | Critical | Environment Variables | Highest |

### Threat Actors

| Actor | Motivation | Capability | Primary Concern |
|-------|------------|------------|-----------------|
| External Attacker | Data theft, ransom | Low to High | FERPA data breach |
| Insider Misuse (faculty) | Curiosity, unauthorized access | Medium | Unauthorized student record access |
| Misconfigured Admin | Accidental exposure | High | Overly permissive RBAC, debug mode |
| LLM Provider Compromise | Data leakage | Low | Student data in prompts logged externally |
| Competitor Institution | Competitive intelligence | Medium | Risk algorithm theft |

### Attack Surfaces

| Surface | Risk Level | Attack Vectors | Mitigations |
|---------|------------|----------------|-------------|
| API Endpoints (/api/v1/*) | High | IDOR, injection, auth bypass | RBAC, input validation, audit logging |
| Authentication Endpoints | Critical | Brute force, token theft | Rate limiting, JWT claims, rotation |
| LLM Integration | Medium | Prompt injection, data leakage | Sanitization, hallucination guard |
| Data Ingestion Pipeline | High | Malicious file upload, injection | Validation, quarantine, row validators |
| Admin Endpoints | Critical | Privilege escalation | Strict RBAC, superuser checks |
| Audit Log Endpoints | Medium | Log tampering, unauthorized access | Write-once storage, admin-only access |

### High-Level Mitigations

```
Defense in Depth Layers:
├── Perimeter: Security headers, rate limiting, HTTPS
├── Authentication: JWT with short expiry, token rotation, revocation
├── Authorization: RBAC with resource ownership checks
├── Input: Pydantic validation, bleach sanitization, encoding detection
├── Data: PII masking, encryption at rest (AES-256), TLS 1.3
├── Monitoring: FERPA audit logging, anomaly detection
└── Response: Incident response plan, breach notification procedures
```

---

## Trust Boundaries

### Boundary Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              TRUST ZONES                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐        ┌──────────────────────────────────┐      │
│  │  UNTRUSTED       │        │         TRUSTED                  │      │
│  │                  │        │                                  │      │
│  │  Browser/Client   │───────▶│  FastAPI Backend                 │      │
│  │  (React SPA)      │  HTTPS │  • JWT Validation                │      │
│  │  Port 3000       │        │  • RBAC Enforcement              │      │
│  │                  │        │  • Input Sanitization            │      │
│  └──────────────────┘        │  • Rate Limiting                 │      │
│                              │  Port 8000                       │      │
│                              └──────────┬─────────────────────┘      │
│                                         │                              │
│                                         ▼                              │
│                              ┌──────────────────┐                      │
│                              │   TRUSTED        │                      │
│                              │   Internal       │                      │
│                              │                  │                      │
│                         ┌───▶│  Redis Cache     │                      │
│                         │    │  Port 6379       │                      │
│                         │    │  • Rate counters │                      │
│                         │    │  • Token blocklist│                     │
│                         │    └──────────────────┘                      │
│                         │                                              │
│                         │    ┌──────────────────┐                      │
│                         │    │   TRUSTED        │                      │
│                         │    │   Internal       │                      │
│                         └───▶│                  │                      │
│                              │  SQLite/         │                      │
│                              │  PostgreSQL      │                      │
│                              │  • FERPA data    │                      │
│                              │  • Audit logs    │                      │
│                              │  • Predictions   │                      │
│                              └──────────────────┘                      │
│                                         │                              │
│                              ┌──────────┴──────────────────┐          │
│                              ▼                              ▼          │
│                    ┌──────────────────┐  ┌──────────────────┐         │
│                    │  UNTRUSTED       │  │  UNTRUSTED        │         │
│                    │  External        │  │  External         │         │
│                    │                  │  │                   │         │
│                    │  Google Gemini   │  │  Anthropic Claude │         │
│                    │  API             │  │  API              │         │
│                    │  (via HTTPS)     │  │  (via HTTPS)      │         │
│                    └──────────────────┘  └──────────────────┘         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Boundary Descriptions

**Browser <-> Backend**
- Authentication: JWT Bearer tokens
- Transport: HTTPS with TLS 1.3 (production)
- Trust Level: Untrusted to Trusted
- Controls: Security headers, CORS, rate limiting, JWT validation

**Backend <-> Redis**
- Authentication: Redis AUTH password
- Transport: Internal network (Docker) or TLS (production)
- Trust Level: Trusted to Trusted
- Controls: Redis ACLs, network segmentation

**Backend <-> Database**
- Authentication: Database credentials (env vars)
- Transport: Internal network (Docker) or TLS (production)
- Trust Level: Trusted to Trusted
- Controls: Connection pooling, parameterized queries (SQL injection prevention), least privilege user

**Backend <-> External LLM Providers**
- Authentication: API keys (env vars)
- Transport: HTTPS with certificate pinning
- Trust Level: Trusted to Untrusted
- Controls: Prompt sanitization, PII masking before sending, rate limiting, response validation (hallucination guard)

---

## Authentication & Token Lifecycle Deep Dive

### JWT Claims

Access token claims structure:

```json
{
  "sub": "user@example.com",
  "role": "faculty",
  "exp": 1713123456,
  "iat": 1713119856,
  "iss": "ews-retention-platform",
  "aud": "ews-api",
  "jti": "unique-token-id-uuid",
  "nbf": 1713119856
}
```

| Claim | Purpose | Validation |
|-------|---------|------------|
| sub | Subject (user identifier) | Must match database user |
| role | RBAC role | Must be valid enum value |
| exp | Expiration timestamp | Must be in future |
| iat | Issued at timestamp | Used for rotation detection |
| iss | Issuer | Must match platform identifier |
| aud | Audience | Must match API identifier |
| jti | JWT ID (unique) | Checked against revocation blocklist |
| nbf | Not before timestamp | Must be in past |

### Token Rotation

```
Initial Login:
┌──────────┐                    ┌──────────┐
│  Client  │ ──── Login ─────▶│ Backend  │
│          │◀── Access Token ─│          │
│          │◀── Refresh Token──│ (httpOnly│
│          │    (cookie)      │ cookie)  │
└──────────┘                    └──────────┘

Token Refresh (on 401):
┌──────────┐                    ┌──────────┐
│  Client  │ ──── /refresh ──▶│ Backend  │
│          │    (cookie auto) │          │
│          │◀── New Access ───│          │
│          │◀── New Refresh ──│ (old     │
│          │    (cookie)      │ revoked) │
└──────────┘                    └──────────┘
```

Rotation benefits:
- Limits window of compromise
- Forces attacker to maintain persistent access
- Enables detection of token theft via concurrent usage patterns

### Revocation Handling

**RevokedToken Model:**

```python
class RevokedToken(Base):
    jti: str  # JWT ID (unique per token)
    expires_at: datetime  # For automatic cleanup
    revoked_at: datetime
    reason: str  # logout, suspicious_activity, admin_action
```

**Revocation Scenarios:**

| Scenario | Action | Token Status |
|----------|--------|--------------|
| User logout | Add to blocklist | Revoked immediately |
| Password change | Revoke all tokens | All existing revoked |
| Suspicious activity | Revoke specific token | Single token revoked |
| Admin action | Revoke user's tokens | All user tokens revoked |
| Scheduled cleanup | Delete expired entries | Cleanup job runs daily |

**Cleanup Job:** `backend/services/infrastructure/token_cleanup.py`
- Runs via APScheduler
- Removes blocklist entries for expired tokens
- Reduces database bloat

### Refresh Flow

```
1. Client stores access token in memory (never localStorage)
2. Client receives refresh token in httpOnly, Secure, SameSite=Strict cookie
3. On 401 response, client calls POST /auth/refresh
4. Server validates refresh token (signature, expiration, not revoked)
5. Server issues new access token + new refresh token
6. Old refresh token added to revocation blocklist
7. New refresh token sent in Set-Cookie header
```

### Expiration Enforcement

| Token Type | Lifetime | Storage | Refreshable |
|------------|----------|---------|-------------|
| Access Token | 15-60 minutes | Client memory | Yes (via refresh) |
| Refresh Token | 7 days | httpOnly cookie | No (rotation only) |

**Expiration Handling:**
- Server rejects expired tokens with HTTP 401
- Client must request token refresh
- If refresh token expired, full re-authentication required

---

## Role-Based Access Control Matrix

### Permission Matrix

| Permission | student | faculty | retention_team | admin | superuser |
|------------|:-------:|:-------:|:--------------:|:-----:|:---------:|
| Read own student data | ✅ | N/A | N/A | N/A | ✅ |
| Read all student data | ❌ | ✅ | ✅ | ✅ | ✅ |
| Modify own profile | ✅ | ❌ | ❌ | ❌ | ✅ |
| Create intervention | ❌ | ✅ | ✅ | ✅ | ✅ |
| Modify intervention | ❌ | ✅ | ✅ | ✅ | ✅ |
| Access audit logs | ❌ | ❌ | ❌ | ✅ | ✅ |
| Trigger data ingestion | ❌ | ❌ | ❌ | ✅ | ✅ |
| Access analytics | ❌ | ✅ | ✅ | ✅ | ✅ |
| Modify risk scores | ❌ | ❌ | ❌ | ❌ | ✅ |
| User management | ❌ | ❌ | ❌ | ✅ | ✅ |
| System configuration | ❌ | ❌ | Limited | ✅ | ✅ |
| Revoke tokens | ❌ | ❌ | ❌ | ✅ | ✅ |
| Access LLM features | ✅ | ✅ | ✅ | ✅ | ✅ |

### Role Descriptions

**student**
- Can view own risk scores and predictions
- Can update personal goals
- Cannot view other students' data
- Rate limited to standard user limits

**faculty**
- Can view all student data within scope
- Can create and manage interventions
- Cannot access audit logs or system configuration
- Cannot modify risk scores directly

**retention_team**
- Full access to student data and analytics
- Can manage intervention queues
- Limited system configuration access
- Cannot access audit logs or user management

**admin**
- Full system access except superuser bypass
- Can manage users and roles
- Can trigger data ingestion
- Can access audit logs for compliance
- Cannot directly modify risk scores (enforced by algorithm)

**superuser**
- Bypasses all RBAC checks when `is_superuser=True`
- Emergency access for critical situations
- All actions logged with elevated priority
- Should be limited to 1-2 individuals

### Implementation

```python
# Route-level protection
@router.get("/api/v1/admin/audit-log")
@require_role(["admin", "superuser"])
def get_audit_logs(...):
    ...

# Resource-level protection
@router.get("/api/v1/students/{student_id}")
@require_role(["faculty", "admin", "superuser"])
def get_student(student_id: str, current_user: User = Depends(get_current_user)):
    # Additional ownership check for students
    if current_user.role == "student" and current_user.email != student_id:
        raise HTTPException(403, "Cannot access other students' data")
    ...
```

---

## Data Retention & Deletion Policy

### Audit Log Retention

| Log Type | Retention Period | Rationale |
|----------|------------------|-----------|
| FERPA Audit Logs | 7 years | Federal compliance requirement |
| Security Events | 7 years | Incident investigation |
| Rate Limit Events | 90 days | Abuse pattern analysis |
| Error Logs | 90 days | Debugging and monitoring |
| Application Logs | 30 days | Operational monitoring |

**Implementation:**
- Automated purge job via scheduler
- Archive to cold storage before deletion (optional)
- Immutable logs (tamper-evident)

### Prediction Retention

| Prediction Type | Retention | Notes |
|-----------------|-----------|-------|
| Current predictions | Indefinite | Until superseded by newer prediction |
| Historical snapshots | 2 years | Risk trend analysis |
| Archived predictions | 5 years | Long-term retention for compliance |

**Snapshot Table:** `risk_snapshots`
- Captures point-in-time risk scores
- Enables historical trend analysis
- Purged after retention period

### GDPR-Style Deletion (Right to Erasure)

**Student Data Deletion Workflow:**

1. **Request Validation:**
   - Verify requester identity
   - Confirm no pending interventions
   - Check legal hold requirements

2. **Data Anonymization (Preferred):**
   - Replace PII with hash codes
   - Maintain aggregate analytics
   - Preserve audit trail (with anonymized references)

3. **Full Deletion (If Required):**
   - Delete student record from `students` table
   - Delete associated predictions
   - Delete intervention records
   - Retain audit logs with anonymized references
   - Update foreign keys to NULL or placeholder

4. **Verification:**
   - Confirm deletion in database
   - Check cache invalidation
   - Log deletion in audit trail

### Token Cleanup Jobs

**Revoked Token Cleanup:**
- Frequency: Daily at 02:00 UTC
- Action: Delete expired tokens from `revoked_tokens` table
- Retention: Tokens expired > 30 days removed

**Stale Session Cleanup:**
- Frequency: Weekly
- Action: Identify and purge orphaned refresh tokens
- Threshold: No activity for 30 days

---

## Scheduler & Background Job Security

### APScheduler Configuration

**Scheduler File:** `backend/services/infrastructure/scheduler.py`

```python
scheduler = AsyncIOScheduler(
    jobstores={'default': SQLAlchemyJobStore(url=DATABASE_URL)},
    executors={'default': ThreadPoolExecutor(max_workers=1)},
    job_defaults={'coalesce': True, 'max_instances': 1}
)
```

### Scheduled Jobs

| Job | Frequency | Function | Security Considerations |
|-----|-----------|----------|------------------------|
| Daily Prediction Generation | 03:00 UTC | `generate_daily_predictions()` | Async lock prevents overlapping runs |
| Weekly Model Retraining | Sunday 02:00 UTC | `retrain_models()` | Requires exclusive database access |
| Token Cleanup | Daily 02:00 UTC | `cleanup_revoked_tokens()` | Removes expired tokens |
| Audit Log Archive | Monthly 1st | `archive_audit_logs()` | Moves old logs to cold storage |
| GDPR Data Purge | Daily 01:00 UTC | `purge_expired_data()` | Handles retention policy enforcement |

### Locking Mechanism

**Async Lock Implementation:**

```python
# Prevents overlapping job execution in single-instance deployments
_prediction_job_lock = asyncio.Lock()

async def generate_daily_predictions():
    if _prediction_job_lock.locked():
        logger.warning("Prediction job already running, skipping")
        return
    
    async with _prediction_job_lock:
        # Process all students
        for student in students:
            await calculate_risk_score(student)
```

**Current Limitation:**
- Single-instance only (asyncio.Lock is process-local)
- Not suitable for multi-worker deployments

### Risk of Overlapping Jobs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Duplicate predictions | Database bloat | Unique constraint on (student_id, date) |
| Resource contention | Slow performance | Async lock prevents concurrent execution |
| Race conditions | Data inconsistency | Transaction isolation (SERIALIZABLE for critical operations) |
| Memory exhaustion | Service crash | Batch processing with limited batch size |

### Recommended Distributed Lock for Scaling

**Redis Distributed Lock:**

```python
# Production implementation for multi-worker deployments
import redis.asyncio as redis

async def distributed_prediction_job():
    redis_client = redis.from_url(REDIS_URL)
    lock = redis_client.lock("prediction_job_lock", timeout=3600)
    
    if await lock.acquire(blocking=False):
        try:
            await generate_daily_predictions()
        finally:
            await lock.release()
    else:
        logger.info("Distributed lock held by another worker, skipping")
```

**Benefits:**
- Works across multiple backend instances
- Automatic expiration prevents stuck locks
- Compatible with containerized deployments

---

## Compliance Mapping

### FERPA Principles Mapping

| FERPA Principle | Implementation | Status |
|-----------------|----------------|--------|
| Annual Notification | Institution responsible (external to platform) | N/A |
| Access to Educational Records | RBAC with resource ownership | ✅ Complete |
| Disclosure with Consent | Audit logging of all access | ✅ Complete |
| Disclosure without Consent (exceptions) | Admin override with audit trail | ✅ Complete |
| Record of Disclosures | `audit_logs` table with 7-year retention | ✅ Complete |
| Amendment of Records | Admin endpoints for record correction | ✅ Complete |
| Third-Party Disclosure | LLM integration with PII masking | ✅ Complete |
| Data Security | Defense in depth architecture | ✅ Complete |

### OWASP Top 10 Mitigations

| OWASP Risk | Mitigation | Implementation |
|------------|------------|----------------|
| A01: Broken Access Control | RBAC, resource ownership checks | `require_role` decorator, IDOR tests |
| A02: Cryptographic Failures | JWT with strong signing, HTTPS | `backend/core/auth.py`, TLS 1.3 |
| A03: Injection | SQL injection prevention, XSS protection | SQLAlchemy ORM, bleach sanitization |
| A04: Insecure Design | Defense in depth, least privilege | Layered security architecture |
| A05: Security Misconfiguration | Security headers, rate limiting | `SecurityHeadersMiddleware` |
| A06: Vulnerable Components | Dependency scanning (pip-audit) | CI/CD pipeline integration |
| A07: Auth Failures | JWT best practices, token rotation | Token lifecycle management |
| A08: Data Integrity Failures | Input validation, audit logging | Pydantic validators, `AuditLog` model |
| A09: Logging Failures | Structured logging, PII masking | `PIIMaskingFilter`, JSON logs |
| A10: SSRF | Limited external calls, URL validation | LLM endpoints only, strict URL validation |

### Defense in Depth Strategy

```
Layer 1: Perimeter Security
├── HTTPS/TLS 1.3 for all communications
├── Security headers (CSP, HSTS, X-Frame-Options)
├── Rate limiting (SlowAPI + Redis)
└── CORS restrictions

Layer 2: Authentication
├── JWT with short expiry (15-60 min)
├── Token rotation on refresh
├── Revocation blocklist
└── Multi-factor authentication (future)

Layer 3: Authorization
├── RBAC with role hierarchy
├── Resource ownership verification
├── Superuser override (logged)
└── API key authentication for integrations

Layer 4: Input Protection
├── Pydantic schema validation
├── Bleach HTML sanitization
├── Encoding bypass detection
├── Prompt injection filtering
└── File upload validation

Layer 5: Data Protection
├── PII masking in logs
├── AES-256 encryption at rest (PostgreSQL TDE)
├── TLS 1.3 in transit
├── Parameterized queries (SQL injection prevention)
└── Audit logging (all data access)

Layer 6: Monitoring & Response
├── FERPA-compliant audit trails
├── Anomaly detection (rate limiting events)
├── Security incident response plan
└── Automated security scanning (bandit, safety)
```

---

## Production Hardening Recommendations

### Database Migration: SQLite to PostgreSQL

**Current State:** SQLite (development)
**Target State:** PostgreSQL (production)

**Migration Steps:**
1. Deploy PostgreSQL with SSL/TLS enabled
2. Enable row-level security policies (optional)
3. Configure connection pooling (PgBouncer)
4. Enable query logging for audit purposes
5. Set up automated backups (point-in-time recovery)
6. Enable Transparent Data Encryption (TDE)

**Benefits:**
- Concurrent write support
- Role-based database permissions
- Better performance at scale
- Advanced audit features (pgAudit)

### Redis Cluster

**Current State:** Single Redis instance
**Target State:** Redis Cluster (production)

**Configuration:**
- 3 master nodes + 3 replica nodes
- Automatic failover
- Data partitioning across nodes
- Persistence (AOF + RDB)

**Benefits:**
- High availability (no single point of failure)
- Horizontal scaling for rate limiting
- Improved fault tolerance

### Distributed Locks

**Implementation:**
- Redis Redlock algorithm for critical sections
- Replace async locks with distributed locks
- Enable multi-worker backend deployments

**Affected Components:**
- Daily prediction generation
- Model training jobs
- Token cleanup jobs

### HTTPS Termination

**Current State:** Development (HTTP)
**Target State:** Production (HTTPS everywhere)

**Implementation:**
- Reverse proxy (nginx) with TLS 1.3
- HSTS headers (already implemented)
- Certificate management (Let's Encrypt or commercial)
- HTTP to HTTPS redirect

**Certificate Rotation:**
- Automated renewal (certbot)
- Zero-downtime rotation
- Certificate pinning for mobile clients

### Secret Rotation

**Rotation Schedule:**

| Secret Type | Rotation Frequency | Method |
|-------------|-------------------|--------|
| JWT Signing Key | 90 days | Gradual token expiration |
| Database Credentials | 90 days | Rolling update |
| Redis Password | 180 days | Rolling update |
| LLM API Keys | 180 days | Provider dashboard + env update |
| Integration API Keys | 90 days | Hash regeneration |

**Rotation Process:**
1. Generate new secret
2. Deploy to environment (rolling update)
3. Update consuming services
4. Revoke old secret after grace period
5. Verify no service disruption

### Infrastructure Monitoring

**Monitoring Stack:**

| Component | Tool | Metrics |
|-----------|------|---------|
| Application | Prometheus + Grafana | Request latency, error rates, throughput |
| Database | PostgreSQL exporter | Query performance, connection pool, locks |
| Cache | Redis exporter | Memory usage, hit rate, evictions |
| Security | WAF logs + SIEM | Blocked requests, suspicious patterns |
| Audit | ELK Stack | Audit log aggregation, compliance dashboards |

**Alerting Rules:**
- Failed authentication rate > 10/min
- Rate limit hits > 100/min
- Database connection pool exhaustion
- 5xx error rate > 1%
- PII detected in application logs

---

## 1. Security Headers Middleware

**File**: `backend/middleware/security_headers.py`

### What it does:
Adds security headers to every HTTP response to prevent common web attacks.

### Headers Added:
| Header | Value | Protection |
|--------|-------|------------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Forces HTTPS, prevents downgrade attacks |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME sniffing attacks |
| `X-Frame-Options` | `DENY` | Prevents clickjacking |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS protection |
| `Content-Security-Policy` | `default-src 'self'...` | Prevents XSS, data injection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limits referrer leakage |
| `Cache-Control` | `no-store, max-age=0` | Prevents sensitive data caching |

### Integration:
```python
# In backend/main.py
app.add_middleware(SecurityHeadersMiddleware)  # Added early in stack
```

### Testing:
```bash
curl -I http://localhost:8000/
# Check all security headers are present
```

---

## 2. Input Sanitization & Injection Prevention

**File**: `backend/core/security.py`

### What it does:
Multi-layer input sanitization to prevent injection attacks.

### Protection Layers:

#### Layer 1: Encoding Detection & Decoding
```python
# Handles encoding bypass attempts:
# - URL encoding: %3Cscript%3E → <script>
# - Unicode: \u003cscript\u003e → <script>
# - HTML entities: &lt;script&gt; → <script>
# - Double encoding: %253C → %3C → <
```

#### Layer 2: Bleach-based HTML Sanitization
```python
# Replaces regex-based sanitization with bleach.clean()
sanitized = bleach.clean(
    text,
    tags=[],           # No HTML tags allowed
    attributes={},    # No attributes allowed
    styles=[],        # No CSS allowed
    protocols=[],     # No URL protocols
    strip=True        # Strip disallowed tags
)
```

#### Layer 3: Control Character Stripping
```python
# Strip null bytes and newlines to prevent:
# - Null byte injection attacks
# - Newline-based injection (header injection)
text = text.replace('\x00', '')
text = text.replace('\r', '').replace('\n', '')
```

#### Layer 4: Prompt Injection Detection
```python
# Detects and removes prompt injection patterns:
# - "ignore previous instructions"
# - "system:" role manipulation
# - Delimiter injection (```, ---, <system>)
# - Jailbreak attempts (DAN, Developer Mode)
```

### Usage in Code:
```python
from backend.core.security import SecurityManager

# For general input
safe_input = SecurityManager.sanitize_input(user_input)

# For LLM inputs (enhanced protection)
llm_safe = SecurityManager.llm_sanitize(user_prompt)

# For student names
safe_name = SecurityManager.sanitize_student_name(raw_name)
```

### Testing:
```bash
# Run encoding bypass tests
pytest backend/tests/test_encoding_bypasses.py -v
```

---

## 3. PII Masking in Logs

**File**: `backend/core/logger.py`

### What it does:
Automatically masks sensitive data in all backend logs to prevent data leakage.

### Masked Patterns:
| Pattern | Example Input | Masked Output |
|---------|---------------|---------------|
| Email addresses | `student@example.com` | `stu***@ex***.com` |
| Student IDs | `STU123456789` | `STU***789` |
| JWT Tokens | `eyJ0eXAiOiJKV1Qi...` | `[REDACTED_JWT]` |
| Phone numbers | `+1-555-123-4567` | `[REDACTED_PHONE]` |

### Integration:
```python
# Applied to all log handlers automatically
handler.addFilter(PIIMaskingFilter())  # In setup_logger()
```

### Example Log Output:
```
# Before masking:
User stu***@ex***.com with ID STU***789 logged in with token eyJ0eX...

# After masking:
User stu***@ex***.com with ID STU***789 logged in with token [REDACTED_JWT]
```

---

## 4. FERPA-Compliant Audit Logging

**Files**:
- `backend/core/audit_logger.py` (helper functions)
- `backend/routes/audit.py` (admin endpoints)
- `backend/database/models/audit.py` (model)

### What it does:
Tracks every access to student educational records for FERPA compliance.

### Audit Log Schema:
```python
class AuditLog(Base):
    id                    # Primary key
    user_id               # Who accessed
    user_role             # Their role (faculty/admin/etc)
    action                # READ/WRITE/DELETE
    resource_type         # student/enrollment/grade/etc
    resource_id           # Which specific record
    ip_address            # Where from
    request_id            # For cross-log correlation
    timestamp             # When
    details               # Additional context (JSON)
```

### Usage in Routes:
```python
from backend.core.audit_logger import log_data_access, log_bulk_data_access

# Individual student access
log_data_access(
    db=db,
    user=current_user,
    action="READ",
    resource_type="student",
    resource_id=student_id,
    request=request  # Auto-extracts IP and request_id
)

# Bulk access (student list)
student_ids = [s["id"] for s in students]
log_bulk_data_access(
    db=db,
    user=current_user,
    action="READ",
    resource_type="student",
    resource_ids=student_ids,
    request=request
)
```

### Admin Endpoints:
```
GET /api/v1/audit-log              # Paginated logs with filters
GET /api/v1/audit-log/summary       # Compliance reporting stats
GET /api/v1/audit-log/student/{id}  # Per-student audit trail
```

### Filter Options:
- `user_id` - Filter by specific user
- `action` - READ, WRITE, DELETE
- `resource_type` - student, enrollment, grade, etc.
- `resource_id` - Specific record
- `start_date` / `end_date` - Date range

### Testing:
```bash
# View audit logs (admin only)
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://localhost:8000/api/v1/audit-log?action=READ&limit=10"
```

---

## 5. Rate Limiting

**Files**:
- `backend/core/rate_limiting.py`
- Applied to all LLM endpoints via `require_llm_rate_limit`

### What it does:
Prevents abuse and ensures fair resource usage.

### Rate Limits:
| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Login | 5 | per minute |
| Data Ingestion | 10 | per hour |
| LLM (per user) | 5 | per minute |
| LLM (per user) | 20 | per hour |
| Default | 200 | per minute |

### Implementation:
```python
# Per-user rate limiting with Redis
# Key format: llm_ratelimit:{user_id}:{window}

@app.get("/api/v1/llm/risk-explanation")
@require_llm_rate_limit  # Applies 5/min + 20/hour limits
def get_risk_explanation(...):
    ...
```

### Response on Limit Hit:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1712345678
```

---

## 6. Pydantic Validators (Strict Input Validation)

**Files**:
- `backend/schemas/common.py`
- `backend/schemas/student.py`
- `backend/schemas/prediction.py`

### What it does:
Strict field validation prevents invalid/malicious data at the schema level.

### Validators:
```python
# GPA: strictly 0.0 - 4.0
GPA_FIELD = Field(ge=0.0, le=4.0)

# Attendance: strictly 0 - 100
ATTENDANCE_FIELD = Field(ge=0, le=100)

# Student ID: alphanumeric, 4-20 chars
STUDENT_ID_FIELD = Field(
    pattern=r'^[A-Za-z0-9_-]{4,20}$',
    min_length=4,
    max_length=20
)
```

### Usage:
```python
from backend.schemas.common import STUDENT_ID_FIELD, GPA_FIELD

class StudentBase(BaseModel):
    id: str = STUDENT_ID_FIELD  # Prevents injection in ID field
    
class PredictionBase(BaseModel):
    risk_score: float = Field(ge=0.0, le=100.0)
    attendance: float = ATTENDANCE_FIELD
```

---

## 7. Feature Engineering Refactoring (Security by Design)

**Files**: `backend/services/features/*.py`

### What it does:
Separated monolithic feature extractor into domain-specific classes for better maintainability and security.

### Structure:
```
backend/services/features/
├── academic.py       # AcademicFeatureExtractor + AcademicFeatures
├── engagement.py     # EngagementFeatureExtractor + EngagementFeatures
├── consistency.py    # ConsistencyFeatureExtractor + ConsistencyFeatures
├── intent.py         # IntentFeatureExtractor + IntentFeatures
├── composer.py       # FeatureEngineer (orchestrates all 4)
└── __init__.py       # Clean exports
```

### Security Benefits:
- **Typed dataclasses** instead of untyped dicts
- **Single Responsibility** - each extractor handles one domain
- **Testable** - each extractor has dedicated test file
- **Auditable** - clear data flow for FERPA compliance

---

## How It All Works Together

### Example: Student Data Access Flow

```
1. User requests: GET /api/v1/students/STU123
   ↓
2. Security Headers Middleware
   - Adds HSTS, CSP, X-Frame-Options to response (future response)
   ↓
3. Rate Limiting Check
   - Verifies user hasn't exceeded 200 req/min
   ↓
4. JWT Authentication
   - Validates token, extracts user_id and role
   ↓
5. RBAC Authorization
   - Verifies user has 'faculty', 'admin', or 'retention team' role
   ↓
6. Request Validation
   - Student ID validated against regex: ^[A-Za-z0-9_-]{4,20}$
   ↓
7. Database Query
   - Fetch student data
   ↓
8. FERPA Audit Logging
   - log_data_access(db, user, "READ", "student", "STU123", request)
   - Records: user_id, role, IP, timestamp, request_id
   ↓
9. PII Masking (if logging data)
   - Email "student@example.com" → "stu***@ex***.com"
   - ID "STU123456" → "STU***456"
   ↓
10. Security Headers on Response
    - Adds all 6 security headers to HTTP response
    ↓
11. User receives data + protected response
```

---

## Testing the Security Stack

### Run All Security Tests:
```bash
# Encoding bypass protection
pytest backend/tests/test_encoding_bypasses.py -v

# Security headers
pytest backend/tests/test_security_headers.py -v

# All tests
pytest backend/tests -v --tb=short
```

### Manual Verification:
```bash
# 1. Check security headers
curl -I http://localhost:8000/

# 2. Test rate limiting (exceed 5 req/min to login)
for i in {1..6}; do curl http://localhost:8000/api/v1/auth/login; done

# 3. Verify PII masking in logs
tail -f backend/backend.log | grep -i "email\|student_id"

# 4. Check audit logs (as admin)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/audit-log?limit=5
```

---

## Compliance Checklist

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| **FERPA Access Logging** | `backend/core/audit_logger.py` + `AuditLog` model | ✅ Complete |
| **Data Encryption in Transit** | HSTS + HTTPS (HSTS headers ready) | ✅ Ready |
| **Input Validation** | Pydantic validators + bleach sanitization | ✅ Complete |
| **PII Protection** | `PIIMaskingFilter` in logger | ✅ Complete |
| **Access Controls** | JWT + RBAC (`require_role` dependency) | ✅ Complete |
| **Rate Limiting** | SlowAPI + Redis | ✅ Complete |
| **Security Headers** | `SecurityHeadersMiddleware` | ✅ Complete |
| **Audit Trail Review** | Admin endpoints for audit log queries | ✅ Complete |

---

## Security Incident Response

### If You Suspect a Breach:

1. **Check Audit Logs**:
   ```bash
   curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     "http://localhost:8000/api/v1/audit-log/student/{student_id}?limit=100"
   ```

2. **Review Rate Limit Hits**:
   ```bash
   # Check Redis for blocked IPs
   redis-cli KEYS "ratelimit:*"
   ```

3. **Analyze Logs**:
   ```bash
   # Search for suspicious patterns
   grep "WARNING\|ERROR" backend/backend.log
   ```

4. **Contact Security Team**:
   - See `SECURITY.md` for contact information

---

## Summary

This platform implements **defense in depth** with multiple overlapping security layers:

1. **Perimeter**: Security headers, rate limiting
2. **Input**: Sanitization, validation, encoding detection
3. **Auth**: JWT, RBAC, strict validators
4. **Data**: PII masking, FERPA audit logging
5. **Output**: Security headers on all responses

All features are **tested**, **documented**, and **integrated** into the FastAPI middleware stack.
