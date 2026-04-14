# Security Policy

## Supported Versions

This security policy applies to the following maintained branches:

| Branch | Status | Support Window | End of Life (EOL) |
|--------|--------|----------------|-------------------|
| `main` | Active Development | Current + 12 months from last commit | 12 months after last release |
| `release/*` | Maintenance | Current release + 6 months | 6 months after next major release |
| `hotfix/*` | Security-only | Until merged to main | Immediate after merge |

### Maintenance Policy

**Active Development (`main`)**:
- Receives all security patches, bug fixes, and feature updates
- Monthly security patch releases on the first Tuesday of each month
- Emergency security patches released within 48 hours of Critical severity fixes

**Maintenance Branches (`release/*`)**:
- Receive only security patches and critical bug fixes
- Quarterly security patch releases
- No new features backported

**End of Life (EOL) Policy**:
- EOL branches receive no security updates
- Users must migrate to supported branches within 30 days of EOL announcement
- EOL announcements published 90 days in advance via project security mailing list

### Patch Cadence

| Patch Type | Frequency | Notification |
|------------|-----------|--------------|
| Scheduled Security | Monthly (first Tuesday) | security@<your-domain> |
| Critical Emergency | Within 48 hours | Immediate email + GitHub Security Advisory |
| High Priority | Within 1 week | GitHub Security Advisory |
| Bug Fix | Next scheduled release | Release notes |

---

## Reporting a Vulnerability

We take the security of the EWS Retention Platform seriously. This system handles sensitive student educational data protected under FERPA, and we appreciate your help in maintaining its security.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:

**security@<your-domain>**

Please include:
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact assessment
- Suggested fix (if any)
- CVSS score estimate (if known)
- Affected versions/branches

### Response Timeline

| Phase | Timeline | Deliverable |
|-------|----------|-------------|
| Acknowledgment | Within 48 hours | Confirmation email with case ID |
| Initial Assessment | Within 5 business days | Severity classification and response plan |
| Status Update | Every 7 days during investigation | Progress summary |
| Resolution | Based on severity (see Vulnerability Severity Matrix) | Patch or mitigation |
| Disclosure | Coordinated with reporter | Public advisory |

---

## Responsible Disclosure Policy

### Safe Harbor Statement

We support and encourage security research on our platform. Individuals conducting security testing in good faith and in compliance with this policy will not face legal action for:

- Accessing data that is not their own
- Using tools to identify vulnerabilities
- Testing security controls and mechanisms
- Circumventing technical protection measures for research purposes

### Non-Retaliation Policy

Researchers acting in good faith will not be subject to:
- Legal action for security research activities
- Account suspension or termination for vulnerability testing
- Claims for damages arising from good faith research

Good faith research requires:
- Avoiding harm to users, systems, or data
- Not exploiting vulnerabilities beyond minimal verification
- Not accessing data beyond what is necessary for validation
- Maintaining confidentiality until coordinated disclosure

### Coordinated Disclosure Process

1. **Report Submission**: Submit vulnerability report via security@<your-domain>
2. **Acknowledgment**: Security team confirms receipt within 48 hours
3. **Investigation**: Security team assesses and validates the finding
4. **Fix Development**: Development team creates and tests patch
5. **Embargo Period**: Coordinated waiting period before public disclosure
6. **Release**: Patch deployed and security advisory published
7. **Recognition**: Reporter acknowledged (with permission) in advisory

### Embargo Expectations

- Embargo period is typically 90 days from report acknowledgment
- May be extended by mutual agreement for complex vulnerabilities
- Early disclosure may occur if vulnerability is actively exploited in the wild
- Reporters agree not to disclose publicly before coordinated release
- Project commits to expedited patching for Critical and High severity issues

---

## Data Classification Model

All data within the EWS Retention Platform is classified into the following categories:

### Public

Data that can be freely shared with the public without risk to the organization.

Examples:
- Open source code (excluding configuration files with credentials)
- Published documentation and API specifications
- Public website content
- Marketing materials

Handling Requirements:
- No special handling required
- Standard copyright and licensing terms apply

### Internal

Data intended for use within the organization and authorized partners. Disclosure would cause minimal harm.

