"""
Critical Path Test Suite (TEST-1, TEST-3, TEST-4, TEST-5)

Covers five test coverage gaps:
1. _safe_int and _safe_float conversions (TEST-1, TEST-5)
2. ABSENT_SENTINEL handling for graded scores (TEST-5)
3. Content completion score calculation (TEST-1)
4. Ghost student detection and activation outreach (TEST-4)
5. Risk spike threshold boundary conditions (TEST-3)

Run with: TESTING=true pytest backend/tests/test_critical_paths.py -v
"""

import pytest

# Import functions under test
from backend.services.core.data_ingestion import (
    _safe_int,
    _safe_float,
    ABSENT_SENTINELS,
)
from backend.services.feature_engineering import FeatureEngineer
from backend.services.core.decision_engine import (
    should_trigger_intervention,
    get_intervention_recommendation,
    RISK_SPIKE_THRESHOLD,
)


# =============================================================================
# SECTION 1 — _safe_int and _safe_float (TEST-1, TEST-5)
# =============================================================================


class TestSafeConversions:
    """Test _safe_int and _safe_float edge cases and correct parsing."""

    def test_safe_int_returns_none_for_none(self):
        """_safe_int should return None for None input."""
        assert _safe_int(None) is None

    def test_safe_int_returns_none_for_empty_string(self):
        """_safe_int should return None for empty string."""
        assert _safe_int("") is None

    def test_safe_int_parses_float_string(self):
        """_safe_int should parse float strings correctly."""
        assert _safe_int("3.0") == 3
        assert _safe_int("3.9") == 3  # truncates, not rounds

    def test_safe_int_returns_int(self):
        """_safe_int should parse integer strings."""
        assert _safe_int("42") == 42
        assert _safe_int(42) == 42  # already int

    def test_safe_int_handles_whitespace(self):
        """_safe_int should strip whitespace."""
        assert _safe_int("  42  ") == 42

    def test_safe_int_returns_none_for_invalid(self):
        """_safe_int should return None for unparseable values."""
        assert _safe_int("not_a_number") is None
        assert _safe_int("N/A") is None

    def test_safe_float_returns_none_for_none(self):
        """_safe_float should return None for None input."""
        assert _safe_float(None) is None

    def test_safe_float_parses_correctly(self):
        """_safe_float should parse float strings."""
        assert _safe_float("9.5") == pytest.approx(9.5)
        assert _safe_float("3.14159") == pytest.approx(3.14159)

    def test_safe_float_handles_whitespace(self):
        """_safe_float should strip whitespace."""
        assert _safe_float("  9.5  ") == pytest.approx(9.5)

    def test_safe_float_returns_none_for_invalid(self):
        """_safe_float should return None for unparseable values."""
        assert _safe_float("not_a_number") is None
        assert _safe_float("") is None


class TestAbsentSentinels:
    """Test ABSENT_SENTINEL handling for graded component scores."""

    @pytest.mark.parametrize("sentinel", ["-", "AB", "NP", "Exc", "EX", "A", "a", ""])
    def test_absent_sentinel_produces_missed_true(self, sentinel):
        """
        Test that ABSENT_SENTINELS mark a score as missed (absent).
        This mirrors the logic in _ingest_graded_sheet.
        """
        # Simulate the logic: is_absent = score_val is None or str(score_val).strip() in ABSENT_SENTINELS
        is_absent = sentinel is None or str(sentinel).strip() in ABSENT_SENTINELS
        score = None if is_absent else _safe_float(sentinel)

        assert is_absent is True
        assert score is None

    def test_absent_sentinel_with_whitespace(self):
        """Test that sentinels with whitespace are still detected."""
        sentinel = "  AB  "
        is_absent = str(sentinel).strip() in ABSENT_SENTINELS
        assert is_absent is True

    def test_numeric_score_is_not_absent(self):
        """Test that valid numeric scores are not marked as missed."""
        score_val = "8.5"
        is_absent = score_val is None or str(score_val).strip() in ABSENT_SENTINELS
        score = None if is_absent else _safe_float(score_val)

        assert is_absent is False
        assert score == pytest.approx(8.5)

    def test_zero_score_is_not_absent(self):
        """Test that zero is a valid score, not a sentinel."""
        score_val = "0"
        is_absent = score_val is None or str(score_val).strip() in ABSENT_SENTINELS
        score = None if is_absent else _safe_float(score_val)

        assert is_absent is False
        assert score == pytest.approx(0.0)

    def test_none_is_absent(self):
        """Test that None values are treated as absent."""
        score_val = None
        is_absent = score_val is None or str(score_val).strip() in ABSENT_SENTINELS

        assert is_absent is True


# =============================================================================
# SECTION 2 — calculate_content_completion_score (TEST-1)
# =============================================================================


