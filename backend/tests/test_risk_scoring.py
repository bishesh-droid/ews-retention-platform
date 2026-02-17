"""
Unit tests for Risk Scoring and Feature Engineering.

Tests verify that:
1. Risk scores are always [0-100]
2. Negative CSV values are handled properly
3. Edge cases (missing data, perfect scores, etc.) work correctly
"""

import pytest
from backend.services.feature_engineering import FeatureEngineer
from backend.services.risk_scoring import RiskScorer


class TestFeatureEngineering:
    """Test feature engineering calculations."""
    
    def test_normalize_to_scale(self):
        """Test normalization function."""
        # Normal case
        result = FeatureEngineer.normalize_to_scale(50, 0, 100, 0, 100)
        assert result == 50.0
        
        # Min value
        result = FeatureEngineer.normalize_to_scale(0, 0, 100, 0, 100)
        assert result == 0.0
        
        # Max value
        result = FeatureEngineer.normalize_to_scale(100, 0, 100, 0, 100)
        assert result == 100.0
        
        # Clamping
        result = FeatureEngineer.normalize_to_scale(150, 0, 100, 0, 100)
        assert result == 100.0
        
        result = FeatureEngineer.normalize_to_scale(-50, 0, 100, 0, 100)
        assert result == 0.0
    
    def test_attendance_score_with_negative_absence(self):
        """Test attendance calculation with negative absence rates."""
        student_data = {
            'absrate1': -5.0,
            'absrate2': -3.0,
            'absrate3': 2.0,
            'absrate4': 5.0,
            'absrate5': 10.0,
            'absrate6': 15.0,
            'absrate7': 8.0
        }
        
        score = FeatureEngineer.calculate_attendance_score(student_data)
        assert 0 <= score <= 100, f"Attendance score {score} out of bounds"
    
    def test_academic_score_normal_range(self):
        """Test academic score with normal MPA values."""
        student_data = {}
        # Set all quarterly scores to 3.0 (average)
        for year in range(1, 8):
            for quarter in range(1, 5):
                student_data[f'q{quarter}mpa{year}'] = 3.0
        
        score = FeatureEngineer.calculate_academic_score(student_data)
        assert 0 <= score <= 100
        assert 40 <= score <= 60  # Should be mid-range for average scores
    
    def test_perfect_student(self):
        """Test student with perfect scores everywhere."""
        student_data = {}
        
        # Perfect attendance (no absences)
        for year in range(1, 8):
            student_data[f'absrate{year}'] = 0.0
            student_data[f'nsusp{year}'] = 0.0
            student_data[f'mobility{year}'] = 0.0
            for quarter in range(1, 5):
                student_data[f'q{quarter}mpa{year}'] = 5.0  # Perfect GPA
        
        student_data['nograd'] = 0  # Graduated
        
        features = FeatureEngineer.calculate_all_features(student_data)
        
        # Perfect student should have high scores
        # Note: Due to CSV containing negative values, zero absences/suspensions
        # get normalized to mid-range (~60%), not 100%
        assert features['attendance_score'] > 50
        assert features['academic_score'] > 80  # MPA=5.0 is above normal max
        assert features['behavioral_score'] > 50  # Zero suspensions = mid-range
        assert features['stability_score'] > 50  # Zero mobility = mid-range
        assert features['graduated'] is True
    
    def test_worst_case_student(self):
        """Test student with worst possible scores."""
        student_data = {}
        
        # Worst scores
        for year in range(1, 8):
            student_data[f'absrate{year}'] = 40.0  # High absence
            student_data[f'nsusp{year}'] = 1.5  # Many suspensions
            student_data[f'mobility{year}'] = 4.0  # High mobility
            for quarter in range(1, 5):
                student_data[f'q{quarter}mpa{year}'] = 0.0  # Failing
        
        student_data['nograd'] = 1  # Did not graduate
        
        features = FeatureEngineer.calculate_all_features(student_data)
        
        # All scores should still be valid [0-100]
        assert 0 <= features['attendance_score'] <= 100
        assert 0 <= features['academic_score'] <= 100
        assert 0 <= features['behavioral_score'] <= 100
        assert 0 <= features['stability_score'] <= 100
        assert features['graduated'] is False
    
    def test_missing_data_handling(self):
        """Test handling of missing data."""
        student_data = {
            'absrate1': 5.0,
            # Missing absrate2-7
            'q1mpa1': 2.5,
            # Missing other quarters
            'nograd': 0
        }
        
        features = FeatureEngineer.calculate_all_features(student_data)
        
        # Should return valid scores even with missing data
        assert 0 <= features['attendance_score'] <= 100
        assert 0 <= features['academic_score'] <= 100
        assert 0 <= features['behavioral_score'] <= 100
        assert 0 <= features['stability_score'] <= 100


class TestRiskScoring:
    """Test risk score calculations."""
    
    def test_risk_score_bounds(self):
        """Ensure risk scores are always 0-100."""
        # Normal features
        features = {
            'attendance_score': 50.0,
            'academic_score': 50.0,
            'behavioral_score': 50.0,
            'stability_score': 50.0
        }
        
        risk = RiskScorer.calculate_risk_score(features)
        assert 0 <= risk <= 100
        assert 45 <= risk <= 55  # Should be mid-range
    
    def test_perfect_student_low_risk(self):
        """Perfect student should have low risk."""
        features = {
            'attendance_score': 100.0,
            'academic_score': 100.0,
            'behavioral_score': 100.0,
            'stability_score': 100.0
        }
        
        risk = RiskScorer.calculate_risk_score(features)
        assert risk < 20  # Very low risk
        assert RiskScorer.get_risk_category(risk) == "low"
    
    def test_failing_student_high_risk(self):
        """Failing student should have high risk."""
        features = {
            'attendance_score': 0.0,
            'academic_score': 0.0,
            'behavioral_score': 0.0,
            'stability_score': 0.0
        }
        
        risk = RiskScorer.calculate_risk_score(features)
        assert risk > 80  # Very high risk
        assert RiskScorer.get_risk_category(risk) == "high"
    
    def test_risk_validation(self):
        """Test risk score validation."""
        assert RiskScorer.validate_risk_score(50.0) is True
        assert RiskScorer.validate_risk_score(0.0) is True
        assert RiskScorer.validate_risk_score(100.0) is True
        assert RiskScorer.validate_risk_score(-1.0) is False
        assert RiskScorer.validate_risk_score(101.0) is False
        assert RiskScorer.validate_risk_score(float('nan')) is False
    
    def test_dominant_risk_factor(self):
        """Test identification of dominant risk factor."""
        # Academic is worst
        features = {
            'attendance_score': 80.0,
            'academic_score': 20.0,  # Worst
            'behavioral_score': 70.0,
            'stability_score': 90.0
        }
        
        dominant = RiskScorer.get_dominant_risk_factor(features)
        assert dominant == "academic"  # Has 40% weight and worst score
    
    def test_weight_sum_equals_one(self):
        """Verify weights sum to 1.0."""
        total = sum(RiskScorer.WEIGHTS.values())
        assert abs(total - 1.0) < 0.001  # Allow tiny floating point error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
