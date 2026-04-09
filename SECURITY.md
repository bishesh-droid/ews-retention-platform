# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.1.x   | :white_check_mark: |
| 2.0.x   | :x:                |
| < 2.0   | :x:                |

## Reporting a Vulnerability

We take the security of the EWS Retention Platform seriously. This system handles sensitive student educational data protected under FERPA, and we appreciate your help in maintaining its security.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to:

📧 **security@your-organization.edu** (placeholder - update with actual contact)

Please include:
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact assessment
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 5 business days
- **Resolution**: Based on severity (see below)

### Severity Classifications

| Severity | Example | Resolution Target |
|----------|---------|-------------------|
| Critical | Data breach, FERPA violation, RCE | 24-48 hours |
| High | Authentication bypass, SQL injection | 1 week |
| Medium | XSS, CSRF, Information disclosure | 2 weeks |
| Low | Best practice violations | Next release |

## Security Considerations for This Project

### Data Sensitivity
This platform processes **FERPA-protected educational records**. All contributors must:
- Understand FERPA compliance requirements
- Implement proper access controls
- Audit all data access patterns
- Use encryption for data in transit and at rest

### Current Security Measures
- JWT-based authentication with role-based access control
- Input validation via Pydantic schemas
- Rate limiting (SlowAPI)
- Security headers middleware
- PII masking in logs
- Audit logging for data access

### Known Security Gaps (from README)
1. Frontend uses hardcoded credentials for demo purposes
2. Rate limiting is in-memory only (resets on restart)
3. SQLite single-writer constraints

### Security Best Practices for Contributors

1. **Never commit secrets** - Use `.env` files (already in `.gitignore`)
2. **Validate all inputs** - Use Pydantic validators
3. **Sanitize outputs** - Use PII masking for logs
4. **Test auth flows** - Verify RBAC on all endpoints
5. **Audit data access** - Use `log_data_access()` for student data

## License

This security policy is part of the project's MIT License terms.