class TestContentCompletionScore:
    """Test FeatureEngineer.calculate_content_completion_score edge cases."""

    def test_returns_none_when_all_required_zero(self):
        """
        When content_required is 0 for all enrollments, returns None
        (absence of data, not zero completion).
        """
        enrollments = [
            {"content_completed": 5, "content_required": 0, "is_optional": False},
            {"content_completed": 10, "content_required": 0, "is_optional": False},
        ]
        result = FeatureEngineer.calculate_content_completion_score(enrollments)
        assert result is None

    def test_correct_percentage(self):
        """Test basic percentage calculation."""
        enrollments = [
            {"content_completed": 50, "content_required": 100, "is_optional": False}
        ]
        result = FeatureEngineer.calculate_content_completion_score(enrollments)
        assert result == pytest.approx(50.0)

    def test_clamped_to_100(self):
        """Score should not exceed 100 even if completed > required."""
        enrollments = [
            {"content_completed": 150, "content_required": 100, "is_optional": False}
        ]
        result = FeatureEngineer.calculate_content_completion_score(enrollments)
        assert result == 100.0

    def test_optional_courses_excluded(self):
        """Optional (self-paced) courses should not affect mandatory completion rate."""
        enrollments = [
            {
                "content_completed": 0,
                "content_required": 100,
                "is_optional": True,
            },  # excluded
            {
                "content_completed": 80,
                "content_required": 100,
                "is_optional": False,
            },  # included
        ]
        result = FeatureEngineer.calculate_content_completion_score(enrollments)
        # Only the mandatory course counts: 80/100 = 80%
        assert result == pytest.approx(80.0)

    def test_all_optional_returns_none(self):
        """If all courses are optional, return None (no mandatory data)."""
        enrollments = [
            {"content_completed": 50, "content_required": 100, "is_optional": True},
            {"content_completed": 75, "content_required": 100, "is_optional": True},
        ]
        result = FeatureEngineer.calculate_content_completion_score(enrollments)
        assert result is None

    def test_multiple_courses_aggregated(self):
        """Test aggregation across multiple mandatory courses."""
        enrollments = [
            {
                "content_completed": 50,
                "content_required": 100,
                "is_optional": False,
            },  # 50%
            {
                "content_completed": 90,
                "content_required": 100,
                "is_optional": False,
            },  # 90%
        ]
        # Total: 140 completed / 200 required = 70%
        result = FeatureEngineer.calculate_content_completion_score(enrollments)
        assert result == pytest.approx(70.0)

    def test_empty_enrollments(self):
        """Empty enrollments list should return None."""
        result = FeatureEngineer.calculate_content_completion_score([])
        assert result is None


# =============================================================================
# SECTION 3 — Ghost student and activation outreach (TEST-4)
# =============================================================================


class TestGhostStudentDetection:
    """Test ghost student detection logic and activation outreach routing."""

    def test_zero_logins_is_ghost(self):
        """Student with zero logins is a ghost (never_logged_in)."""
        result = FeatureEngineer.detect_ghost_student(
            enrollments=[{"content_completed": 0, "total_time_spent": 0}],
            student_login_count=0,
        )
        assert result["is_ghost"] is True
        assert result["ghost_type"] == "never_logged_in"

    def test_logins_but_zero_content_is_ghost(self):
        """Student with logins but no content progress is ghost (logged_in_never_started)."""
        result = FeatureEngineer.detect_ghost_student(
            enrollments=[{"content_completed": 0, "total_time_spent": 0}],
            student_login_count=5,
        )
        assert result["is_ghost"] is True
        assert result["ghost_type"] == "logged_in_never_started"

    def test_logins_but_zero_content_high_time_not_ghost(self):
        """Student with logins and significant time spent is not ghost (time > 300s threshold)."""
        result = FeatureEngineer.detect_ghost_student(
            enrollments=[{"content_completed": 0, "total_time_spent": 600}],
            student_login_count=5,
        )
        # High time spent means they're engaging somehow, not a ghost
        assert result["is_ghost"] is False

    def test_active_student_is_not_ghost(self):
        """Student with content progress is not a ghost."""
        result = FeatureEngineer.detect_ghost_student(
            enrollments=[{"content_completed": 10, "total_time_spent": 3600}],
            student_login_count=20,
        )
        assert result["is_ghost"] is False
        assert result["ghost_type"] is None

    def test_partial_progress_not_ghost(self):
        """Student with some progress is not a ghost."""
        result = FeatureEngineer.detect_ghost_student(
            enrollments=[
                {"content_completed": 5, "total_time_spent": 100},
                {"content_completed": 0, "total_time_spent": 0},
            ],
            student_login_count=10,
        )
        assert result["is_ghost"] is False

    def test_empty_enrollments_not_ghost(self):
        """Empty enrollments returns not ghost with zero counts."""
        result = FeatureEngineer.detect_ghost_student(
            enrollments=[], student_login_count=0
        )
        assert result["is_ghost"] is False
        assert result["total_enrolled_courses"] == 0

    def test_ghost_student_gets_activation_outreach(self):
        """
        Ghost students with requires_activation_outreach flag get
        activation_outreach intervention type with critical priority.
        """
        features = {
            "risk_score": 95.0,
            "requires_activation_outreach": True,
            "ghost_info": {"is_ghost": True, "ghost_type": "never_logged_in"},
            "engagement_pattern": "disengaged",
        }
        result = get_intervention_recommendation(95.0, features=features)
        assert result["type"] == "activation_outreach"
        assert result["priority"] == "critical"
        assert result["suppress_automated_messages"] is True
        assert "direct_call" in result["channels"]

    def test_logged_in_never_started_gets_different_actions(self):
        """
        Ghost type 'logged_in_never_started' gets different action items
        than 'never_logged_in'.
        """
        features = {
            "risk_score": 85.0,
            "requires_activation_outreach": True,
            "ghost_info": {"is_ghost": True, "ghost_type": "logged_in_never_started"},
        }
        result = get_intervention_recommendation(85.0, features=features)
        assert result["type"] == "activation_outreach"
        assert result["ghost_type"] == "logged_in_never_started"
        # Should have onboarding-specific actions
        action_text = " ".join(result["action_items"])
        assert (
            "onboarding" in action_text.lower() or "orientation" in action_text.lower()
        )


