"""
Composite Explainable Indices
Named, interpretable indices combining multiple advanced features
"""
from typing import Dict, Optional, List, Tuple
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session

# Import all feature computers
from backend.features.temporal_features import TemporalFeatureComputer
from backend.features.behavioral_features import ConsistencyFeatureComputer, EffortOutcomeFeatureComputer
from backend.features.advanced_engagement_features import (
    EngagementDepthComputer,
    IntentResponsivenessComputer,
    CohortNormalizationComputer
)


class CompositeIndexComputer:
    """Compute composite explainable retention indices"""
    
    def __init__(self):
        self.temporal = TemporalFeatureComputer()
        self.consistency = ConsistencyFeatureComputer()
        self.effort = EffortOutcomeFeatureComputer()
        self.engagement_depth = EngagementDepthComputer()
        self.intent_resp = IntentResponsivenessComputer()
    
    def compute_all(self, db: Session, student_id: str, cohort_id: str = None) -> Dict:
        """Compute all composite indices"""
        
        # Get all base features
        temporal_features = self.temporal.compute_all(db, student_id)
        consistency_features = self.consistency.compute_all(db, student_id)
        effort_features = self.effort.compute_all(db, student_id)
        engagement_features = self.engagement_depth.compute_all(db, student_id)
        intent_features = self.intent_resp.compute_all(db, student_id)
        
        return {
            'disengagement_velocity_index': self.disengagement_velocity_index(
                temporal_features, consistency_features, intent_features
            ),
            'academic_instability_index': self.academic_instability_index(
                temporal_features, effort_features
            ),
            'routine_strength_index': self.routine_strength_index(
                consistency_features
            ),
            'retention_risk_index': self.retention_risk_index(
                temporal_features, consistency_features, effort_features,
                engagement_features, intent_features
            ),
            'computation_timestamp': datetime.now().isoformat()
        }
    
    def disengagement_velocity_index(
        self,
        temporal_features: Dict,
        consistency_features: Dict,
        intent_features: Dict
    ) -> Dict:
        """
        Index 8.1: Disengagement Velocity Index (DVI)
        
        Rate of engagement decline across multiple dimensions
        
        Contributing Features:
        - engagement_decay_rate (30%)
        - engagement_session_frequency_trend (25%)
        - engagement_longest_inactivity_days (20%)
        - consistency_login_regularity_score (15%)
        - responsiveness_latency_trend (10%)
        """
        components = []
        weights = []
        details = []
        
        # 1. Engagement decay rate (30%)
        decay = temporal_features.get('engagement_decay_rate')
        if decay and decay['value'] is not None:
            # Convert to 0-100 risk score (negative decay = higher risk)
            decay_risk = max(0, min(100, -decay['value'] * 2))  # -50%/week = 100 risk
            components.append(decay_risk)
            weights.append(0.30)
            details.append({
                'feature': 'Engagement decay',
                'value': decay['value'],
                'risk_score': decay_risk,
                'weight': '30%',
                'interpretation': decay['interpretation']
            })
        
        # 2. Session frequency trend (25%)
        session = temporal_features.get('engagement_session_frequency_trend')
        if session and session['value'] is not None:
            # Declining sessions = higher risk
            session_risk = max(0, min(100, -session['value'] * 20))  # -5 logins/week = 100 risk
            components.append(session_risk)
            weights.append(0.25)
            details.append({
                'feature': 'Session frequency',
                'value': session['value'],
                'risk_score': session_risk,
                'weight': '25%',
                'interpretation': session['interpretation']
            })
        
        # 3. Longest inactivity gap (20%)
        gap = temporal_features.get('engagement_longest_inactivity_days')
        if gap and gap['value'] is not None:
            # Gap > 14 days = 100 risk
            gap_risk = min(100, (gap['value'] / 14) * 100)
            components.append(gap_risk)
            weights.append(0.20)
            details.append({
                'feature': 'Longest activity gap',
                'value': gap['value'],
                'risk_score': gap_risk,
                'weight': '20%',
                'interpretation': gap['interpretation']
            })
        
        # 4. Login regularity (15%)
        regularity = consistency_features.get('consistency_login_regularity_score')
        if regularity and regularity['value'] is not None:
            # Low regularity = high risk (invert)
            regularity_risk = 100 - regularity['value']
            components.append(regularity_risk)
            weights.append(0.15)
            details.append({
                'feature': 'Login regularity',
                'value': regularity['value'],
                'risk_score': regularity_risk,
                'weight': '15%',
                'interpretation': regularity['interpretation']
            })
        
        # 5. Response latency trend (10%)
        latency = intent_features.get('responsiveness_latency_trend')
        if latency and latency['value'] is not None:
            # Increasing latency = higher risk
            latency_risk = max(0, min(100, latency['value'] * 10))  # +10 hrs/msg = 100 risk
            components.append(latency_risk)
            weights.append(0.10)
            details.append({
                'feature': 'Response latency',
                'value': latency['value'],
                'risk_score': latency_risk,
                'weight': '10%',
                'interpretation': latency['interpretation']
            })
        
        # Calculate weighted average
        if not components:
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown',
                'components': []
            }
        
        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        dvi = sum(c * w for c, w in zip(components, normalized_weights))
        
        # Interpretation
        if dvi < 30:
            interpretation = "Stable/growing engagement"
            risk_level = 'low'
            recommendation = "Continue monitoring"
        elif dvi < 60:
            interpretation = "Moderate disengagement"
            risk_level = 'medium'
            recommendation = "Proactive check-in recommended"
        else:
            interpretation = "Rapid disengagement"
            risk_level = 'high'
            recommendation = "Immediate intervention needed within 7 days"
        
        return {
            'value': float(dvi),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'components': details,
            'prediction': f"{int(dvi)}% probability of dropout within 6 weeks" if dvi > 50 else None
        }
    
    def academic_instability_index(
        self,
        temporal_features: Dict,
        effort_features: Dict
    ) -> Dict:
        """
        Index 8.2: Academic Instability Index (AII)
        
        Volatility and decline in academic performance
        
        Contributing Features:
        - academic_score_volatility (30%)
        - academic_grade_trend_slope (25%)
        - effort_practice_exam_gap (20%)
        - effort_time_to_score_ratio (15%)
        - effort_procrastination_index (10%)
        """
        components = []
        weights = []
        details = []
        
        # 1. Score volatility (30%)
        volatility = temporal_features.get('academic_score_volatility')
        if volatility and volatility['value'] is not None:
            # SD > 20 = 100 risk
            volatility_risk = min(100, (volatility['value'] / 20) * 100)
            components.append(volatility_risk)
            weights.append(0.30)
            details.append({
                'feature': 'Score volatility',
                'value': volatility['value'],
                'risk_score': volatility_risk,
                'weight': '30%',
                'interpretation': volatility['interpretation']
            })
        
        # 2. Grade trend slope (25%)
        trend = temporal_features.get('academic_grade_trend_slope')
        if trend and trend['value'] is not None:
            # Declining = high risk
            trend_risk = max(0, min(100, -trend['value'] * 50))  # -2%/day = 100 risk
            components.append(trend_risk)
            weights.append(0.25)
            details.append({
                'feature': 'Grade trend',
                'value': trend['value'],
                'risk_score': trend_risk,
                'weight': '25%',
                'interpretation': trend['interpretation']
            })
        
        # 3. Practice-exam gap (20%)
        gap = effort_features.get('effort_practice_exam_gap')
        if gap and gap['value'] is not None:
            # Gap > 30% = 100 risk
            gap_risk = min(100, abs(gap['value']) / 30 * 100)
            components.append(gap_risk)
            weights.append(0.20)
            details.append({
                'feature': 'Practice-exam gap',
                'value': gap['value'],
                'risk_score': gap_risk,
                'weight': '20%',
                'interpretation': gap['interpretation']
            })
        
        # 4. Time-to-score ratio (15%)
        efficiency = effort_features.get('effort_time_to_score_ratio')
        if efficiency and efficiency['value'] is not None:
            # > 15 min/point = 100 risk
            efficiency_risk = min(100, (efficiency['value'] / 15) * 100)
            components.append(efficiency_risk)
            weights.append(0.15)
            details.append({
                'feature': 'Learning efficiency',
                'value': efficiency['value'],
                'risk_score': efficiency_risk,
                'weight': '15%',
                'interpretation': efficiency['interpretation']
            })
        
        # 5. Procrastination index (10%)
        procrastination = effort_features.get('effort_procrastination_index')
        if procrastination and procrastination['value'] is not None:
            # > 70% = 100 risk
            proc_risk = min(100, (procrastination['value'] / 70) * 100)
            components.append(proc_risk)
            weights.append(0.10)
            details.append({
                'feature': 'Procrastination',
                'value': procrastination['value'],
                'risk_score': proc_risk,
                'weight': '10%',
                'interpretation': procrastination['interpretation']
            })
        
        # Calculate index
        if not components:
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown',
                'components': []
            }
        
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        aii = sum(c * w for c, w in zip(components, normalized_weights))
        
        # Interpretation
        if aii < 30:
            interpretation = "Stable performance"
            risk_level = 'low'
            recommendation = "Continue current approach"
        elif aii < 60:
            interpretation = "Some instability"
            risk_level = 'medium'
            recommendation = "Study skills assessment recommended"
        else:
            interpretation = "High instability"
            risk_level = 'high'
            recommendation = "Academic advising + tutoring needed"
        
        return {
            'value': float(aii),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'components': details
        }
    
    def routine_strength_index(self, consistency_features: Dict) -> Dict:
        """
        Index 8.3: Routine Strength Index (RSI)
        
        Consistency of study habits and behavioral patterns
        
        Contributing Features:
        - consistency_login_regularity_score (30%)
        - consistency_study_streak_days (25%)
        - consistency_weekend_weekday_ratio (20%)
        - consistency_recovery_speed_days (15%)
        - consistency_late_night_ratio (10%, inverted)
        """
        components = []
        weights = []
        details = []
        
        # 1. Login regularity (30%)
        regularity = consistency_features.get('consistency_login_regularity_score')
        if regularity and regularity['value'] is not None:
            components.append(regularity['value'])
            weights.append(0.30)
            details.append({
                'feature': 'Login regularity',
                'value': regularity['value'],
                'weight': '30%',
                'interpretation': regularity['interpretation']
            })
        
        # 2. Study streak (25%)
        streak = consistency_features.get('consistency_study_streak_days')
        if streak and streak['value'] is not None:
            # Convert to 0-100 scale (21+ days = 100)
            streak_score = min(100, (streak['value'] / 21) * 100)
            components.append(streak_score)
            weights.append(0.25)
            details.append({
                'feature': 'Current streak',
                'value': streak['value'],
                'score': streak_score,
                'weight': '25%',
                'interpretation': streak['interpretation']
            })
        
        # 3. Weekend-weekday balance (20%)
        balance = consistency_features.get('consistency_weekend_weekday_ratio')
        if balance and balance['value'] is not None:
            # Optimal ratio around 0.5, normalize
            balance_score = min(100, (balance['value'] / 0.6) * 100)
            components.append(balance_score)
            weights.append(0.20)
            details.append({
                'feature': 'Week balance',
                'value': balance['value'],
                'score': balance_score,
                'weight': '20%',
                'interpretation': balance['interpretation']
            })
        
        # 4. Recovery speed (15%, inverted)
        recovery = consistency_features.get('consistency_recovery_speed_days')
        if recovery and recovery['value'] is not None:
            # Faster = better, 1 day = 100, 7+ days = 0
            recovery_score = max(0, 100 - ((recovery['value'] - 1) / 6 * 100))
            components.append(recovery_score)
            weights.append(0.15)
            details.append({
                'feature': 'Recovery speed',
                'value': recovery['value'],
                'score': recovery_score,
                'weight': '15%',
                'interpretation': recovery['interpretation']
            })
        
        # Calculate index
        if not components:
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown',
                'components': []
            }
        
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        rsi = sum(c * w for c, w in zip(components, normalized_weights))
        
        # Interpretation
        if rsi > 70:
            interpretation = "Strong routine"
            risk_level = 'low'
            recommendation = "Habits well-established"
        elif rsi > 40:
            interpretation = "Moderate routine"
            risk_level = 'medium'
            recommendation = "Encourage consistency"
        else:
            interpretation = "Weak/no routine"
            risk_level = 'high'
            recommendation = "Time management coaching needed"
        
        return {
            'value': float(rsi),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'components': details
        }
    
    def retention_risk_index(
        self,
        temporal_features: Dict,
        consistency_features: Dict,
        effort_features: Dict,
        engagement_features: Dict,
        intent_features: Dict
    ) -> Dict:
        """
        Index 8.4: Retention Risk Index (RRI)
        
        Overall dropout risk combining all signal groups
        
        Contributing Indices:
        - Disengagement Velocity Index (30%)
        - Academic Instability Index (25%)
        - Responsiveness latency (15%)
        - Ignored escalations (15%)
        - Routine Strength Index (10%, inverted)
        - Refund inquiries (5%)
        """
        
        # First compute the sub-indices
        dvi_result = self.disengagement_velocity_index(temporal_features, consistency_features, intent_features)
        aii_result = self.academic_instability_index(temporal_features, effort_features)
        rsi_result = self.routine_strength_index(consistency_features)
        
        components = []
        weights = []
        details = []
        
        # 1. DVI (30%)
        if dvi_result['value'] is not None:
            components.append(dvi_result['value'])
            weights.append(0.30)
            details.append({
                'index': 'Disengagement Velocity',
                'value': dvi_result['value'],
                'weight': '30%',
                'risk_level': dvi_result['risk_level']
            })
        
        # 2. AII (25%)
        if aii_result['value'] is not None:
            components.append(aii_result['value'])
            weights.append(0.25)
            details.append({
                'index': 'Academic Instability',
                'value': aii_result['value'],
                'weight': '25%',
                'risk_level': aii_result['risk_level']
            })
        
        # 3. Response latency (15%)
        latency = intent_features.get('responsiveness_latency_trend')
        if latency and latency['value'] is not None:
            latency_risk = max(0, min(100, latency['value'] * 10))
            components.append(latency_risk)
            weights.append(0.15)
            details.append({
                'index': 'Response Latency',
                'value': latency['value'],
                'risk_score': latency_risk,
                'weight': '15%',
                'risk_level': latency['risk_level']
            })
        
        # 4. Ignored escalations (15%)
        escalations = intent_features.get('responsiveness_ignored_escalation_count')
        if escalations and escalations['value'] is not None:
            escalation_risk = min(100, (escalations['value'] / 3) * 100)
            components.append(escalation_risk)
            weights.append(0.15)
            details.append({
                'index': 'Ignored Escalations',
                'value': escalations['value'],
                'risk_score': escalation_risk,
                'weight': '15%',
                'risk_level': escalations['risk_level']
            })
        
        # 5. RSI (10%, inverted - low routine = high risk)
        if rsi_result['value'] is not None:
            routine_risk = 100 - rsi_result['value']
            components.append(routine_risk)
            weights.append(0.10)
            details.append({
                'index': 'Routine Strength (inverted)',
                'value': rsi_result['value'],
                'risk_score': routine_risk,
                'weight': '10%',
                'risk_level': rsi_result['risk_level']
            })
        
        # Calculate RRI
        if not components:
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown',
                'components': []
            }
        
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        rri = sum(c * w for c, w in zip(components, normalized_weights))
        
        # Risk levels
        if rri < 30:
            interpretation = "LOW RISK"
            risk_level = 'low'
            recommendation = "Continue monitoring"
            actions = ["Maintain current support level"]
            probability = f"{int(rri)}% dropout probability"
        elif rri < 60:
            interpretation = "MODERATE RISK"
            risk_level = 'medium'
            recommendation = "Proactive check-in"
            actions = [
                "Faculty email check-in",
                "Review engagement patterns",
                "Offer office hours"
            ]
            probability = f"{int(rri)}% dropout probability"
        elif rri < 80:
            interpretation = "HIGH RISK"
            risk_level = 'high'
            recommendation = "Intervention needed"
            actions = [
                "Immediate faculty outreach (within 24h)",
                "Academic advisor meeting",
                "Study skills assessment",
                "Peer mentor assignment"
            ]
            probability = f"{int(rri)}% dropout probability within 4 weeks"
        else:
            interpretation = "CRITICAL RISK"
            risk_level = 'critical'
            recommendation = "URGENT action required"
            actions = [
                "🚨 Immediate intervention (same day)",
                "Dean/program director notification",
                "Emergency academic support plan",
                "Financial aid/wellness check",
                "Weekly monitoring cadence"
            ]
            probability = f"{int(rri)}% dropout probability within 2-4 weeks"
        
        return {
            'value': float(rri),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'recommended_actions': actions,
            'dropout_probability': probability,
            'components': details,
            'sub_indices': {
                'disengagement_velocity': dvi_result,
                'academic_instability': aii_result,
                'routine_strength': rsi_result
            }
        }
