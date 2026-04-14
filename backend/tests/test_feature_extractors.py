"""
TEST-5: Feature Extractor Tests

Comprehensive tests for the modular feature extraction system:
- AcademicFeatureExtractor
- EngagementFeatureExtractor
- ConsistencyFeatureExtractor
- IntentFeatureExtractor

These tests replace TODOs in the original test suite and verify:
1. Each extractor works in isolation
2. Edge cases (empty data, missing fields, None values)
3. Score bounds [0-100]
4. Type safety with dataclasses
"""

import pytest
from typing import List, Dict

from backend.services.features.academic import AcademicFeatureExtractor, AcademicFeatures
from backend.services.features.engagement import EngagementFeatureExtractor, EngagementFeatures
from backend.services.features.consistency import ConsistencyFeatureExtractor, ConsistencyFeatures
from backend.services.features.intent import IntentFeatureExtractor, IntentFeatures
from backend.services.features.composer import FeatureEngineer


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_enrollments() -> List[Dict]:
    """Sample enrollment data for testing."""
    return [
        {
            "course_id": "CS101",
            "course_name": "Intro to Computer Science",
            "content_completed": 15,
            "content_required": 20,
            "content_required_w1w2": 5,
            "content_completed_w1w2": 4,
            "quiz_completed": 3,
            "total_quiz_attempts": 5,
            "discussion_posts_created": 5,
            "discussion_post_replies": 10,
            "discussion_posts_read": 50,
            "num_assignment_submissions": 4,
            "total_time_spent_seconds": 36000,  # 10 hours
            "num_logins": 25,
            "is_optional": False,
        },
        {
            "course_id": "DS201",
            "course_name": "Data Structures",
            "content_completed": 8,
            "content_required": 15,
            "content_required_w1w2": 4,
            "content_completed_w1w2": 2,
            "quiz_completed": 2,
            "total_quiz_attempts": 4,
            "discussion_posts_created": 2,
            "discussion_post_replies": 5,
            "discussion_posts_read": 30,
            "num_assignment_submissions": 2,
            "total_time_spent_seconds": 18000,  # 5 hours
            "num_logins": 15,
            "is_optional": False,
        },
        {
            "course_id": "ML301",
            "course_name": "Machine Learning",
            "content_completed": 5,
            "content_required": 10,
            "content_required_w1w2": 3,
            "content_completed_w1w2": 1,
            "quiz_completed": 1,
            "total_quiz_attempts": 2,
            "discussion_posts_created": 1,
            "discussion_post_replies": 2,
            "discussion_posts_read": 15,
            "num_assignment_submissions": 1,
            "total_time_spent_seconds": 7200,  # 2 hours
            "num_logins": 8,
            "is_optional": True,  # Optional course
        },
    ]


@pytest.fixture
def sample_graded_components() -> List[Dict]:
    """Sample graded component data for testing."""
    return [
        {"component_type": "quiz", "score": 85, "max_score": 100, "missed": False},
        {"component_type": "quiz", "score": 92, "max_score": 100, "missed": False},
        {"component_type": "quiz", "score": None, "max_score": 100, "missed": True},  # Missed
        {"component_type": "assignment", "score": 78, "max_score": 100, "missed": False},
        {"component_type": "assignment", "score": 88, "max_score": 100, "missed": False},
    ]


@pytest.fixture
def sample_exam_records() -> List[Dict]:
    """Sample exam record data for testing."""
    return [
        {"course_code": "CS101", "present": True, "marks_obtained": 75, "marks_total": 100, "defaulter_reason": None, "ufm_flagged": False},
        {"course_code": "DS201", "present": True, "marks_obtained": 82, "marks_total": 100, "defaulter_reason": None, "ufm_flagged": False},
        {"course_code": "ML301", "present": False, "marks_obtained": 0, "marks_total": 100, "defaulter_reason": "health_support", "ufm_flagged": False},
    ]


@pytest.fixture
def empty_enrollments() -> List[Dict]:
    """Empty enrollment list for edge case testing."""
    return []


@pytest.fixture
def partial_enrollments() -> List[Dict]:
    """Enrollment with missing fields for robustness testing."""
    return [
        {
            "course_id": "CS101",
            "content_completed": 10,
            # Missing content_required
            "num_logins": 5,
            # Missing other fields
        },
    ]


