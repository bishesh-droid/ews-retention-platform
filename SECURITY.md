# Security Policy — Meridian EWS Retention Platform

---

## Section 1: Supported Versions

| Version / Branch | Security Fixes |
|---|---|
| `main` branch (current) | Fully supported |
| `develop` branch | Patches applied before merge to `main` |
| Tagged release > 6 months old | Not supported — upgrade required |

If you are running a release older than 6 months, no security patches will be backported. Upgrade to the current `main` branch.

---

## Section 2: Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.** Public disclosure before a fix is available puts student FERPA-protected data at risk.

### Where to Report

Email: **[security@your-institution.edu]**
*(Replace this address with the institution's actual security contact before publishing.)*

### What to Include

- **Affected component** — file path and subsystem if known (e.g. `backend/routes/auth.py`, JWT refresh flow, LLM prompt pipeline)
- **Description** — what the vulnerability is and how it can be triggered
- **Attack scenario** — who can exploit it, under what conditions, and what they can access or do
- **Steps to reproduce** — include a proof of concept if you have one; theoretical reports without reproduction steps will be triaged at lower priority
- **Potential impact** — data exposure, privilege escalation, authentication bypass, audit log corruption, etc.
- **Suggested fix** — optional, but appreciated if you have one

### Response SLA

| Milestone | Target |
|---|---|
| Acknowledgement | Within 48 hours of receipt |
| Triage and severity assessment | Within 5 business days |
| Fix timeline communicated | Within 10 business days |
| Critical vulnerabilities (CVSS ≥ 9.0) | Patched within 72 hours of confirmation |

### Responsible Disclosure

We ask reporters to allow **90 days** from the date of report acknowledgement before public disclosure. If a fix is shipped sooner, we will notify you and you may disclose at that point.

Reporters will be credited by name in release notes unless they prefer to remain anonymous. Please state your preference in your initial report.

---

## Section 3: Security Architecture Summary

This section describes the security controls in place. Researchers should read this before triaging a potential issue.

### Authentication

- **JWT access tokens** with a 15-minute lifetime. Issued at login and refreshed via the refresh endpoint.
- **Refresh tokens** stored in an `httpOnly` cookie with a 7-day lifetime.
- **Refresh Token Rotation (RTR):** on every refresh call, the previous token's JTI is revoked. Reuse of a superseded refresh token triggers immediate family revocation.
- **Token revocation** is backed by Redis (TTL-based key store). SQLite provides a fallback revocation check if Redis is unreachable.
- Refresh cookie attributes: `Secure`, `SameSite=Strict`, `Path=/api/v1/auth/refresh`.

### Authorization

- Four roles: `student`, `faculty`, `retention_team`, `admin`.
- RBAC is enforced at the FastAPI dependency layer (`backend/api/deps.py`) — not in route handlers.
- Ownership checks are enforced on all student-scoped endpoints. A `student` role user cannot access records belonging to another student.

### Data Protection

- **FERPA audit log:** append-only log covering all PII access, role-based data access, and all AI-generated disclosures. Table: `AuditLog`. Do not truncate or modify this table.
- **PII masking:** student IDs and email addresses are masked at the logger level (`backend/core/logger.py`) before any log output is written. Raw PII does not appear in application logs.
- **Development environments** use only synthetic student fixtures. No real student records are used outside production.

### LLM Security

- Student free-text fields (names, notes, free-response inputs) are **never interpolated directly** into LLM prompt strings.
- All prompts are constructed from structured templates in `backend/services/ai/llm_orchestrator.py`.
- A hallucination guard validates LLM responses before they are surfaced to any user.
- All LLM-generated disclosures to students are written to the FERPA audit log.

### Network

- **Rate limiting** is Redis-backed and applied to all authentication and LLM endpoints (`backend/core/rate_limiting.py`). Falls back to in-process TTLCache on Redis unavailability.
- **CORS:** production configuration allows HTTPS origins only. Wildcards (`*`) are not permitted. Loopback origins are allowed only when `ENVIRONMENT != production`.
- **`X-Forwarded-For`** is trusted only from IPs listed in `TRUSTED_PROXY_IPS`. Requests from unlisted IPs use the direct connection address for audit logging.

---

## Section 4: Known Security Scope

### In Scope for Bug Reports

- Authentication and session management — JWT issuance, refresh token rotation, logout, token revocation
- Authorization bypass or IDOR — one authenticated user accessing or modifying another user's data
- FERPA data exposure — student PII leaking to a role that should not have access
- LLM prompt injection via student-controlled input reaching the LLM prompt pipeline
- SQL injection or ORM bypass against any endpoint
- CORS misconfiguration allowing cross-origin requests from unintended origins
- Secrets or credentials committed to version history (current or past)
- Rate limit bypass allowing unauthenticated or bulk abuse of auth or LLM endpoints
- Audit log tampering — any mechanism that allows modification or deletion of `AuditLog` records

### Out of Scope

- Theoretical vulnerabilities without a working proof of concept
- Security issues in third-party LLM providers (Google Gemini, Anthropic Claude) — report those directly to Google or Anthropic
- Denial of service via resource exhaustion that does not involve an authentication or authorization bypass
- Social engineering attacks against institution staff
- Security issues that are only reproducible in development mode with SQLite (production uses PostgreSQL)

---

## Section 5: Incident Response Runbook

### Compromised API Key (e.g. Committed to Git)

1. **Rotate the key immediately at the provider console — do this before anything else.**
   - Anthropic: https://console.anthropic.com/ → API Keys → Revoke and reissue
   - Google: https://console.cloud.google.com/ → APIs & Services → Credentials → Delete and create new

2. **Purge the key from git history.** The commit is not enough — the key is in history on every clone.
   ```bash
   git filter-repo --path .env --invert-paths
   git push --force --all
   ```

3. **Notify all repository collaborators** to delete their local clones and re-clone. Their local `.git` directories contain the exposed history.

4. **Audit provider usage logs** for the window between the commit timestamp and key rotation. Look for API calls from unfamiliar IPs, unusual usage spikes, or requests outside normal operating hours.

5. **Update `.gitignore`** to ensure `.env` and any new secret files are excluded. Run `detect-secrets scan > .secrets.baseline` to update the baseline.

6. **Document the incident** in the internal incident log: exposure start time (git commit timestamp), rotation time, audit findings, and any remediation actions taken.

---

### Suspected JWT Compromise (Stolen Access or Refresh Token)

1. **Force-logout the affected user.** If the user is identifiable, call the logout endpoint with admin credentials, or directly insert the token JTI into the Redis revocation store:
   ```bash
   redis-cli SETEX "jti:<jti-value>" <ttl-seconds> "1"
   ```
   Replace `<jti-value>` with the JTI claim from the suspected token and `<ttl-seconds>` with the remaining lifetime of that token.

2. **If the signing key itself is suspected to be compromised**, rotate the `SECRET_KEY` environment variable. Be aware: **this invalidates all active tokens for all users across the entire platform.** Coordinate with the team and plan for a brief authentication outage.

3. **Review the `AuditLog` table** for all actions by the affected `actor_id` during the suspected exposure window. Identify what data was accessed or modified.

4. **Check Redis** for unusual token revocation or issuance patterns that may indicate automated token reuse attempts.

---

### Student Data Exposure

1. **Identify the scope.** Query the `AuditLog` table for the affected student IDs, the `actor_id` that accessed them, and the timestamp range of the exposure. Do not modify or delete any audit log records.

2. **Notify the institution's FERPA compliance officer within 24 hours** of discovering the exposure. Provide the audit log excerpt documenting the access.

3. **Preserve all logs** for the exposure window — application logs, audit logs, and Redis access logs if available. Do not rotate or truncate them until the compliance review is complete.

4. **Contain the exposure.** If it is ongoing:
   - Disable the affected endpoint (`router.include_router` can be commented out and redeployed)
   - Or revoke the affected user account's tokens and lock the account

5. **Assess FERPA breach notification obligations.** Depending on the nature and scope of the exposure, affected students may need to be notified within a defined window. The compliance officer makes this determination — provide them with the complete audit record.

---

### Redis Unavailability (Rate Limiting and Token Revocation Degraded)

1. **The service will continue operating.** Rate limiting falls back to in-process TTLCache at reduced thresholds. Token revocation checks fall back to the SQLite revocation table.

2. **Understand the degraded security posture:**
   - In-process rate limiting is per-worker, not global — a multi-worker deployment will have proportionally higher effective limits than intended.
   - SQLite-based revocation checks are slower and may not reflect revocations issued to Redis-only during the outage window.

3. **Restore Redis as the immediate priority.** Check Redis logs, container status, and network connectivity. Do not treat prolonged Redis unavailability as acceptable.

4. **Monitor authentication logs** for unusual login frequency or token reuse patterns during the degraded window.

5. **After Redis is restored**, verify that the revocation store is consistent with recent logout events. Any revocations that occurred during the outage may need to be replayed into Redis from the SQLite fallback table.

---

## Section 6: Security Configuration Checklist

Use this table to verify deployment configuration before going to production or after any infrastructure change.

| Setting | Required Value | Risk if Wrong |
|---|---|---|
| `SECRET_KEY` | ≥ 32 cryptographically random bytes, never a default or placeholder | All JWT tokens can be forged by anyone who knows the default |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ≤ 15 | Stolen access tokens remain valid for an extended window |
| `ENVIRONMENT` | `production` in production deployments | CORS allows loopback origins; dev-only behaviors may be active |
| `CORS_ORIGINS` | Explicit HTTPS URLs only — no wildcards, no `http://` | Cross-origin attacks from arbitrary origins |
| `TRUSTED_PROXY_IPS` | Set to load balancer / reverse proxy IPs only | Client-supplied `X-Forwarded-For` headers trusted; audit logs contain attacker-controlled IP values |
| Refresh cookie `Path` | `/api/v1/auth/refresh` | Refresh token sent on every request to the API, widening the exposure window |
| Refresh cookie `SameSite` | `Strict` | CSRF attacks can trigger refresh token rotation on cross-site navigation |
| Redis | Running and reachable from the backend | Rate limiting and refresh token rotation operate in degraded fallback mode |
| `.env` in `.gitignore` | Present and effective | Credentials committed to version history on next `git add .` |

---

## Section 7: Dependency Security

**Python (backend)**

Dependencies are pinned in `requirements.txt`. Before each release:
```bash
pip-audit -r requirements.txt
# or
safety check -r requirements.txt
```
Do not merge a release if either tool reports a known CVE in a direct or transitive dependency without a documented exception.

**Node (frontend)**

```bash
npm audit
```
This runs in CI. A failing audit with high or critical severity vulnerabilities will block the build. Review `npm audit fix` output before applying — automatic fixes can introduce breaking changes.

**Docker**

The base Docker image in `docker/Dockerfile` is digest-pinned. Verify the digest has not changed on each rebuild. Do not use floating tags (`:latest`) in production images.

**Previously Addressed CVEs**

| Library | Issue | Resolution |
|---|---|---|
| `python-jose` | Multiple CVEs in JOSE/JWT handling | Migrated to `authlib` |

Maintain this table when addressing future CVEs so that auditors can verify the fix is in place.