Examples:
- Internal documentation not containing student references
- System architecture diagrams (without sensitive implementation details)
- Non-sensitive configuration templates
- Staff contact information (non-student facing)

Handling Requirements:
- Store on authenticated systems only
- Do not post on public forums without review
- Mark as "Internal Use Only"

### Sensitive (FERPA)

Data protected under FERPA and other educational privacy laws. Disclosure could harm individuals or violate legal obligations.

Examples:
- Student educational records
- Risk scores and intervention data
- Academic performance metrics linked to identifiable students
- Enrollment and attendance records
- Audit logs containing student identifiers
- Email addresses associated with student records

Handling Requirements:
- Encryption at rest (AES-256) and in transit (TLS 1.3)
- Access restricted to authorized personnel with legitimate educational interest
- Audit logging required for all access
- Must not be included in code repositories, test data, or public issues
- Breach notification required within 72 hours of discovery

### Restricted

Data with the highest sensitivity. Unauthorized disclosure would cause severe harm to individuals or the organization.

Examples:
- System master encryption keys
- Database credentials and API secrets
- Authentication tokens and refresh tokens
- Raw PII before anonymization
- Security audit findings before remediation
- FERPA breach documentation

Handling Requirements:
- Access limited to Security Lead and designated administrators
- Multi-factor authentication required for access
- Separate secure storage (HSM or secure vault)
- Rotated immediately if compromise suspected
- Never committed to version control
- Never transmitted via unencrypted channels

---

## Vulnerability Severity Matrix (CVSS-aligned)

Vulnerabilities are classified using the Common Vulnerability Scoring System (CVSS) v3.1 framework.

### Critical (CVSS 9.0 - 10.0)

Immediate threat to the confidentiality, integrity, or availability of FERPA-protected data or core system functionality.

Examples:
- Unauthenticated remote code execution
- Direct FERPA data breach or mass extraction
- Authentication bypass allowing unauthorized FERPA access
- Privilege escalation to administrative access on production systems
- Cryptographic key compromise

Response Requirements:
- Acknowledgment: Within 4 hours
- Initial Assessment: Within 24 hours
- Patch Target: Within 48 hours
- Notification: Immediate notification to all users

### High (CVSS 7.0 - 8.9)

Significant security risk with potential for FERPA data exposure or serious system compromise.

Examples:
- SQL injection in authenticated endpoints
- Stored XSS leading to session hijacking
- IDOR allowing access to other users' FERPA data
- Broken authentication allowing credential compromise
- Insecure deserialization

Response Requirements:
- Acknowledgment: Within 48 hours
- Initial Assessment: Within 5 business days
- Patch Target: Within 1 week
- Notification: Security advisory published upon fix

### Medium (CVSS 4.0 - 6.9)

Moderate security risk with limited data exposure potential or partial system compromise.

Examples:
- Reflected XSS (non-persistent)
- CSRF on state-changing operations
- Information disclosure of non-FERPA internal data
- Rate limiting bypass with limited impact
- Missing security headers (CSP, HSTS)
- Weak input validation on non-sensitive endpoints

Response Requirements:
- Acknowledgment: Within 5 business days
- Initial Assessment: Within 10 business days
- Patch Target: Within 2 weeks
- Notification: Included in scheduled security release notes

### Low (CVSS 0.1 - 3.9)

Minor security issues with minimal practical impact on system security or data protection.

Examples:
- Verbose error messages revealing stack traces
- Missing best practice security headers with no direct exploit
- Self-XSS (attacker can only exploit their own account)
- SSL/TLS configuration weaknesses without direct exploit path
- Information disclosure of public information

Response Requirements:
- Acknowledgment: Within 10 business days
- Initial Assessment: Within 30 days
- Patch Target: Next scheduled release
- Notification: Bundled in routine release notes

---

## Security Controls Overview

The EWS Retention Platform implements defense-in-depth security through the following controls:

### JWT Authentication

