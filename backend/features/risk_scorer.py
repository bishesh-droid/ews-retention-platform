"""
Risk Score Aggregation
Combines all signals into final risk score with bounds checking
"""
from typing import Dict, Optional
import numpy as np
from datetime import datetime

from backend.features.academic_signals import AcademicPerformanceSignal
from backend.features.engagement_signals import EngagementSignal


class RiskScorer:
    """Aggregate all signals into final risk score"""
    
    def __init__(self):
        self.signal_weights = {
            'academic_performance': 0.45,
            'engagement': 0.55
        }
    
    def compute_risk_score(self, db_session, student_id: str, trimester: str) -> Dict:
        """
        Compute final risk score with multi-layer validation
        
        Returns:
            {
                'risk_score': float (0-100),
                'risk_level': str ('Low', 'Medium', 'High', 'Critical'),
                'signals': dict,
                'missing_signals': list,
                'confidence': float (0-1)
            }
        """
        # Compute all signals
        signals = {
            'academic_performance': AcademicPerformanceSignal().compute(db_session, student_id, trimester),
            'engagement': EngagementSignal().compute(db_session, student_id, trimester)
        }
        
        # Extract signal values
        signal_values = {k: v.get('signal_value') for k, v in signals.items()}
        
        # Check for missing signals
        missing = [k for k, v in signal_values.items() if v is None]
        
        # Compute weighted score
        valid_signals = {k: v for k, v in signal_values.items() if v is not None}
        
        if not valid_signals:
            return {
                'risk_score': None,
                'risk_level': 'Unknown',
                'signals': signals,
                'missing_signals': missing,
                'confidence': 0.0,
                'error': 'Insufficient data'
            }
        
        # Renormalize weights for available signals
        available_weight = sum(self.signal_weights[k] for k in valid_signals.keys())
        norm_weights = {k: self.signal_weights[k] / available_weight 
                       for k in valid_signals.keys()}
        
        risk_score = sum(norm_weights[k] * valid_signals[k] for k in valid_signals.keys())
        
        # MULTI-LAYER BOUNDS CHECKING
        # Layer 1: Clamp to bounds
        risk_score = max(0.0, min(100.0, risk_score))
        
        # Layer 2: Validate output
        assert 0 <= risk_score <= 100, f"Invalid risk score: {risk_score}"
        
        # Layer 3: Check for NaN/Inf
        if not np.isfinite(risk_score):
            risk_score = None
            return {
                'risk_score': None,
                'risk_level': 'Unknown',
                'signals': signals,
                'missing_signals': missing,
                'confidence': 0.0,
                'error': 'Non-finite risk score'
            }
        
        # Compute confidence (% of signals available)
        confidence = len(valid_signals) / len(self.signal_weights)
        
        # Determine risk level
        if risk_score >= 75:
            risk_level = 'Critical'
        elif risk_score >= 50:
            risk_level = 'High'
        elif risk_score >= 25:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        return {
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'signals': signals,
            'missing_signals': missing,
            'confidence': round(confidence, 2)
        }
