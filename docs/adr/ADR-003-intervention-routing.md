# ADR-003: Intervention Routing — Rule-Based Decision Engine vs LLM-Generated Messages

## Status

**Accepted** — Implemented in v1.1.0

## Context

The team has prior experience with LLM/RAG systems (Gemini, Claude integration exists for other features). Two approaches were considered for intervention recommendation:

**Option A: LLM-Generated Interventions**
- Input: Student features, history, risk score
- Output: Personalized intervention message + channel recommendations
- Pros: Highly personalized, natural language, can adapt tone to student profile
- Cons: Non-deterministic, harder to test, potential for inappropriate recommendations, requires prompt engineering maintenance

**Option B: Rule-Based Decision Engine**
- Input: Risk score, engagement pattern, academic flags
- Output: Categorized intervention type with template action items
- Pros: Deterministic, auditable, testable, consistent across similar students
- Cons: Less personalized, templates may feel generic

Current state:
- LLM integration exists for optional "AI advice" feature (`/api/v1/llm/*`)
- No historical intervention effectiveness data exists to evaluate LLM recommendations
- Advisors need consistent, predictable guidance they can learn to trust
- Regulatory/compliance considerations favor auditable decision paths

## Decision

Use a **deterministic decision engine** for V1 intervention routing with the following structure:

1. **Academic flag overrides** (highest priority):
   - Dropout intent → retention_emergency (critical, sales call)
   - UFM flagged → academic_integrity (high, dean notification)
   - Deferred → suppress_intervention
   - Health support → welfare_referral

2. **Ghost student override**:
   - Never logged in → activation_outreach (direct call, no automated messages)
   - Logged in never started → activation_outreach (onboarding walkthrough)

3. **Engagement pattern routing** (E-2):
   - Struggling → academic_support (TA session, remedial content)
   - Disengaged → re_engagement (verify platform access, warm outreach)

4. **Threshold ladder** (0-100 scale):
   - <30: No action
   - 30-40: Gentle reminder (automated email)
   - 40-60: Mentor outreach (faculty)
   - 60-80: Escalated mentor outreach (faculty, high urgency)
   - >=80: Urgent intervention (sales + WhatsApp + incentives)

Define the **path to LLM personalization** as follows:
1. V1 (current): Rule-based with consistent templates
2. V1.5: Collect intervention outcome data via `InterventionLog` system (E-9)
3. V2: A/B test LLM personalization vs rule-based for specific intervention types
4. V2.5: LLM used for message drafting within rule-determined categories (human approval required)

## Consequences

### Positive

- **Auditable**: Every recommendation traceable to specific rule
- **Testable**: Unit tests can verify routing for all combinations
- **Consistent**: Similar students receive similar interventions (fairness)
- **Safe**: No risk of LLM hallucinating inappropriate actions
- **Fallback preserved**: Rules work even if LLM service unavailable

### Negative

- **Generic messaging**: Students may receive similar-sounding communications
- **Manual template maintenance**: Message templates require updates per trimester
- **No personalization nuance**: Cannot adapt to individual student circumstances beyond categories
- **Binary classification**: Pattern classification may miss edge cases

### Mitigations

- Message templates include personalization fields (student name, course names, specific metrics)
- `InterventionLog.notes` field allows advisors to add personalized context when acting
- LLM-based "AI advice" feature remains available as optional supplemental guidance
- Effectiveness tracking (E-9) will inform which intervention types warrant deeper personalization investment
