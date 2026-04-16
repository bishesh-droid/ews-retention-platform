# Code of Conduct

## 1. Purpose

This project — Meridian, an Early Warning System for student retention — processes sensitive student academic and engagement records protected under the Family Educational Rights and Privacy Act (FERPA). That regulatory context shapes every expectation in this document.

This Code of Conduct applies to all contributors, maintainers, reviewers, and anyone with access to the codebase, infrastructure, CI/CD pipelines, or any environment that contains or processes student data. It applies in all project spaces: pull requests, code reviews, issue discussions, team channels, and direct communication related to this project.

---

## 2. Our Standards

### Expected behaviors

- **Constructive code review.** Critique the code, not the person. Reviews should explain *why* a change is problematic and, where possible, suggest an alternative. Tone that would be unacceptable in a face-to-face meeting is unacceptable in a PR comment.

- **Documentation on sensitive changes.** Any change that touches authentication, authorization, data access paths, or student PII must include a clear description of what changed and why. This is not optional — reviewers are entitled to that context before approving.

- **Responsible vulnerability disclosure.** Security issues discovered in this codebase must be reported privately through the process described in `SECURITY.md`. Do not open a public GitHub issue for a security finding.

- **Clarifying questions before assumptions.** In reviews and architecture discussions, ask before assuming intent. A question is cheaper than a revert.

- **Welcoming contributors across disciplines.** This project has contributors from Computer Science, Civil Engineering, and Data Science backgrounds. Experience with FastAPI or React is not a prerequisite for meaningful contribution. Technical feedback should be calibrated to the contributor's domain.

### Unacceptable behaviors

- Committing secrets, credentials, API keys, or tokens to any branch — including feature branches and draft PRs. The detect-secrets baseline exists for this reason; circumventing it is a policy violation.

- Accessing, exporting, copying, or sharing student data outside of the defined data handling procedures — regardless of the stated reason.

- Bypassing or disabling security controls (rate limiting, RBAC, audit logging) without documented approval from the tech lead. "It was slowing down development" is not an approval.

- Merging a PR with failing security gates (Bandit, detect-secrets) without a written exception signed off by the tech lead. The exception must be recorded in the PR before merge, not after.

- Harassment, discrimination, or hostile communication in any project space — reviews, issues, or team channels. This includes sustained dismissiveness, condescension about background or experience level, and any conduct based on race, gender, nationality, disability, or religion.

---

## 3. Data Handling Responsibilities

Because this project processes FERPA-protected student records, every contributor must understand and follow these rules without exception.

**Development environments**
- Never copy real student data to a local development environment. Use synthetic test fixtures only. If you need representative data for local testing, generate it — do not export it from any staging or production database.

**Logging and debug output**
- Never log, print, or expose raw student PII (names, student IDs, grades, enrollment records) in debug output, error messages, or stack traces. The PII-masking logger in `backend/core/logger.py` handles this automatically. Do not bypass it, wrap around it, or use the standard library `logging` module directly in code paths that handle student records.

**Accidental exposure**
- Treat any accidental exposure of student data — leaked in logs, committed to a branch, pasted in a comment — as a security incident. Report it immediately per the incident response process in `SECURITY.md`. Speed of disclosure matters; delay makes remediation harder.

**Audit logs**
- Audit logs are append-only by design. They must not be modified, truncated, rotated destructively, or deleted under any circumstances. If you believe an audit log entry contains an error, raise it with the tech lead — do not attempt to correct it yourself.

---

## 4. Contribution Responsibilities

### All contributors

- Follow the branching model defined in `README.md`: `feature/*` branches off `develop`; `develop` merges to `main` via reviewed PR. Do not push directly to `main` or `develop`.
- Ensure all CI quality gates pass before requesting review: linting, type checking, Bandit security scan, detect-secrets, and the test suite.
- Include tests for any new API endpoint, service method, or security-relevant logic. A PR that adds behavior without tests will not be merged.
- Add audit logging for any new endpoint that reads or writes student data. The audit logger in `backend/core/audit_logger.py` is the standard path.

### Security-sensitive changes

Changes to authentication, authorization (RBAC), PII access paths, or LLM prompt construction require additional process:

1. Tag the PR with the `security-review` label before requesting review.
2. Request review from the security-designated reviewer. The PR must not be merged without their approval.
3. Include a brief threat model in the PR description: what is the attack surface, what could go wrong, and how does this change handle it?

"Security-sensitive" means: auth tokens, session handling, permission checks, queries that return student records, and any code that passes student data to an external service or LLM.

---

## 5. Incident Reporting

**Security incidents** — discovered vulnerabilities, accidental data exposure, compromised credentials, suspected unauthorized access — must be reported privately via the process in `SECURITY.md`. Do not open a public GitHub issue. Time-sensitive incidents should be escalated directly to the project maintainer.

**Conduct concerns** — violations of this Code of Conduct, harassment, or hostile behavior — should be reported to the project maintainer directly. Reports will be handled discreetly.

---

## 6. Enforcement

Reported violations will be reviewed by the project maintainer. Consequences depend on severity and context:

- **Required correction** — the default for first-time, non-malicious violations (e.g. a committed key that is promptly reported). The contributor is expected to remediate the issue and understand why it matters.
- **Temporary or permanent removal of repository and infrastructure access** — for repeated violations, malicious intent, unauthorized data access, or deliberate bypass of security controls.

Accidental credential commits that are promptly disclosed and remediated will be treated as learning opportunities, not punitive violations. The important thing is that they are reported fast and handled correctly. Concealment is treated far more seriously than the original mistake.

---

## 7. Attribution

This Code of Conduct is adapted from the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/), with additional provisions specific to FERPA-regulated educational data handling.
