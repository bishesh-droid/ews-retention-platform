# Layered Architecture Migration Plan

## Goal
Move from service-centric modules to a layered architecture:
- `domain/` for business rules and policies
- `application/` for orchestration and use-cases
- `infrastructure/` for persistence and external I/O
- `presentation/` for API shaping and transport concerns

## Current state (after this refactor)
- Student bounded context is now split across:
  - `backend/domain/student/policies.py`
  - `backend/application/student/student_application_service.py`
  - `backend/infrastructure/student_repository.py`
  - `backend/presentation/student/serializers.py`
- Legacy API entry points still call `backend/services/student_service.py`,
  which now acts as a compatibility facade.

## Phase 1: Stabilize compatibility facade
1. Keep `backend/services/student_service.py` as adapter-only.
2. Block new logic in facade via code review rule.
3. Add tests around critical student endpoints:
   - `GET /students`
   - `GET /students/{id}`
   - `GET /students/{id}/weekly-summary`
   - `GET /analytics/trends`

## Phase 2: Route/application decoupling
1. Replace calls to private facade methods in routes:
   - `_get_enrollment_dicts`
   - `_get_graded_components`
   - `_get_exam_records`
2. Expose explicit application use-cases for ML routes:
   - `get_student_learning_inputs(student_id)`
   - `get_batch_learning_inputs(student_ids)`
3. Update controllers to call application services directly where possible.

## Phase 3: Move remaining student analytics
1. Extract cohort trend computations from controllers into:
   - `backend/application/student/analytics_use_cases.py`
2. Keep only HTTP concerns in controllers (validation, status codes, mapping).
3. Move common score normalization helpers into a single domain or application utility.

## Phase 4: Apply pattern to other God/mixed modules
Prioritize by fan-out and change frequency:
1. `backend/services/ml_service.py`
2. `backend/routes/business.py`
3. `backend/routes/llm.py`

For each module:
1. Identify domain rules vs orchestration vs I/O.
2. Move SQL-heavy logic into `infrastructure/`.
3. Move branching business rules into `domain/`.
4. Keep response shaping in `presentation/`.
5. Leave a short-lived compatibility facade at old import path.

## Phase 5: Dead code and duplicate logic cleanup
1. Remove compatibility methods after all imports are migrated.
2. Consolidate duplicate risk normalization and trend bucketing.
3. Delete unused helper functions and stale route-level logic.
4. Enforce layered boundaries with import lints.

## Phase 6: Final cutover
1. Remove `backend/services/student_service.py` facade.
2. Update all imports to layered modules.
3. Run full test + smoke API checks.
4. Publish architecture update in `ARCHITECTURE.md`.
