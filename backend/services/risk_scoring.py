"""
Risk Scoring Engine for EWS Retention Platform.

Calculates dropout risk from engagement features derived from
real XLSX data (Engagement_Analysis, Quiz/Assignment/Exam).

Risk Score Formula:
    risk = 100 - weighted_engagement

    weighted_engagement = sum of (weight * score) for all components

Higher risk score = higher chance of disengagement/dropout.
"""

from typing import Dict


class RiskScorer:
    """
    Calculates student risk scores from engagement features.
    """

    # Engagement component weights (must sum to 1.0)
    WEIGHTS = {
        'content_completion': 0.15,
        'quiz_engagement': 0.05,
        'login_consistency': 0.05,
        'time_investment': 0.05,
        'discussion_engagement': 0.05,
        'assignment': 0.05,
        'graded_quiz': 0.20,
        'graded_assignment': 0.15,
        'exam': 0.15,
        'exam_attendance': 0.10,
    }

    # Risk thresholds
    RISK_THRESHOLDS = {
        'low': 40.0,       # risk < 40
        'medium': 70.0,    # 40 <= risk < 70
        'high': 100.0      # risk >= 70
    }

    @staticmethod
    def calculate_risk_score(features: Dict) -> float:
        """
        Calculate overall risk score from engagement features.

        Args:
            features: Dictionary from FeatureEngineer.calculate_all_features()

        Returns:
            Risk score [0-100], where higher = higher risk of dropout
        """
        # Map weight keys to feature keys
        feature_key_map = {
            'content_completion': 'content_completion_score',
            'quiz_engagement': 'quiz_engagement_score',
            'login_consistency': 'login_consistency_score',
            'time_investment': 'time_investment_score',
            'discussion_engagement': 'discussion_engagement_score',
            'assignment': 'assignment_score',
            'graded_quiz': 'graded_quiz_score',
            'graded_assignment': 'graded_assignment_score',
            'exam': 'exam_score',
            'exam_attendance': 'exam_attendance_rate',
        }

        weighted_engagement = 0.0
        for key, weight in RiskScorer.WEIGHTS.items():
            feature_key = feature_key_map.get(key, f'{key}_score')
            score = features.get(feature_key, 0)
            if score is None:
                score = 0
            weighted_engagement += weight * score

        # Zero-progress penalty: if all courses have 0 progress, increase risk
        zero_ratio = features.get('zero_progress_ratio', 0)
        if zero_ratio >= 0.8:
            weighted_engagement *= 0.5

        risk_score = 100 - weighted_engagement
        risk_score = max(0.0, min(100.0, risk_score))

        if not isinstance(risk_score, (int, float)) or risk_score != risk_score:
            return 75.0  # Default high-ish risk for NaN

        return round(risk_score, 2)

    @staticmethod
    def get_risk_category(risk_score: float) -> str:
        """Categorize risk score into low/medium/high."""
        if risk_score < RiskScorer.RISK_THRESHOLDS['low']:
            return "low"
        elif risk_score < RiskScorer.RISK_THRESHOLDS['medium']:
            return "medium"
        else:
            return "high"

    @staticmethod
    def get_retention_likelihood(risk_score: float) -> str:
        """Convert risk score to retention likelihood label."""
        if risk_score < 20:
            return "Very High"
        elif risk_score < 40:
            return "High"
        elif risk_score < 60:
            return "Medium"
        elif risk_score < 80:
            return "Low"
        else:
            return "Very Low"

    @staticmethod
    def get_dominant_risk_factor(features: Dict) -> str:
        """Identify which engagement component is weakest (contributes most to risk)."""
        feature_key_map = {
            'Content Completion': 'content_completion_score',
            'Quiz Engagement': 'quiz_engagement_score',
            'Login Consistency': 'login_consistency_score',
            'Time Investment': 'time_investment_score',
            'Discussion Engagement': 'discussion_engagement_score',
            'Assignment Submissions': 'assignment_score',
            'Graded Quiz Performance': 'graded_quiz_score',
            'Graded Assignment Performance': 'graded_assignment_score',
            'Exam Performance': 'exam_score',
            'Exam Attendance': 'exam_attendance_rate',
        }

        weight_map = {
            'Content Completion': 'content_completion',
            'Quiz Engagement': 'quiz_engagement',
            'Login Consistency': 'login_consistency',
            'Time Investment': 'time_investment',
            'Discussion Engagement': 'discussion_engagement',
            'Assignment Submissions': 'assignment',
            'Graded Quiz Performance': 'graded_quiz',
            'Graded Assignment Performance': 'graded_assignment',
            'Exam Performance': 'exam',
            'Exam Attendance': 'exam_attendance',
        }

        risk_contributions = {}
        for label, feature_key in feature_key_map.items():
            score = features.get(feature_key, 0) or 0
            weight = RiskScorer.WEIGHTS.get(weight_map[label], 0)
            risk_contributions[label] = (100 - score) * weight

        return max(risk_contributions, key=risk_contributions.get)

    @staticmethod
    def get_risk_breakdown(features: Dict) -> Dict:
        """Get detailed breakdown of risk components."""
        return {
            'content_completion_risk': round(100 - features.get('content_completion_score', 0), 2),
            'quiz_engagement_risk': round(100 - features.get('quiz_engagement_score', 0), 2),
            'login_consistency_risk': round(100 - features.get('login_consistency_score', 0), 2),
            'time_investment_risk': round(100 - features.get('time_investment_score', 0), 2),
            'discussion_engagement_risk': round(100 - features.get('discussion_engagement_score', 0), 2),
            'assignment_risk': round(100 - features.get('assignment_score', 0), 2),
            'graded_quiz_risk': round(100 - features.get('graded_quiz_score', 0), 2),
            'graded_assignment_risk': round(100 - features.get('graded_assignment_score', 0), 2),
            'exam_risk': round(100 - features.get('exam_score', 0), 2),
            'exam_attendance_risk': round(100 - features.get('exam_attendance_rate', 0), 2),
            'weights': RiskScorer.WEIGHTS,
        }

    @staticmethod
    def validate_risk_score(risk_score: float) -> bool:
        """Validate that risk score is within acceptable range."""
        if not isinstance(risk_score, (int, float)):
            return False
        if risk_score != risk_score:  # NaN check
            return False
        if risk_score < 0 or risk_score > 100:
            return False
        return True
