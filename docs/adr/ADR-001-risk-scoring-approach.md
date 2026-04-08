# ADR-001: Risk Scoring Approach — Rule-Based Formula vs Trained ML Model

## Status

**Accepted** — Implemented in v1.1.0

## Context

At project start, no labeled outcome data exists for the target student cohort. The BITS Pilani Digital Campus program is relatively new, and historical retention outcomes are:
- Sparse (only one prior trimester with reliable tracking)
- Not yet linked to engagement data exports
- Inconsistent in definition (what constitutes "dropout" varies by timing and reason)

Early prototypes included XGBoost and Logistic Regression model files in `models/saved_models/`, but these were discovered to have a schema mismatch between their training features (absrate7, q4mpa7, nsusp7, mobility7) and the runtime database schema (content completion, login consistency, quiz engagement, etc.). The training code that produced these models is no longer in the repository, and no pipeline exists to retrain them.

The team needs to decide:
1. Attempt to rebuild a trained ML pipeline with insufficient labeled data
2. Ship a deterministic rule-based scorer that works now with clear upgrade path

## Decision

Use a **deterministic weighted formula** for V1 (current implementation).

The formula structure is:
```
risk_score = 100 - weighted_engagement
  + zero_progress_penalty
  + calendar_blend_adjustment
  + ghost_override (if applicable)
  + academic_flag_overrides
```

Where `weighted_engagement` is the sum of feature scores multiplied by configurable weights from `FEATURE_WEIGHTS` in config.

Define the **path to ML** as follows:
1. V1 (current): Rule-based with T1 cohort labeling via `infer_outcomes_from_exam_data()`
2. V1.5: Run `backend/ml/training/calibrate.py` to optimize thresholds against T1 outcomes
3. V2: Once 2+ trimesters of labeled data exist, train gradient-boosted model using same feature set
4. V2.5: A/B test rule-based vs ML, maintain fallback to rule-based if ML confidence low

## Consequences

### Positive

- **Operational immediately**: No dependency on labeled historical data
- **Interpretable**: Advisors can see exactly which features drive a student's score
- **Debuggable**: Risk scores can be manually recalculated from raw features for verification
- **Configurable**: Thresholds and weights adjustable via environment variables
- **Safe fallback**: Even in V2 with ML, rule-based remains as fallback for edge cases

### Negative

- **Not calibrated to actual outcomes**: Default thresholds (30/40/60/80) are starting hypotheses, not empirically validated
- **Requires manual calibration**: Operations team must run `calibrate.py` after each trimester to optimize thresholds
- **Cannot capture complex interactions**: Formula is linear (with minor nonlinear penalties), may miss feature interactions that predict dropout
- **Per-cohort variability**: A rule that works for T1 may not generalize to T2 without recalibration

### Mitigations

- Calibration script provided (`backend/ml/training/calibrate.py`) to optimize thresholds against actual T1 exam outcomes
- Evaluation endpoint (`GET /api/v1/admin/evaluate-scorer`) reports precision/recall against labeled data
- All thresholds and weights are environment-configurable without code changes
- Clear documentation of the "path to ML" for stakeholders
