# ML and Scoring Pipeline (Implemented State)

## Scope

This file separates active runtime scoring behavior from legacy or offline ML assets included in the repository.

## 1) Active Runtime Pipeline

Primary runtime path:

1. Load student interaction/performance data from backend DB models.
2. Compute engineered features with `backend/services/feature_engineering.py`.
3. Compute risk score with `backend/services/risk_scoring.py`.
4. Persist prediction snapshots through:
   - `backend/services/ml_service.py`
   - `backend/services/infrastructure/scheduler.py`

This path is rule-based and deterministic over current DB records.

## 2) Why Runtime Is Rule-Based

`backend/services/ml_service.py` explicitly attempts to load saved joblib pipeline artifacts, then disables model usage for scoring due to feature schema mismatch:

- Saved model expects historical absrate/mpa-style feature schema.
- Runtime DB feature schema is LMS-centric and differs in column set.
- Service logs this and falls back to rule-based path.

Result:

- `model_used` remains false in runtime responses.
- Model inference is not active until retraining aligns schema.

## 3) Runtime Feature Set

Feature engineering consumes:

- enrollment activity counters
- discussion and login activity
- graded quiz/assignment scores
- exam attendance and exam marks

Derived outputs include:

- content completion metrics
- quiz engagement metrics
- graded score signals
- attendance and consistency signals
- trend and progress labels

The exact fields returned by `StudentService` include compatibility aliases for frontend (`attendance_score`, `academic_score`, `behavioral_score`, `stability_score`).

## 4) Risk Score Semantics

Risk score in service-level calculations: 0-100.

Risk category mapping used by scoring helpers:

- low
- medium
- high (and urgency mapping in intervention helpers)

Persistence mapping:

- `Prediction.risk_score` stored as probability 0-1.
- Similar scaling in `RiskSnapshot`.

This creates conversion points that must be handled per endpoint.

## 5) Batch Prediction Scheduler

`backend/services/infrastructure/scheduler.py`:

- Daily at 03:00 UTC:
  - computes features for all students
  - calculates risk score
  - inserts `Prediction` and `RiskSnapshot`
- Weekly at Sunday 04:00 UTC:
  - logs retrain placeholder, no retraining execution

Therefore, model drift adaptation is currently manual.

## 6) API-Side ML Endpoints

`/api/v1/ml/*` and `/api/v1/predictions/*` endpoints expose:

- per-student predictions
- batch/cached outputs
- model status metadata
- trend/cohort views

These outputs are currently driven by the rule-based service and persisted records.

## 7) Legacy and Parallel ML Assets

## 7.1 `models/` standalone pipeline

Contains:

- training scripts
- prediction scripts
- feature engineering scripts
- model loaders and saved artifacts

This pipeline expects different source datasets and is not auto-wired to backend startup.

## 7.2 `backend/ml/` package status

Contains evaluate utilities and partial package exports.
Some exports/imports reference removed symbols, indicating incomplete migration.

## 8) Risks and Failure Modes

- Schema mismatch between stored model artifacts and runtime features blocks true inference.
- 0-1 persisted vs 0-100 service logic can create threshold inconsistencies.
- Scheduler retrain is placeholder; no automatic labeled retraining loop.
- Multiple ML code paths increase confusion in operational ownership.

## 9) Recommended Consolidation Path

1. Define one canonical feature schema (runtime DB features or historical features).
2. Retrain and version a model on that schema.
3. Add strict feature-schema validation before inference.
4. Persist risk units consistently (single scale).
5. Remove stale exports and archive inactive ML paths.

## 10) Operational Truth Table

- Runtime prediction in API: active, rule-based.
- Scheduler daily prediction persistence: active.
- Scheduler weekly retraining: inactive placeholder.
- Root `models/` training utilities: available but manual/offline.
- `backend/ml` as complete production package: partial/inconsistent.
