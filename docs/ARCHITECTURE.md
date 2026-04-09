# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) documenting significant architectural decisions made during the development of the EWS Retention Platform.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences. ADRs help teams understand why certain technical choices were made and provide a historical record for future developers.

## Current ADRs

### ADR-001: Risk Scoring Approach
**Status**: Accepted  
**Date**: 2024-03-15

**Decision**: Use a rule-based weighted aggregation approach for risk scoring instead of pre-trained ML models.

**Context**: 
- Pre-trained XGBoost models exist but have schema mismatches with live data
- Need explainable scores for faculty trust
- Feature engineering pipeline was already producing normalized 0-100 scores

**Consequences**:
- (+) Highly explainable to non-technical stakeholders
- (+) No model training or drift monitoring required
- (+) Fast computation without model loading overhead
- (-) Cannot capture complex non-linear relationships
- (-) Requires manual tuning of feature weights

**Alternative Considered**: XGBoost inference with feature adaptation

---

### ADR-002: Database Selection
**Status**: Accepted  
**Date**: 2024-02-20

**Decision**: Use SQLite for development/single-instance deployment, PostgreSQL for production multi-worker setups.

**Context**:
- Development team needs simple setup
- SQLite sufficient for single-instance deployments
- Migration path to PostgreSQL via SQLAlchemy

**Consequences**:
- (+) Zero-config development environment
- (+) Single file backup/restore
- (-) No concurrent writes (single-writer limitation)
- (-) Limited scalability for high-traffic scenarios

---

### ADR-003: Frontend Authentication Strategy
**Status**: Proposed → In Progress  
**Date**: 2024-04-01

**Decision**: Implement JWT-based authentication with backend integration.

**Context**:
- Current React app uses hardcoded credentials for demo
- Backend has full JWT auth implementation
- Need to bridge frontend with existing auth system

**Implementation Plan**:
1. Create AuthContext in React
2. Integrate with `/api/v1/auth/login` and `/api/v1/auth/register`
3. Store JWT in httpOnly cookie or secure storage
4. Add auth headers to all API requests

---

### ADR-004: Feature Engineering Modularity
**Status**: Accepted  
**Date**: 2026-04-09

**Decision**: Refactor monolithic FeatureEngineer (28KB) into 4 domain-specific extractors.

**Context**:
- Original FeatureEngineer was a "God class" with 30+ methods
- Mixed concerns: academic, engagement, consistency, intent features
- Difficult to test and maintain

**Solution**:
- `AcademicFeatureExtractor`: Graded performance, exam scores
- `EngagementFeatureExtractor`: LMS activity, content completion
- `ConsistencyFeatureExtractor`: Login patterns, ghost detection
- `IntentFeatureExtractor`: Engagement pattern classification
- `FeatureEngineer`: Composer orchestrating all 4

**Consequences**:
- (+) Single Responsibility Principle compliance
- (+) Easier unit testing per domain
- (+) Typed dataclasses instead of dicts
- (+) Backward compatible API maintained
