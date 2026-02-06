"""
Risk Scoring Engine for EWS Retention Platform.

This module implements the risk scoring algorithm that combines
multiple features into a single risk score [0-100].

Risk Score Formula:
    risk = (0.30 * attendance_risk +
            0.40 * academic_risk +
            0.20 * behavioral_risk +
            0.10 * stability_risk)

All component scores are inverted from their feature scores:
    component_risk = 100 - component_score
    
So a student with low attendance (score=20) has high attendance risk (80).
"""

from typing import Dict


class RiskScorer:
    """
    Calculates student risk scores using weighted formula.
    """
    
    # Risk component weights (must sum to 1.0)
    WEIGHTS = {
        'attendance': 0.30,
        'academic': 0.40,
        'behavioral': 0.20,
        'stability': 0.10
    }
    
    # Risk thresholds for categorization
    RISK_THRESHOLDS = {
        'low': 40.0,       # risk < 40
        'medium': 70.0,    # 40 <= risk < 70
        'high': 100.0      # risk >= 70
    }
    
    @staticmethod
    def calculate_risk_score(features: Dict) -> float:
        """
        Calculate overall risk score from component features.
        
        Args:
            features: Dictionary containing:
                - attendance_score: 0-100 (higher = better)
                - academic_score: 0-100 (higher = better)
                - behavioral_score: 0-100 (higher = better)
                - stability_score: 0-100 (higher = better)
        
        Returns:
            Risk score [0-100], where higher = higher risk of dropout
        """
        # Convert feature scores to risk scores (invert)
        attendance_risk = 100 - features['attendance_score']
        academic_risk = 100 - features['academic_score']
        behavioral_risk = 100 - features['behavioral_score']
        stability_risk = 100 - features['stability_score']
        
        # Weighted sum
        risk_score = (
            RiskScorer.WEIGHTS['attendance'] * attendance_risk +
            RiskScorer.WEIGHTS['academic'] * academic_risk +
            RiskScorer.WEIGHTS['behavioral'] * behavioral_risk +
            RiskScorer.WEIGHTS['stability'] * stability_risk
        )
        
        # Clamp to valid range [0, 100]
        risk_score = max(0.0, min(100.0, risk_score))
        
        # Validate no NaN or infinity
        if not isinstance(risk_score, (int, float)) or risk_score != risk_score:
            # NaN detected, return median risk
            return 50.0
        
        return round(risk_score, 2)
    
    @staticmethod
    def get_risk_category(risk_score: float) -> str:
        """
        Categorize risk score into low/medium/high.
        
        Args:
            risk_score: Risk score [0-100]
            
        Returns:
            "low", "medium", or "high"
        """
        if risk_score < RiskScorer.RISK_THRESHOLDS['low']:
            return "low"
        elif risk_score < RiskScorer.RISK_THRESHOLDS['medium']:
            return "medium"
        else:
            return "high"
    
    @staticmethod
    def get_retention_likelihood(risk_score: float) -> str:
        """
        Convert risk score to retention likelihood label.
        
        Args:
            risk_score: Risk score [0-100]
            
        Returns:
            "Very High", "High", "Medium", "Low", or "Very Low"
        """
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
        """
        Identify which component contributes most to overall risk.
        
        Args:
            features: Feature scores dictionary
            
        Returns:
            "attendance", "academic", "behavioral", or "stability"
        """
        # Calculate risk contributions (inverted scores * weights)
        risks = {
            'attendance': (100 - features['attendance_score']) * RiskScorer.WEIGHTS['attendance'],
            'academic': (100 - features['academic_score']) * RiskScorer.WEIGHTS['academic'],
            'behavioral': (100 - features['behavioral_score']) * RiskScorer.WEIGHTS['behavioral'],
            'stability': (100 - features['stability_score']) * RiskScorer.WEIGHTS['stability']
        }
        
        # Return factor with highest contribution
        return max(risks, key=risks.get)
    
    @staticmethod
    def get_risk_breakdown(features: Dict) -> Dict:
        """
        Get detailed breakdown of risk components.
        
        Args:
            features: Feature scores dictionary
            
        Returns:
            Dictionary with risk breakdown per component
        """
        return {
            'attendance_risk': round(100 - features['attendance_score'], 2),
            'academic_risk': round(100 - features['academic_score'], 2),
            'behavioral_risk': round(100 - features['behavioral_score'], 2),
            'stability_risk': round(100 - features['stability_score'], 2),
            'weights': RiskScorer.WEIGHTS
        }
    
    @staticmethod
    def validate_risk_score(risk_score: float) -> bool:
        """
        Validate that risk score is within acceptable range.
        
        Args:
            risk_score: Score to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(risk_score, (int, float)):
            return False
        
        if risk_score != risk_score:  # NaN check
            return False
        
        if risk_score < 0 or risk_score > 100:
            return False
        
        return True