- **Access Tokens**: Short-lived JWT tokens (15-60 minutes) with strong signing algorithms (HS256)
- **Refresh Tokens**: Long-lived tokens (7 days) stored in httpOnly, Secure, SameSite=Strict cookies
- **Token Revocation**: Blocklist table for revoked tokens with automatic cleanup
- **Claims Validation**: sub, role, exp, iat, iss, aud, jti, nbf claims validated on each request
- **Rotation**: Automatic token rotation on refresh to prevent replay attacks

### Role-Based Access Control (RBAC)

| Role | Student Data | User Management | System Config | Analytics |
|------|--------------|-----------------|---------------|-----------|
| student | Own data only | None | None | None |
| faculty | All students | None | None | Read-only |
| retention_team | All students | None | Limited | Full |
| admin | All students | Full | Full | Full |

- **Resource Ownership Checker**: Prevents IDOR attacks by verifying user-resource relationships
- **Superuser Override**: `is_superuser` flag for emergency access with audit logging
- **Role Hierarchy**: Well-defined role inheritance and permission boundaries

### Audit Logging

- **FERPA Compliance**: All student data access logged with user_id, action, resource_type, resource_id, timestamp, request_id, ip_address
- **Structured Format**: JSON-formatted logs with consistent schema
- **Retention**: Audit logs retained for 7 years per FERPA requirements
- **Tamper Resistance**: Write-once log storage with integrity verification
- **Query Interface**: Admin endpoint for authorized audit log queries

### PII Masking

All logs automatically mask sensitive data:

| Data Type | Example Input | Masked Output |
|-----------|---------------|---------------|
| Email | student@example.edu | stu***@ex***.edu |
| Student ID | 2025EB110001 | 2025***1001 |
| Phone Number | +1-555-123-4567 | [REDACTED_PHONE] |
| JWT Token | eyJhbG... | [REDACTED_JWT] |
| Password | (any value) | [REDACTED_PASSWORD] |

- **Masking Engine**: Regex-based and dictionary-based masking
- **Exceptions**: Raw values accessible only in debug mode (non-production)
- **Third-party**: PII masking applied before sending to external services

### Rate Limiting

| Endpoint | Limit | Window | Scope |
|----------|-------|--------|-------|
| Login | 5 | per minute | Per IP |
| Data Ingestion | 10 | per hour | Per user |
| LLM API | 5 | per minute | Per user |
| LLM API | 20 | per hour | Per user |
| Default | 200 | per minute | Per user |

- **Implementation**: SlowAPI with Redis backend for distributed rate limiting
- **Response**: HTTP 429 with Retry-After header
- **Monitoring**: Rate limit events logged for anomaly detection
- **Bypass**: Rate limit bypass requires admin API key with audit logging

### Input Sanitization

- **Pydantic Validation**: Type validation, field constraints, and custom validators
- **HTML Sanitization**: bleach library for HTML input cleaning
- **Encoding Detection**: URL, Unicode, and HTML entity decoding detection
- **Control Character Stripping**: Null bytes, newlines, and control characters removed
- **Prompt Injection Detection**: LLM-specific injection pattern detection for AI endpoints

### Security Headers

| Header | Value | Purpose |
|--------|-------|---------|
| Strict-Transport-Security | max-age=31536000; includeSubDomains | HTTPS enforcement |
| X-Frame-Options | DENY | Clickjacking protection |
| X-Content-Type-Options | nosniff | MIME sniffing prevention |
| Content-Security-Policy | default-src 'self'; script-src 'self' 'unsafe-inline' | XSS mitigation |
| X-Permitted-Cross-Domain-Policies | none | Flash/Acrobat restriction |
| Referrer-Policy | strict-origin-when-cross-origin | Referrer control |

- **Middleware**: All headers set via centralized security headers middleware
- **Override**: Headers can be overridden per-endpoint with security review

---

## Security Testing Requirements for Contributors

All contributors must adhere to the following security testing requirements:

### Required Security Test Suite

Before submitting any pull request, contributors must run the security test suite:

```bash
# Run all security tests
pytest backend/tests/test_security_headers.py -v
pytest backend/tests/test_encoding_bypasses.py -v
pytest backend/tests/test_idor.py -v
pytest backend/tests/test_auth.py -v

# Run with coverage
pytest backend/tests --cov=backend.core.security --cov=backend.core.auth
```