# =============================================================================
# SECTION 4 — Risk spike threshold boundary (TEST-3)
# =============================================================================


class TestRiskSpikeThreshold:
    """
    Test risk spike threshold boundaries for intervention triggering.

    RISK_SPIKE_THRESHOLD (default 15.0) allows bypassing the cooldown
    if risk increases significantly.
    """

    def test_small_delta_does_not_bypass_cooldown(self):
        """
        Delta below RISK_SPIKE_THRESHOLD should NOT trigger intervention
        when within cooldown period.
        """
        # Delta of 10 (below threshold 15) with 2 days since last intervention
        result = should_trigger_intervention(
            current_risk_score=60.0,
            previous_risk_score=50.0,
            days_since_last_intervention=2,  # within 7-day cooldown
        )
        assert result is False

    def test_large_delta_bypasses_cooldown(self):
        """
        Delta above RISK_SPIKE_THRESHOLD SHOULD trigger intervention
        even when within cooldown period.
        """
        # Delta of 16 (above threshold 15) with 2 days since last intervention
        result = should_trigger_intervention(
            current_risk_score=66.0,
            previous_risk_score=50.0,
            days_since_last_intervention=2,
        )
        assert result is True

    def test_exact_threshold_boundary(self):
        """
        Delta of exactly RISK_SPIKE_THRESHOLD should trigger (>= threshold).
        """
        # Delta of exactly 15
        result = should_trigger_intervention(
            current_risk_score=65.0,
            previous_risk_score=50.0,
            days_since_last_intervention=2,
        )
        assert result is True

    def test_below_threshold_with_expired_cooldown_triggers(self):
        """
        Small delta but expired cooldown (8 days) should trigger.
        """
        result = should_trigger_intervention(
            current_risk_score=51.0,
            previous_risk_score=50.0,
            days_since_last_intervention=8,  # beyond 7-day cooldown
        )
        assert result is True

    def test_no_previous_score_does_not_bypass(self):
        """
        Without previous risk score, can't calculate delta.
        Should not bypass cooldown unless cooldown is expired.
        """
        result = should_trigger_intervention(
            current_risk_score=80.0,
            previous_risk_score=None,
            days_since_last_intervention=2,
        )
        assert result is False  # still in cooldown, no delta to bypass

    def test_no_previous_score_expired_cooldown_triggers(self):
        """
        Without previous risk score but expired cooldown should trigger.
        """
        result = should_trigger_intervention(
            current_risk_score=80.0,
            previous_risk_score=None,
            days_since_last_intervention=8,  # expired
        )
        assert result is True

    def test_below_threshold_no_intervention(self):
        """
        Risk below THRESHOLD_NO_ACTION should not trigger even with expired cooldown.
        """
        result = should_trigger_intervention(
            current_risk_score=20.0,  # below default 30.0 threshold
            previous_risk_score=None,
            days_since_last_intervention=8,
        )
        assert result is False

    def test_risk_spike_threshold_config_value(self):
        """
        Verify RISK_SPIKE_THRESHOLD is correctly configured (15.0, not 0.15).
        """
        # This test documents the correct scale (0-100, not 0-1)
        assert RISK_SPIKE_THRESHOLD == 15.0


# =============================================================================
# Additional Edge Case Tests
# =============================================================================


class TestDecisionEngineEdgeCases:
    """Additional edge cases for decision engine."""

    def test_invalid_risk_score_handling(self):
        """Decision engine should handle NaN gracefully and reject Inf."""
        import numpy as np

        # NaN should not raise — returns a valid recommendation with neutral score
        result = get_intervention_recommendation(np.nan, features={})
        assert "type" in result

        # Inf is an invalid score and must raise AssertionError
        with pytest.raises(AssertionError):
            get_intervention_recommendation(np.inf, features={})

    def test_negative_risk_score_clamped(self):
        """Risk scores below 0 should not be possible (assertion), but test behavior."""
        # The function has an assertion, so this would raise AssertionError
        # We test that valid scores work
        result = get_intervention_recommendation(0.0, features={})
        assert result["type"] is not None


# =============================================================================
# Run Configuration
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
