"""
Unit tests for risk score validation utilities
"""

from backend.ml.utils.validation_utils import (
    validate_and_clamp_probability,
    validate_student_features,
    sanitize_student_features,
    validate_risk_score_dict,
    sanitize_risk_score_dict,
    get_safe_default_prediction,
    validate_student_data,
)
import sys
import os
import numpy as np
import pandas as pd

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestValidateAndClampProbability:
    """Test probability validation and clamping"""

    def test_valid_probability(self):
        """Valid probabilities should pass through unchanged"""
        assert validate_and_clamp_probability(0.5) == 0.5
        assert validate_and_clamp_probability(0.0) == 0.0
        assert validate_and_clamp_probability(1.0) == 1.0
        assert validate_and_clamp_probability(0.75) == 0.75

    def test_negative_probability_clamped(self):
        """Negative values should be clamped to 0.0"""
        assert validate_and_clamp_probability(-0.1) == 0.0
        assert validate_and_clamp_probability(-1.0) == 0.0
        assert validate_and_clamp_probability(-100) == 0.0

    def test_too_large_probability_clamped(self):
        """Values > 1.0 should be clamped to 1.0"""
        assert validate_and_clamp_probability(1.5) == 1.0
        assert validate_and_clamp_probability(2.0) == 1.0
        assert validate_and_clamp_probability(100) == 1.0

    def test_nan_uses_default(self):
        """NaN should return default value"""
        assert validate_and_clamp_probability(np.nan) == 0.5
        assert validate_and_clamp_probability(np.nan, default=0.75) == 0.75

    def test_inf_uses_default(self):
        """Infinity should return default value"""
        assert validate_and_clamp_probability(np.inf) == 0.5
        assert validate_and_clamp_probability(-np.inf) == 0.5

    def test_none_uses_default(self):
        """None should return default value"""
        assert validate_and_clamp_probability(None) == 0.5
        assert validate_and_clamp_probability(None, default=0.3) == 0.3


class TestValidateStudentFeatures:
    """Test student feature validation"""

    def test_valid_features(self):
        """Valid feature DataFrame should return True"""
        df = pd.DataFrame({"feature1": [1.0, 2.0, 3.0], "feature2": [0.5, 0.6, 0.7]})
        assert validate_student_features(df) is True

    def test_nan_features_invalid(self):
        """Features with NaN should return False"""
        df = pd.DataFrame({"feature1": [1.0, np.nan, 3.0], "feature2": [0.5, 0.6, 0.7]})
        assert validate_student_features(df) is False

    def test_inf_features_invalid(self):
        """Features with Inf should return False"""
        df = pd.DataFrame({"feature1": [1.0, 2.0, np.inf], "feature2": [0.5, 0.6, 0.7]})
        assert validate_student_features(df) is False

    def test_empty_dataframe_invalid(self):
        """Empty DataFrame should return False"""
        df = pd.DataFrame()
        assert validate_student_features(df) is False

    def test_none_dataframe_invalid(self):
        """None should return False"""
        assert validate_student_features(None) is False


class TestSanitizeStudentFeatures:
    """Test student feature sanitization"""

    def test_nan_replaced_with_median(self):
        """NaN values should be replaced with median"""
        df = pd.DataFrame({"feature1": [1.0, np.nan, 3.0]})
        sanitized = sanitize_student_features(df)
        assert not sanitized["feature1"].isna().any()
        assert sanitized["feature1"].iloc[1] == 2.0  # median of [1.0, 3.0]

    def test_inf_replaced(self):
        """Inf values should be replaced"""
        df = pd.DataFrame({"feature1": [1.0, np.inf, 3.0]})
        sanitized = sanitize_student_features(df)
        assert not np.isinf(sanitized["feature1"]).any()


