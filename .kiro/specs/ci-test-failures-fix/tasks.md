# Implementation Plan

## Bug 1: Import Error Fix

- [ ] 1. Write bug condition exploration test for import error
  - **Property 1: Bug Condition** - GradedComponent Import Path Error
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the import error exists
  - **Scoped PBT Approach**: Test the 4 specific files with incorrect import paths
  - Test that importing GradedComponent from `backend.database.models.graded_component` fails with ModuleNotFoundError
  - Test files: test_fk_constraints.py, test_recommendations_idor.py, test_cohort_risk_profiles.py, rag_engine.py
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with ModuleNotFoundError (this is correct - it proves the bug exists)
  - Document counterexamples found (21 test failures due to import error)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 2.1_

- [ ] 2. Write preservation property tests for import error fix (BEFORE implementing fix)
  - **Property 2: Preservation** - Other Model Imports Continue Working
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy imports
  - Test that importing ExamRecord from backend.database.models.academic works correctly
  - Test that importing other models (Student, Enrollment, Course, etc.) works correctly
  - Test that GradedComponent model functionality (create, query, relationships) works correctly
  - Write property-based tests capturing observed import behavior patterns
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1_

- [ ] 3. Fix import paths for GradedComponent

  - [ ] 3.1 Update import statements in all affected files
    - Replace `from backend.database.models.graded_component import GradedComponent` with `from backend.database.models.academic import GradedComponent`
    - Files to update:
      - backend/tests/test_fk_constraints.py (line 200)
      - backend/tests/test_recommendations_idor.py (line 43)
      - backend/tests/test_cohort_risk_profiles.py (line 60)
      - backend/services/ai/rag_engine.py (line 15)
    - _Bug_Condition: isBugCondition1(import_statement) where import_statement references non-existent module path_
    - _Expected_Behavior: Import succeeds from backend.database.models.academic where GradedComponent is defined_
    - _Preservation: All other model imports continue to work correctly_
    - _Requirements: 1.1, 2.1, 3.1_

  - [ ] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - GradedComponent Import Succeeds
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - Verify all 21 previously failing tests now pass
    - _Requirements: 2.1_

  - [ ] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Other Model Imports Preserved
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all import tests still pass after fix

## Bug 2: Ghost Detection Logic Fix

- [ ] 4. Write bug condition exploration test for ghost detection
  - **Property 1: Bug Condition** - Empty Enrollments Ghost Detection Error
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the ghost detection bug exists
  - **Scoped PBT Approach**: Test the specific case of empty enrollments with zero login count
  - Test that ConsistencyFeatureExtractor.extract(enrollments=[], total_login_count=0) returns is_ghost=True (incorrect behavior)
  - Expected correct behavior: should return is_ghost=False (no courses means not a ghost)
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (returns is_ghost=True instead of False - this proves the bug exists)
  - Document counterexamples found
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.2, 2.2_

- [ ] 5. Write preservation property tests for ghost detection (BEFORE implementing fix)
  - **Property 2: Preservation** - Ghost Detection for Enrolled Students
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for students with enrollments
  - Test that students with enrollments and zero progress are correctly detected as ghosts
  - Test that students with zero logins and enrollments are detected as "never_logged_in" ghosts
  - Test that students with logins but zero progress are detected as "logged_in_never_started" ghosts
  - Test that zero_progress_course_count is correctly calculated
  - Write property-based tests capturing observed ghost detection patterns
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.2, 3.5_

- [ ] 6. Fix ghost detection logic for empty enrollments

  - [ ] 6.1 Update _detect_ghost_student method in ConsistencyFeatureExtractor
    - File: backend/services/features/consistency.py
    - In the `if total_courses == 0:` block (around line 155), change logic to return is_ghost=False
    - Add comment: "No enrollments means not a ghost (ghost implies enrolled but not engaging)"
    - Return {"is_ghost": False, "ghost_type": None, ...}
    - _Bug_Condition: isBugCondition2(enrollments, login_count) where len(enrollments)==0 and login_count==0_
    - _Expected_Behavior: Returns is_ghost=False for students with no course enrollments_
    - _Preservation: Ghost detection for enrolled students continues to work correctly_
    - _Requirements: 1.2, 2.2, 3.2, 3.5_

  - [ ] 6.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Empty Enrollments Returns False
    - **IMPORTANT**: Re-run the SAME test from task 4 - do NOT write a new test
    - The test from task 4 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 4
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed - now returns is_ghost=False)
    - _Requirements: 2.2_

  - [ ] 6.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Ghost Detection Preserved
    - **IMPORTANT**: Re-run the SAME tests from task 5 - do NOT write new tests
    - Run preservation property tests from step 5
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all ghost detection tests still pass after fix

## Bug 3: Engagement Pattern Boundary Fix