# =============================================================================
# AcademicFeatureExtractor Tests
# =============================================================================

class TestAcademicFeatureExtractor:
    """Tests for AcademicFeatureExtractor."""

    def test_extract_with_full_data(self, sample_graded_components, sample_exam_records):
        """Academic extractor should return valid features with full data."""
        extractor = AcademicFeatureExtractor()
        features = extractor.extract(sample_graded_components, sample_exam_records)

        assert isinstance(features, AcademicFeatures)
        assert features.graded_quiz_score is not None
        assert features.graded_assignment_score is not None
        assert features.exam_score is not None
        assert features.exam_attendance_rate is not None
        assert isinstance(features.academic_flags, dict)

        # Verify score bounds
        assert 0 <= features.graded_quiz_score <= 100
        assert 0 <= features.graded_assignment_score <= 100
        assert 0 <= features.exam_score <= 100
        assert 0 <= features.exam_attendance_rate <= 100

    def test_extract_with_empty_data(self, empty_enrollments):
        """Academic extractor should handle empty graded components."""
        extractor = AcademicFeatureExtractor()
        features = extractor.extract([], [])

        assert isinstance(features, AcademicFeatures)
        assert features.graded_quiz_score is None
        assert features.graded_assignment_score is None
        assert features.exam_score is None
        assert features.exam_attendance_rate is None

    def test_quiz_score_calculation(self, sample_graded_components):
        """Quiz score should be average of non-missed quizzes."""
        extractor = AcademicFeatureExtractor()
        features = extractor.extract(sample_graded_components, [])

        # Expected: (85 + 92 + 0) / 3 = 59.0 (missed counts as 0)
        assert features.graded_quiz_score is not None
        assert 55 <= features.graded_quiz_score <= 65  # Allow some tolerance

    def test_assignment_score_calculation(self, sample_graded_components):
        """Assignment score should be average of assignment scores."""
        extractor = AcademicFeatureExtractor()
        features = extractor.extract(sample_graded_components, [])

        # Expected: (78 + 88) / 2 = 83.0
        assert features.graded_assignment_score is not None
        assert 80 <= features.graded_assignment_score <= 86

    def test_exam_attendance_rate(self, sample_exam_records):
        """Exam attendance rate should reflect present exams."""
        extractor = AcademicFeatureExtractor()
        features = extractor.extract([], sample_exam_records)

        # 2 out of 3 exams attended = 66.67%
        assert features.exam_attendance_rate is not None
        assert 65 <= features.exam_attendance_rate <= 68

    def test_exam_score_with_absence(self, sample_exam_records):
        """Absent exams should count as 0 in exam score."""
        extractor = AcademicFeatureExtractor()
        features = extractor.extract([], sample_exam_records)

        # (75 + 82 + 0) / 3 = 52.33
        assert features.exam_score is not None
        assert 50 <= features.exam_score <= 55

    def test_academic_flags_ufm_detected(self):
        """UFM flag should be detected when present."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": True, "marks_obtained": 50, "marks_total": 100, "ufm_flagged": True, "defaulter_reason": None},
        ]
        features = extractor.extract([], exam_records)

        assert features.academic_flags["ufm_flagged"] is True

    def test_academic_flags_deferred_detected(self):
        """Deferred flag should be detected when present."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": False, "marks_obtained": 0, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": "deferred"},
        ]
        features = extractor.extract([], exam_records)

        assert features.academic_flags["deferred"] is True

    def test_academic_flags_dropout_intent_detected(self):
        """Dropout intent flag should be detected when present."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": False, "marks_obtained": 0, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": "dropout_intent"},
        ]
        features = extractor.extract([], exam_records)

        assert features.academic_flags["dropout_intent"] is True

    def test_nan_input_handling(self):
        """NaN values should be handled gracefully without crashing."""
        import math
        extractor = AcademicFeatureExtractor()
        graded_components = [
            {"component_type": "quiz", "score": float('nan'), "max_score": 100, "missed": False},
        ]
        # Should not crash - should handle NaN gracefully
        features = extractor.extract(graded_components, [])
        assert isinstance(features, AcademicFeatures)


# =============================================================================
# EngagementFeatureExtractor Tests
# =============================================================================

class TestEngagementFeatureExtractor:
    """Tests for EngagementFeatureExtractor."""

    def test_extract_with_full_data(self, sample_enrollments):
        """Engagement extractor should return valid features with full data."""
        extractor = EngagementFeatureExtractor()
        features = extractor.extract(sample_enrollments, week_number=5)

        assert isinstance(features, EngagementFeatures)
        assert features.content_completion_score is not None
        assert 0 <= features.content_completion_score <= 100
        assert 0 <= features.w1w2_completion_score <= 100
        assert 0 <= features.quiz_engagement_score <= 100
        assert 0 <= features.discussion_engagement_score <= 100
        assert 0 <= features.login_consistency_score <= 100
        assert 0 <= features.time_investment_score <= 100
        assert 0 <= features.assignment_score <= 100
        assert 0 <= features.zero_progress_ratio <= 1
        assert features.progress_category in ["0%", "0-10%", ">10%"]

    def test_extract_with_empty_data(self, empty_enrollments):
        """Engagement extractor should handle empty enrollments."""
        extractor = EngagementFeatureExtractor()
        features = extractor.extract(empty_enrollments, week_number=5)

        assert isinstance(features, EngagementFeatures)
        assert features.content_completion_score is None  # Unknown, not 0
        assert features.w1w2_completion_score == 0.0
        assert features.quiz_engagement_score == 0.0
        assert features.discussion_engagement_score == 0.0
        assert features.login_consistency_score == 0.0
        assert features.time_investment_score == 0.0
        assert features.assignment_score == 0.0
        assert features.zero_progress_ratio == 1.0  # All courses have zero progress
        assert features.progress_category == "0%"

    def test_content_completion_mandatory_only(self, sample_enrollments):
        """Content completion should only consider mandatory courses."""
        extractor = EngagementFeatureExtractor()
        features = extractor.extract(sample_enrollments, week_number=5)

        # Mandatory: CS101 (15/20) + DS201 (8/15) = 23/35 = 65.7%
        # ML301 (optional) should be excluded
        assert features.content_completion_score is not None
        assert 63 <= features.content_completion_score <= 68

    def test_w1w2_completion_calculation(self, sample_enrollments):
        """W1W2 completion should use week-specific fields."""
        extractor = EngagementFeatureExtractor()
        features = extractor.extract(sample_enrollments, week_number=2)

        # W1W2: CS101 (4/5) + DS201 (2/4) + ML301 (1/3) = 7/12 = 58.3%
        assert features.w1w2_completion_score is not None
        assert 55 <= features.w1w2_completion_score <= 62

    def test_week_number_affects_w1w2(self, sample_enrollments):
        """After week 2, W1W2 should use full-term completion."""
        extractor = EngagementFeatureExtractor()

        # Week 2: uses W1W2-specific calculation
        features_week2 = extractor.extract(sample_enrollments, week_number=2)

        # Week 5: uses full-term completion
        features_week5 = extractor.extract(sample_enrollments, week_number=5)

        # Week 5 should use full-term completion rate
        assert features_week5.w1w2_completion_score == (features_week5.content_completion_score or 0)

    def test_self_directed_learning_from_optional(self, sample_enrollments):
        """SDL score should be based on optional course engagement."""
        extractor = EngagementFeatureExtractor()
        features = extractor.extract(sample_enrollments, week_number=5)

        # ML301 is optional with 5/10 = 50% completion
        # Score = 0.5 * 100 * 2.5 = 125, clamped to 100
        assert features.self_directed_learning_score >= 0
        assert features.self_directed_learning_score <= 100

    def test_zero_progress_ratio_calculation(self):
        """Zero progress ratio should count courses with no completion."""
        extractor = EngagementFeatureExtractor()
        enrollments = [
            {"content_completed": 0, "content_required": 10},
            {"content_completed": 5, "content_required": 10},
            {"content_completed": 0, "content_required": 10},
        ]
        features = extractor.extract(enrollments, week_number=5)

        # 2 out of 3 courses have zero progress
        assert features.zero_progress_ratio == pytest.approx(0.6667, rel=0.01)

    def test_progress_category_boundaries(self):
        """Progress category should correctly bucket W1W2 completion."""
        extractor = EngagementFeatureExtractor()

        # 0% completion
        enrollments_zero = [{"content_completed_w1w2": 0, "content_required_w1w2": 10}]
        features_zero = extractor.extract(enrollments_zero, week_number=2)
        assert features_zero.progress_category == "0%"

        # 5% completion (0-10% bucket)
        enrollments_low = [{"content_completed_w1w2": 0.5, "content_required_w1w2": 10}]
        features_low = extractor.extract(enrollments_low, week_number=2)
        assert features_low.progress_category == "0-10%"

        # 15% completion (>10% bucket)
        enrollments_high = [{"content_completed_w1w2": 1.5, "content_required_w1w2": 10}]
        features_high = extractor.extract(enrollments_high, week_number=2)
        assert features_high.progress_category == ">10%"

    def test_per_course_breakdown_structure(self, sample_enrollments):
        """Per-course breakdown should have expected structure."""
        extractor = EngagementFeatureExtractor()
        features = extractor.extract(sample_enrollments, week_number=5)

        assert len(features.per_course_breakdown) == 3
        for course in features.per_course_breakdown:
            assert "course_id" in course
            assert "course_name" in course
            assert "content_completed" in course
            assert "content_required" in course
            assert "completion_pct" in course
            assert "stale_required_count" in course

    def test_partial_data_robustness(self, partial_enrollments):
        """Extractor should handle missing fields gracefully."""
        extractor = EngagementFeatureExtractor()
        features = extractor.extract(partial_enrollments, week_number=5)

        # Should return valid features even with missing data
        assert isinstance(features, EngagementFeatures)
        # content_required missing -> completion should be None or 0
        assert features.content_completion_score is None or features.content_completion_score >= 0


# =============================================================================
# ConsistencyFeatureExtractor Tests
# =============================================================================

class TestConsistencyFeatureExtractor:
    """Tests for ConsistencyFeatureExtractor."""

    def test_extract_with_full_data(self, sample_enrollments):
        """Consistency extractor should return valid features."""
        extractor = ConsistencyFeatureExtractor()
        total_logins = sum(e["num_logins"] for e in sample_enrollments)  # 25 + 15 + 8 = 48
        features = extractor.extract(sample_enrollments, total_logins)

        assert isinstance(features, ConsistencyFeatures)
        assert features.engagement_trend in ["active", "declining", "inactive"]
        assert isinstance(features.is_ghost, bool)
        assert features.ghost_type is None or isinstance(features.ghost_type, str)
        assert features.zero_progress_course_count >= 0
        assert features.total_enrolled_courses == 3
        assert features.total_time_seconds >= 0

    def test_extract_with_empty_data(self, empty_enrollments):
        """Consistency extractor should handle empty enrollments."""
        extractor = ConsistencyFeatureExtractor()
        features = extractor.extract(empty_enrollments, total_login_count=0)

        assert isinstance(features, ConsistencyFeatures)
        assert features.engagement_trend == "inactive"
        assert features.is_ghost is True
        assert features.ghost_type == "never_logged_in"
        assert features.zero_progress_course_count == 0
        assert features.total_enrolled_courses == 0

    def test_ghost_detection_never_logged_in(self):
        """Ghost detection should identify students who never logged in."""
        extractor = ConsistencyFeatureExtractor()
        enrollments = [
            {"content_completed": 0, "total_time_spent": 0},
        ]
        features = extractor.extract(enrollments, total_login_count=0)

        assert features.is_ghost is True
        assert features.ghost_type == "never_logged_in"

    def test_ghost_detection_logged_in_never_started(self):
        """Ghost detection should identify students who logged in but never started."""
        extractor = ConsistencyFeatureExtractor()
        enrollments = [
            {"content_completed": 0, "total_time_spent": 100},  # Some time but no progress
        ]
        features = extractor.extract(enrollments, total_login_count=5)

        assert features.is_ghost is True
        assert features.ghost_type == "logged_in_never_started"

    def test_not_a_ghost_student(self, sample_enrollments):
        """Active student should not be detected as ghost."""
        extractor = ConsistencyFeatureExtractor()
        total_logins = sum(e["num_logins"] for e in sample_enrollments)
        features = extractor.extract(sample_enrollments, total_logins)

        assert features.is_ghost is False
        assert features.ghost_type is None

    def test_engagement_trend_active(self):
        """Active trend should be detected with recent activity."""
        from datetime import datetime, timedelta
        extractor = ConsistencyFeatureExtractor()

        enrollments = [
            {
                "content_completed": 10,
                "last_system_login": (datetime.utcnow() - timedelta(days=5)).isoformat() + "Z",
            },
        ]
        features = extractor.extract(enrollments, total_login_count=20)

        assert features.engagement_trend == "active"

    def test_engagement_trend_inactive(self):
        """Inactive trend should be detected with no recent activity."""
        from datetime import datetime, timedelta
        extractor = ConsistencyFeatureExtractor()

        enrollments = [
            {
                "content_completed": 10,
                "last_system_login": (datetime.utcnow() - timedelta(days=60)).isoformat() + "Z",
            },
        ]
        features = extractor.extract(enrollments, total_login_count=5)

        assert features.engagement_trend == "inactive"


# =============================================================================
# IntentFeatureExtractor Tests
# =============================================================================

class TestIntentFeatureExtractor:
    """Tests for IntentFeatureExtractor."""

    def test_extract_on_track_profile(self):
        """On-track student should be classified correctly."""
        extractor = IntentFeatureExtractor()
        features = extractor.extract(
            content_completion_score=80.0,
            login_consistency_score=85.0,
            time_investment_score=75.0,
            graded_quiz_score=82.0,
            risk_score=20.0,
            total_login_count=50,
            total_time_seconds=50000,
        )

        assert isinstance(features, IntentFeatures)
        assert features.engagement_pattern == "on_track"

    def test_extract_disengaged_profile(self):
        """Disengaged student should be classified correctly."""
        extractor = IntentFeatureExtractor()
        features = extractor.extract(
            content_completion_score=5.0,
            login_consistency_score=10.0,
            time_investment_score=5.0,
            graded_quiz_score=None,
            risk_score=80.0,
            total_login_count=2,
            total_time_seconds=500,
        )

        assert features.engagement_pattern == "disengaged"

    def test_extract_struggling_profile(self):
        """Struggling student (trying but failing) should be classified correctly."""
        extractor = IntentFeatureExtractor()
        features = extractor.extract(
            content_completion_score=15.0,
            login_consistency_score=90.0,  # High login
            time_investment_score=85.0,  # High time
            graded_quiz_score=45.0,  # Low quiz score
            risk_score=65.0,
            total_login_count=100,  # Very high login count
            total_time_seconds=10000,  # Significant time
        )

        assert features.engagement_pattern == "struggling"

    def test_extract_at_risk_normal_profile(self):
        """At-risk but normal pattern should be classified correctly."""
        extractor = IntentFeatureExtractor()
        features = extractor.extract(
            content_completion_score=50.0,
            login_consistency_score=60.0,
            time_investment_score=55.0,
            graded_quiz_score=55.0,
            risk_score=50.0,  # Elevated risk
            total_login_count=30,
            total_time_seconds=20000,
        )

        assert features.engagement_pattern == "at_risk_normal"


# =============================================================================
# FeatureEngineer Composer Tests
# =============================================================================

class TestFeatureEngineerComposer:
    """Tests for the FeatureEngineer composer."""

    def test_composer_assembles_all_features(self, sample_graded_components, sample_exam_records):
        """Composer should assemble features from all extractors."""
        # Mock the fetch methods
        engineer = FeatureEngineer()

        # Test _assemble_features directly
        academic = AcademicFeatures(
            graded_quiz_score=80.0,
            graded_assignment_score=85.0,
            exam_score=75.0,
            exam_attendance_rate=90.0,
            academic_flags={"ufm_flagged": False, "deferred": False},
        )
        engagement = EngagementFeatures(
            content_completion_score=70.0,
            w1w2_completion_score=60.0,
            quiz_engagement_score=75.0,
            discussion_engagement_score=65.0,
            login_consistency_score=80.0,
            time_investment_score=70.0,
            assignment_score=60.0,
            zero_progress_ratio=0.2,
            progress_category=">10%",
            self_directed_learning_score=50.0,
        )
        consistency = ConsistencyFeatures(
            engagement_trend="active",
            is_ghost=False,
            ghost_type=None,
            zero_progress_course_count=0,
            total_enrolled_courses=3,
            total_time_seconds=50000,
        )
        intent = IntentFeatures(engagement_pattern="on_track")

        features = engineer._assemble_features(academic, engagement, consistency, intent)

        # Verify all features are present
        assert features["graded_quiz_score"] == 80.0
        assert features["content_completion_score"] == 70.0
        assert features["engagement_trend"] == "active"
        assert features["engagement_pattern"] == "on_track"
        assert features["total_courses"] == 3

    def test_new_student_tolerance_applied(self):
        """New student tolerance should boost scores for weeks 1-3."""
        engineer = FeatureEngineer()

        features = {
            "content_completion_score": 50.0,
            "login_consistency_score": 60.0,
            "quiz_engagement_score": 70.0,  # Should not be boosted
        }

        boosted = engineer._apply_new_student_tolerance(features)

        # 20% boost applied
        assert boosted["content_completion_score"] == 60.0  # 50 * 1.2
        assert boosted["login_consistency_score"] == 72.0  # 60 * 1.2
        assert boosted["quiz_engagement_score"] == 70.0  # Unchanged

    def test_new_student_tolerance_clamped_at_100(self):
        """Boosted scores should be clamped at 100."""
        engineer = FeatureEngineer()

        features = {
            "content_completion_score": 90.0,
            "login_consistency_score": 95.0,
        }

        boosted = engineer._apply_new_student_tolerance(features)

        # Clamped at 100
        assert boosted["content_completion_score"] == 100.0  # 90 * 1.2 = 108 -> 100
        assert boosted["login_consistency_score"] == 100.0  # 95 * 1.2 = 114 -> 100


# =============================================================================
# Integration Tests
# =============================================================================

class TestFeatureExtractionIntegration:
    """Integration tests for the full feature extraction pipeline."""

    def test_full_pipeline_with_sample_data(self, sample_enrollments, sample_graded_components, sample_exam_records):
        """Full feature extraction pipeline should produce valid output."""
        from backend.services.feature_engineering import FeatureEngineer as LegacyFeatureEngineer

        features = LegacyFeatureEngineer.calculate_all_features(
            sample_enrollments,
            graded_components=sample_graded_components,
            exam_records=sample_exam_records,
            is_new_student=False,
            week_number=5,
        )

        # Verify all expected keys are present
        expected_keys = [
            "content_completion_score", "w1w2_completion_score",
            "quiz_engagement_score", "discussion_engagement_score",
            "login_consistency_score", "time_investment_score",
            "assignment_score", "graded_quiz_score", "graded_assignment_score",
            "exam_score", "exam_attendance_rate",
            "zero_progress_ratio", "progress_category", "engagement_trend",
            "per_course_breakdown", "engagement_pattern", "ghost_info",
        ]

        for key in expected_keys:
            assert key in features, f"Missing expected key: {key}"

        # Verify score bounds
        score_fields = [
            "content_completion_score", "w1w2_completion_score",
            "quiz_engagement_score", "discussion_engagement_score",
            "login_consistency_score", "time_investment_score",
            "assignment_score",
        ]

        for field in score_fields:
            value = features.get(field)
            if value is not None:
                assert 0 <= value <= 100, f"{field} out of bounds: {value}"

    def test_empty_data_pipeline(self, empty_enrollments):
        """Pipeline should handle empty data without crashing."""
        from backend.services.feature_engineering import FeatureEngineer as LegacyFeatureEngineer

        features = LegacyFeatureEngineer.calculate_all_features(
            empty_enrollments,
            graded_components=[],
            exam_records=[],
            is_new_student=False,
            week_number=5,
        )

        # Should return valid feature dict
        assert isinstance(features, dict)
        assert features["engagement_pattern"] in ["disengaged", "struggling", "at_risk_normal", "on_track"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