class TestValidateRiskScoreDict:
    """Test risk score dictionary validation"""

    def test_valid_result(self):
        """Valid result dict should return True"""
        result = {
            "risk_score": 0.75,
            "prediction": 1,
            "signal_breakdown": {
                "academic_signal_score": 0.6,
                "engagement_signal_score": 0.8,
            },
        }
        assert validate_risk_score_dict(result) is True

    def test_missing_risk_score_invalid(self):
        """Dict without risk_score should return False"""
        result = {"prediction": 1}
        assert validate_risk_score_dict(result) is False

    def test_nan_risk_score_invalid(self):
        """NaN risk_score should return False"""
        result = {"risk_score": np.nan, "prediction": 1}
        assert validate_risk_score_dict(result) is False

    def test_out_of_range_risk_score_invalid(self):
        """Risk score outside [0, 100] should return False"""
        result = {"risk_score": -0.5, "prediction": 1}
        assert validate_risk_score_dict(result) is False

        result = {"risk_score": 150.0, "prediction": 1}
        assert validate_risk_score_dict(result) is False

    def test_none_result_invalid(self):
        """None result should return False"""
        assert validate_risk_score_dict(None) is False


class TestGetSafeDefaultPrediction:
    """Test safe default prediction"""

    def test_has_required_fields(self):
        """Default prediction should have all required fields"""
        default = get_safe_default_prediction()
        assert "risk_score" in default
        assert "prediction" in default
        assert "signal_breakdown" in default
        assert "model_version" in default

    def test_risk_score_is_valid(self):
        """Default risk_score should be valid"""
        default = get_safe_default_prediction()
        assert default["risk_score"] == 50.0
        assert 0.0 <= default["risk_score"] <= 100.0

    def test_signals_are_valid(self):
        """All signal scores should be valid"""
        default = get_safe_default_prediction()
        for signal_name, signal_value in default["signal_breakdown"].items():
            assert 0.0 <= signal_value <= 1.0


class TestRegressionNoNegativeRiskScore:
    """
    Regression test to ensure -1 risk scores can NEVER occur

    This is the CRITICAL test that verifies the bug is fixed.
    """

    def test_negative_value_clamped_to_zero(self):
        """Ensure negative values are always clamped to 0"""
        test_values = [-1, -0.5, -100, -0.001]
        for val in test_values:
            result = validate_and_clamp_probability(val)
            assert result >= 0.0, f"Negative value {val} not clamped: got {result}"
            assert result == 0.0, f"Expected 0.0 for {val}, got {result}"

    def test_invalid_values_never_propagate(self):
        """Ensure invalid values use safe default"""
        invalid_values = [None, np.nan, np.inf, -np.inf]
        for val in invalid_values:
            result = validate_and_clamp_probability(val, default=0.5)
            assert result >= 0.0, f"Invalid value {val} resulted in negative: {result}"
            assert result <= 1.0, f"Invalid value {val} resulted in > 1.0: {result}"
            assert (
                result == 0.5
            ), f"Invalid value {val} should use default 0.5, got {result}"

    def test_sanitize_prevents_negative(self):
        """Sanitize should prevent negative risk scores"""
        invalid_result = {
            "risk_score": -1.0,  # This is the BUG we're fixing
            "signal_breakdown": {},
        }

        sanitized = sanitize_risk_score_dict(invalid_result)
        assert sanitized["risk_score"] >= 0.0
        assert sanitized["risk_score"] <= 1.0
        assert sanitized["risk_score"] == 0.0  # -1 should be clamped to 0


class TestValidateStudentData:
    """Test student data validation"""

    def test_valid_dataframe(self):
        """Valid DataFrame should return True"""
        df = pd.DataFrame({"id": ["student1"], "absrate7": [0.1]})
        assert validate_student_data(df) is True

    def test_valid_dict(self):
        """Valid dict should return True"""
        data = {"id": "student1", "absrate7": 0.1}
        assert validate_student_data(data) is True

    def test_none_invalid(self):
        """None should return False"""
        assert validate_student_data(None) is False

    def test_empty_dataframe_invalid(self):
        """Empty DataFrame should return False"""
        assert validate_student_data(pd.DataFrame()) is False

    def test_empty_dict_invalid(self):
        """Empty dict should return False"""
        assert validate_student_data({}) is False
