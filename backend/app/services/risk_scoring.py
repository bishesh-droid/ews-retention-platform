"""
Risk Scoring Engine for EWS Retention Platform.

Calculates dropout risk from engagement features derived from
Engagement_Analysis.xlsx data.

Risk Score Formula:
    risk = 100 - weighted_engagement

    weighted_engagement = (
        0.30 * content_completion_score +
        0.20 * quiz_engagement_score +
        0.15 * login_consistency_score +
        0.15 * time_investment_score +
        0.10 * discussion_engagement_score +
        0.10 * assignment_score
    )

Higher risk score = higher chance of disengagement/dropout.
"""

from typing import Dict


class RiskScorer:
    """
    Calculates student risk scores from engagement features.
    """

    # Engagement component weights (must sum to 1.0)
    WEIGHTS = {
        'content_completion': 0.30,
        'quiz_engagement': 0.20,
        'login_consistency': 0.15,
        'time_investment': 0.15,
        'discussion_engagement': 0.10,
        'assignment': 0.10,
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
        weighted_engagement = (
            RiskScorer.WEIGHTS['content_completion'] * features.get('content_completion_score', 0) +
            RiskScorer.WEIGHTS['quiz_engagement'] * features.get('quiz_engagement_score', 0) +
            RiskScorer.WEIGHTS['login_consistency'] * features.get('login_consistency_score', 0) +
            RiskScorer.WEIGHTS['time_investment'] * features.get('time_investment_score', 0) +
            RiskScorer.WEIGHTS['discussion_engagement'] * features.get('discussion_engagement_score', 0) +
            RiskScorer.WEIGHTS['assignment'] * features.get('assignment_score', 0)
        )

        # Zero-progress penalty: if all courses have 0 progress, increase risk
        zero_ratio = features.get('zero_progress_ratio', 0)
        if zero_ratio >= 0.8:
            weighted_engagement *= 0.5  # Halve engagement if mostly zero progress

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
        component_scores = {
            'content_completion': features.get('content_completion_score', 0),
            'quiz_engagement': features.get('quiz_engagement_score', 0),
            'login_consistency': features.get('login_consistency_score', 0),
            'time_investment': features.get('time_investment_score', 0),
            'discussion_engagement': features.get('discussion_engagement_score', 0),
            'assignment': features.get('assignment_score', 0),
        }

        # Risk contribution = (100 - score) * weight
        risk_contributions = {
            k: (100 - v) * RiskScorer.WEIGHTS[k]
            for k, v in component_scores.items()
        }

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