**Pre-submission Checklist:**
- [ ] All security tests pass
- [ ] No new security warnings from static analysis (bandit, safety)
- [ ] PII masking verified for new log statements
- [ ] RBAC decorators applied to new endpoints
- [ ] Rate limiting applied to new endpoints

### Sanitization Requirements

- **NEVER** disable input sanitization for "testing purposes"
- **NEVER** comment out Pydantic validators to "make it work"
- **NEVER** bypass bleach sanitization for "trusted input"
- All validator bypasses must be documented in code with security review approval

### RBAC Requirements

- All new endpoints must have explicit RBAC checks via `@require_role` decorator
- Resource-level access control required for endpoints accessing student data
- IDOR vulnerability tests must be included for endpoints with path parameters
- Test cases must verify both allowed and denied access scenarios

### PII Logging Requirements

- **NEVER** log raw student email addresses
- **NEVER** log raw student IDs or org_defined_id values
- **NEVER** log authentication tokens or passwords
- **NEVER** include real student data in test files or fixtures
- Use `mask_pii()` function for all log output containing student references
- Use synthetic data generators for all test data

### Security Review Process

1. **Automated Scanning**: All PRs scanned with bandit (Python security linter)
2. **Dependency Audit**: pip-audit runs on requirements.txt changes
3. **Security Test Gate**: PRs cannot merge with failing security tests
4. **Manual Review**: Security Lead reviews changes to:
   - Authentication/authorization code
   - Data access layer modifications
   - PII handling code
   - Rate limiting configuration

---

## Incident Response Overview

The EWS Retention Platform follows a structured incident response process aligned with NIST SP 800-61.

### Detection

**Monitoring Sources:**
- Audit log anomaly detection (unexpected bulk access patterns)
- Failed authentication rate monitoring
- PII detection in application logs
- Unauthorized access attempts to FERPA data
- Infrastructure monitoring (Redis, database)
- External security notifications (CVE feeds, vendor advisories)

**Detection Channels:**
- Security@<your-domain> email monitoring
- GitHub Security Advisory notifications
- Automated security scanning alerts
- User incident reports
- Threat intelligence feeds

### Containment

**Immediate Actions (within 1 hour):**
- Activate Security Incident Response Team
- Isolate affected systems (disable compromised accounts, block IPs)
- Preserve evidence (snapshot logs, database state)
- Notify Security Lead and Project Maintainer
- Assess FERPA breach notification requirements

**Short-term Containment (within 24 hours):**
- Deploy emergency patches for confirmed vulnerabilities
- Implement temporary workarounds (WAF rules, additional rate limiting)
- Revoke compromised credentials/tokens
- Enable enhanced monitoring on affected systems

### Eradication

**Vulnerability Remediation:**
- Develop and test permanent fix
- Verify fix addresses root cause (not just symptoms)
- Scan for similar vulnerabilities in codebase
- Update security controls to prevent recurrence

**Threat Removal:**
- Remove attacker persistence mechanisms
- Clean compromised data if any
- Rotate all potentially exposed credentials
- Verify no unauthorized access remains

### Recovery

**System Restoration:**
- Restore affected systems from known-good state if necessary
- Gradual return to production with enhanced monitoring
- Verify all security controls functioning
- Confirm audit logging operational

**Monitoring Enhancement:**
- Increase monitoring frequency for affected components
- Implement additional detection rules
- Extended monitoring period (minimum 30 days)

### Postmortem Review

**Timeline:** Within 5 business days of incident closure

**Required Elements:**
- Timeline of incident from detection to resolution
- Root cause analysis (5 Whys methodology)
- Impact assessment (data exposed, systems affected, FERPA implications)
- Response effectiveness evaluation
- Lessons learned and process improvements
- Action items with owners and deadlines

**Distribution:**
- Incident report to project leadership
- Summary to affected users (if applicable)
- FERPA breach notification to institution (if required)
- Updates to security policy and controls based on findings

**Retention:**
- Incident documentation retained for 7 years
- Lessons learned integrated into security training
- Control improvements tracked and verified

---

## License

This security policy is part of the project's security documentation and is subject to the same license terms as the project codebase.
