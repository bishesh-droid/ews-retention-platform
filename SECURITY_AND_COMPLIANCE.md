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
