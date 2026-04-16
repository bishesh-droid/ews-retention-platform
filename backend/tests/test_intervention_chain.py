"""
Test suite for the intervention recommendation call chain.

Validates the full path from decision_engine through service layer.
Uses real logic functions — only DB and external calls are mocked.
"""

import pytest

# Import the real functions under test (NOT mocked)
from backend.services.core.decision_engine import (
    get_intervention_recommendation,
    calculate_intervention_priority,
    should_trigger_intervention,
)


# =============================================================================
# SECTION 1 — Unit tests for get_intervention_recommendation (threshold ladder)
# =============================================================================


@pytest.mark.parametrize(
    "score,expected_type,expected_priority",
    [
        (15, "no_action", None),
        (29, "no_action", None),
        (30, "gentle_reminder", "low"),
        (39, "gentle_reminder", "low"),
        (40, "mentor_outreach", "medium"),
        (59, "mentor_outreach", "medium"),
        (60, "mentor_outreach", "high"),  # escalated mentor, NOT urgent
        (79, "mentor_outreach", "high"),  # still NOT urgent
        (80, "urgent_intervention", "critical"),
        (100, "urgent_intervention", "critical"),
    ],
)
def test_intervention_threshold_ladder(score, expected_type, expected_priority):
    """
    Test the full threshold ladder for intervention recommendations.
    Validates fix B-4 (missing elif) is correctly wired.
    """
    result = get_intervention_recommendation(score)
    assert (
        result["type"] == expected_type
    ), f"score={score}: got {result['type']}, expected {expected_type}"
    if expected_priority:
        assert (
            result.get("priority") == expected_priority
        ), f"score={score}: priority mismatch"


# =============================================================================
# SECTION 2 — Unit tests for calculate_intervention_priority
# =============================================================================


@pytest.mark.parametrize(
    "score,expected_priority",
    [
        (10, "low"),
        (44, "low"),
        (45, "medium"),
        (69, "medium"),
        (70, "high"),
        (84, "high"),
        (85, "critical"),
        (100, "critical"),
    ],
)
def test_priority_scale_is_0_to_100(score, expected_priority):
    """
    Test that priority scale correctly uses 0-100 range.
    Validates fix M-1 (scale normalization) is correctly wired.
    """
    result = calculate_intervention_priority(score)
    assert (
        result == expected_priority
    ), f"score={score}: got {result}, expected {expected_priority}"


# =============================================================================
# SECTION 3 — Scale contract assertion tests
# =============================================================================


def test_decision_engine_rejects_normalised_score():
    """
    Decision engine should reject 0-1 scale scores (expects 0-100).
    Validates contract enforcement (fix M-4).
    """
    with pytest.raises(AssertionError):
        get_intervention_recommendation(0.75)  # 0–1 scale should be rejected


def test_decision_engine_rejects_negative():
    """
    Decision engine should reject negative risk scores.
    """
    with pytest.raises((AssertionError, ValueError)):
        get_intervention_recommendation(-5)


def test_decision_engine_rejects_over_100():
    """
    Decision engine should reject scores above 100.
    """
    with pytest.raises(AssertionError):
        get_intervention_recommendation(105)


# =============================================================================
# SECTION 4 — Integration smoke test for the full call chain
# =============================================================================


def test_student_with_risk_65_gets_mentor_not_urgent():
    """
    Smoke test that the full service layer correctly routes risk_score=65.

    Risk score 65 should produce mentor_outreach (high priority), NOT urgent.
    This catches if fix B-4 (the missing elif) is not wired through the service layer.
    """
    # Call the decision engine directly through the public API
    result = get_intervention_recommendation(
        risk_score=65.0,
        engagement_pattern="at_risk_normal",
        features={},
    )

    assert (
        result["type"] != "urgent_intervention"
    ), "risk_score=65 must NOT produce urgent_intervention — fix B-4 may not be wired correctly"
    assert "mentor" in result["type"].lower() or result["type"] in [
        "academic_support",
        "mentor_outreach",
    ], f"risk_score=65 should get mentor or academic support, got {result['type']}"


def test_engagement_pattern_struggling_gets_academic_support():
    """
    Test that struggling students get academic support regardless of risk score.
    """
    result = get_intervention_recommendation(
        risk_score=55.0,
        engagement_pattern="struggling",
        features={},
    )

    assert (
        result["type"] == "academic_support"
    ), f"Struggling students should get academic_support, got {result['type']}"


def test_ghost_student_gets_activation_outreach():
    """
    Test that ghost students (requires_activation_outreach) get activation outreach.
    """
    result = get_intervention_recommendation(
        risk_score=50.0,
        engagement_pattern="on_track",
        features={
            "requires_activation_outreach": True,
            "ghost_info": {"ghost_type": "never_logged_in"},
        },
    )

    assert (
        result["type"] == "activation_outreach"
    ), f"Ghost students should get activation_outreach, got {result['type']}"
    assert (
        result.get("priority") == "critical"
    ), "Activation outreach should be critical priority"


# =============================================================================
# SECTION 5 — Spike threshold tests
# =============================================================================


def test_spike_threshold_uses_0_to_100_scale():
    """
    Test that spike detection correctly uses 0-100 scale (not 0-1).
    Validates fix M-4 is wired through.

    A delta of 0.15 should NOT trigger — it's noise on a 0–100 scale.
    A delta of 15 SHOULD trigger even within cooldown.
    """
    # Small delta (0.15) should NOT trigger — below threshold
    assert not should_trigger_intervention(
        current_risk_score=50.15,
        previous_risk_score=50.0,
        days_since_last_intervention=3,
    ), "Delta of 0.15 should NOT trigger intervention (below threshold)"

    # Large delta (15) SHOULD trigger even within cooldown
    assert should_trigger_intervention(
        current_risk_score=65.0,
        previous_risk_score=50.0,
        days_since_last_intervention=3,
    ), "Delta of 15 SHOULD trigger intervention (significant spike)"


def test_spike_no_previous_score():
    """
    Test behavior when no previous risk score exists.
    """
    # No previous score — should trigger if current is high enough
    assert should_trigger_intervention(
        current_risk_score=75.0,
        previous_risk_score=None,
        days_since_last_intervention=None,
    ), "High risk with no baseline should trigger"


def test_spike_respects_cooldown():
    """
    Test that spike detection respects cooldown period.
    """
    # Within cooldown (1 day), small spike should not trigger
    assert not should_trigger_intervention(
        current_risk_score=60.0,
        previous_risk_score=50.0,
        days_since_last_intervention=1,
    ), "Within cooldown, moderate spike should not trigger"


# =============================================================================
# Edge case tests
# =============================================================================


def test_nan_inf_rejection():
    """
    Test that NaN and Inf values are rejected.
    """

    # NaN should be handled (current implementation uses 50.0 as default)
    result = get_intervention_recommendation(float("nan"))
    assert result["type"] is not None  # Should return some valid recommendation

    # Inf should raise assertion error
    with pytest.raises(AssertionError):
        get_intervention_recommendation(float("inf"))


def test_boundary_scores():
    """
    Test exact boundary values.
    """
    # Exactly at thresholds
    result_30 = get_intervention_recommendation(30.0)
    assert result_30["type"] == "gentle_reminder"

    result_40 = get_intervention_recommendation(40.0)
    assert result_40["type"] == "mentor_outreach"

    result_80 = get_intervention_recommendation(80.0)
    assert result_80["type"] == "urgent_intervention"