- [ ] 7. Write bug condition exploration test for engagement pattern boundary
  - **Property 1: Bug Condition** - 5% Completion Boundary Error
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the boundary condition bug exists
  - **Scoped PBT Approach**: Test the specific boundary case of exactly 5% completion with < 5 logins
  - Test that _classify_engagement_pattern(login_count=4, content_completion_rate=0.05, ...) returns "disengaged" (incorrect)
  - Expected correct behavior: should NOT return "disengaged" (condition requires < 5%, not <= 5%)
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (returns "disengaged" instead of other pattern - this proves the bug exists)
  - Document counterexamples found
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.3, 2.3_

- [ ] 8. Write preservation property tests for engagement pattern (BEFORE implementing fix)
  - **Property 2: Preservation** - Engagement Pattern Classification Preserved
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-boundary cases
  - Test that students with < 5% completion and < 5 logins return "disengaged"
  - Test that students with high login, low completion, poor quiz scores return "struggling"
  - Test that students with risk_score >= 40 return "at_risk_normal"
  - Test that students with healthy engagement return "on_track"
  - Write property-based tests capturing observed engagement pattern classification
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.3, 3.6_

- [ ] 9. Fix engagement pattern boundary condition

  - [ ] 9.1 Update _classify_engagement_pattern method in IntentFeatureExtractor
    - File: backend/services/features/intent.py
    - In the disengaged rule (around line 82), change `content_completion_rate <= 0.05` to `content_completion_rate < 0.05`
    - Change: `if login_count < 5 and content_completion_rate <= 0.05:` to `if login_count < 5 and content_completion_rate < 0.05:`
    - _Bug_Condition: isBugCondition3(login_count, completion_rate) where login_count<5 and completion_rate==0.05_
    - _Expected_Behavior: Students with exactly 5% completion should NOT be classified as "disengaged"_
    - _Preservation: All other engagement pattern classifications continue to work correctly_
    - _Requirements: 1.3, 2.3, 3.3, 3.6_

  - [ ] 9.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - 5% Completion Not Disengaged
    - **IMPORTANT**: Re-run the SAME test from task 7 - do NOT write a new test
    - The test from task 7 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 7
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed - 5% completion no longer returns "disengaged")
    - _Requirements: 2.3_

  - [ ] 9.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Engagement Patterns Preserved
    - **IMPORTANT**: Re-run the SAME tests from task 8 - do NOT write new tests
    - Run preservation property tests from step 8
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all engagement pattern tests still pass after fix

## Bug 4: Null Field Handling Fix

- [ ] 10. Write bug condition exploration test for null field handling
  - **Property 1: Bug Condition** - Null Fields Cause 500 Error
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the null field handling bug exists
  - **Scoped PBT Approach**: Test the specific case of student with all null name/department fields
  - Test that cohort-risk-profiles endpoint with student having null first_name, last_name, parent_department_name returns 500 error (incorrect)
  - Expected correct behavior: should return 200 OK with gracefully handled null values
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (returns 500 error instead of 200 OK - this proves the bug exists)
  - Document counterexamples found
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.4, 2.4_

- [ ] 11. Write preservation property tests for null field handling (BEFORE implementing fix)
  - **Property 2: Preservation** - Valid Student Profiles Preserved
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for students with valid fields
  - Test that students with valid non-null fields return correct profile data
  - Test that risk_min and risk_max filtering works correctly
  - Test that academic, engagement, and consistency signals are calculated correctly
  - Test that pagination and batch processing work correctly
  - Write property-based tests capturing observed profile building behavior
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.4_

- [ ] 12. Fix null field handling in profile building

  - [ ] 12.1 Update _build_risk_profile_from_cached_data function
    - File: backend/routes/integration.py
    - Verify student_name construction (around line 280) properly handles null values
    - Ensure pattern: `f"{student.first_name or ''} {student.last_name or ''}".strip() or student.id`
    - Verify dept_name construction properly handles null values
    - Ensure pattern: `(student.parent_department_name or "").lower()`
    - Add explicit null checks if needed to prevent string concatenation errors
    - _Bug_Condition: isBugCondition4(student) where student has null first_name, last_name, parent_department_name_
    - _Expected_Behavior: Returns 200 OK with gracefully handled null values (fallback to student.id)_
    - _Preservation: Profile building for valid students continues to work correctly_
    - _Requirements: 1.4, 2.4, 3.4_

  - [ ] 12.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Null Fields Return 200 OK
    - **IMPORTANT**: Re-run the SAME test from task 10 - do NOT write a new test
    - The test from task 10 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 10
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed - now returns 200 OK)
    - _Requirements: 2.4_

  - [ ] 12.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Profile Building Preserved
    - **IMPORTANT**: Re-run the SAME tests from task 11 - do NOT write new tests
    - Run preservation property tests from step 11
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all profile building tests still pass after fix

## Final Validation

- [ ] 13. Checkpoint - Ensure all tests pass
  - Run full test suite to verify all 24 previously failing tests now pass
  - Verify no new test failures introduced
  - Verify all 4 bugs are fixed:
    - Import error: 21 tests now pass
    - Ghost detection: edge case handled correctly
    - Engagement pattern: boundary condition fixed
    - Null field handling: endpoint returns 200 OK
  - Ask the user if questions arise
