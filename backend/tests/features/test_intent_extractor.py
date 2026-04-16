"""
Test for IntentFeatureExtractor.

Comprehensive tests for:
- Engagement pattern classification
- Disengaged vs struggling distinction
- Risk score integration
- Edge cases in classification rules
"""

from backend.services.features.intent import IntentFeatureExtractor, IntentFeatures


class TestIntentFeatureExtractor:
    """Tests for intent/motivation feature extraction."""

    def test_extract_classifies_pattern(self):
        """Should return IntentFeatures with engagement_pattern set."""
        extractor = IntentFeatureExtractor()
        result = extractor.extract(
            content_completion_score=50.0,
            login_consistency_score=50.0,
            time_investment_score=50.0,
            graded_quiz_score=60.0,
            risk_score=30.0,
            total_login_count=50,
            total_time_seconds=3600,
        )

        assert isinstance(result, IntentFeatures)
        assert result.engagement_pattern in [
            "disengaged",
            "struggling",
            "at_risk_normal",
            "on_track",
        ]

    def test_classify_disengaged_low_login_low_completion(self):
        """Should classify as 'disengaged' with <5 logins and <5% completion."""
        extractor = IntentFeatureExtractor()

        # Low logins (<5) and low completion (<5%)
        result = extractor.extract(
            content_completion_score=3.0,  # 3% completion
            login_consistency_score=50.0,
            time_investment_score=50.0,
            graded_quiz_score=60.0,
            risk_score=30.0,
            total_login_count=3,  # < 5 logins
            total_time_seconds=3600,
        )

        assert result.engagement_pattern == "disengaged"

    def test_classify_struggling_high_login_low_completion(self):
        """Should classify as 'struggling' with high login but low completion + poor quiz."""
        extractor = IntentFeatureExtractor()

        # High logins (>80), low completion (<20%), significant time, poor quiz
        result = extractor.extract(
            content_completion_score=15.0,  # 15% completion
            login_consistency_score=90.0,
            time_investment_score=85.0,
            graded_quiz_score=45.0,  # Poor quiz score (< 55)
            risk_score=50.0,
            total_login_count=100,  # > 80 logins
            total_time_seconds=10000,  # > 7200 seconds
        )

        assert result.engagement_pattern == "struggling"

    def test_classify_struggling_with_none_quiz(self):
        """Should classify as 'struggling' with None quiz score."""
        extractor = IntentFeatureExtractor()

        # High logins, low completion, significant time, None quiz (treated as < 55)
        result = extractor.extract(
            content_completion_score=10.0,
            login_consistency_score=90.0,
            time_investment_score=85.0,
            graded_quiz_score=None,  # None counts as failed
            risk_score=50.0,
            total_login_count=90,
            total_time_seconds=8000,
        )

        assert result.engagement_pattern == "struggling"

    def test_classify_at_risk_normal(self):
        """Should classify as 'at_risk_normal' when risk >= 40 but not disengaged/struggling."""
        extractor = IntentFeatureExtractor()

        # Risk >= 40 but not meeting disengaged/struggling criteria
        result = extractor.extract(
            content_completion_score=50.0,
            login_consistency_score=60.0,
            time_investment_score=55.0,
            graded_quiz_score=70.0,
            risk_score=45.0,  # >= 40 risk
            total_login_count=30,  # Not low enough for disengaged
            total_time_seconds=5000,
        )

        assert result.engagement_pattern == "at_risk_normal"

    def test_classify_on_track(self):
        """Should classify as 'on_track' for healthy engagement patterns."""
        extractor = IntentFeatureExtractor()

        # Healthy engagement pattern
        result = extractor.extract(
            content_completion_score=80.0,
            login_consistency_score=85.0,
            time_investment_score=75.0,
            graded_quiz_score=82.0,
            risk_score=20.0,  # Low risk (< 40)
            total_login_count=50,
            total_time_seconds=50000,
        )

        assert result.engagement_pattern == "on_track"

    def test_classify_on_track_boundary_risk(self):
        """Should classify as 'on_track' when risk is exactly at boundary (39)."""
        extractor = IntentFeatureExtractor()

        result = extractor.extract(
            content_completion_score=60.0,
            login_consistency_score=70.0,
            time_investment_score=65.0,
            graded_quiz_score=65.0,
            risk_score=39.0,  # Just below 40 threshold
            total_login_count=50,
            total_time_seconds=20000,
        )

        assert result.engagement_pattern == "on_track"

    def test_null_quiz_score_handling(self):
        """Should handle None quiz score in struggling classification."""
        extractor = IntentFeatureExtractor()

        # Verify None quiz score is treated as < 55
        result = extractor.extract(
            content_completion_score=15.0,
            login_consistency_score=90.0,
            time_investment_score=85.0,
            graded_quiz_score=None,
            risk_score=50.0,
            total_login_count=100,
            total_time_seconds=10000,
        )

        assert result.engagement_pattern == "struggling"

    def test_boundary_conditions_login_exactly_5(self):
        """Should handle boundary value: exactly 5 logins."""
        extractor = IntentFeatureExtractor()

        # Exactly 5 logins, < 5% completion - should NOT be disengaged (login >= 5)
        result = extractor.extract(
            content_completion_score=3.0,
            login_consistency_score=50.0,
            time_investment_score=50.0,
            graded_quiz_score=60.0,
            risk_score=30.0,
            total_login_count=5,  # Exactly at threshold
            total_time_seconds=3600,
        )

        # Should NOT be disengaged because login_count is not < 5
        assert result.engagement_pattern != "disengaged"

    def test_boundary_conditions_completion_exactly_5_percent(self):
        """Should handle boundary value: exactly 5% completion."""
        extractor = IntentFeatureExtractor()

        # < 5 logins, exactly 5% completion - should NOT be disengaged (rate >= 0.05)
        result = extractor.extract(
            content_completion_score=5.0,  # Exactly 5% (0.05 rate)
            login_consistency_score=50.0,
            time_investment_score=50.0,
            graded_quiz_score=60.0,
            risk_score=30.0,
            total_login_count=3,  # < 5 logins
            total_time_seconds=3600,
        )

        # Should NOT be disengaged because completion_rate is not < 0.05
        assert result.engagement_pattern != "disengaged"

    def test_struggling_boundary_login_80(self):
        """Should handle boundary: exactly 80 logins (not struggling)."""
        extractor = IntentFeatureExtractor()

        # Exactly 80 logins - should NOT meet struggling criterion (login > 80 required)
        result = extractor.extract(
            content_completion_score=15.0,
            login_consistency_score=90.0,
            time_investment_score=85.0,
            graded_quiz_score=45.0,
            risk_score=50.0,
            total_login_count=80,  # Exactly 80, not > 80
            total_time_seconds=10000,
        )

        # Should NOT be struggling because login_count is not > 80
        # But it has risk >= 40, so should be at_risk_normal
        assert result.engagement_pattern == "at_risk_normal"

    def test_struggling_boundary_completion_20_percent(self):
        """Should handle boundary: exactly 20% completion (not struggling)."""
        extractor = IntentFeatureExtractor()

        # Exactly 20% completion - should NOT meet struggling criterion (rate < 0.20 required)
        result = extractor.extract(
            content_completion_score=20.0,  # Exactly 20%
            login_consistency_score=90.0,
            time_investment_score=85.0,
            graded_quiz_score=45.0,
            risk_score=50.0,
            total_login_count=100,
            total_time_seconds=10000,
        )

        # Should NOT be struggling because completion_rate is not < 0.20
        assert result.engagement_pattern != "struggling"
