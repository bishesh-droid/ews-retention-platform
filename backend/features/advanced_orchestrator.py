"""
Advanced Features Orchestrator
Master interface for computing all 36 advanced retention features
"""
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from backend.features.temporal_features import TemporalFeatureComputer
from backend.features.behavioral_features import ConsistencyFeatureComputer, EffortOutcomeFeatureComputer
from backend.features.advanced_engagement_features import (
    EngagementDepthComputer,
    IntentResponsivenessComputer,
    CohortNormalizationComputer
)
from backend.features.composite_indices import CompositeIndexComputer


class AdvancedFeatureOrchestrator:
    """
    Master orchestrator for all 36 advanced retention prediction features
    
    Feature Categories:
    1. Temporal & Trend (6 features)
    2. Consistency & Habits (5 features)
    3. Effort-Outcome Mismatch (4 features)
    4. Engagement Depth (4 features)
    5. Intent & Commitment (3 features)
    6. Responsiveness (3 features)
    7. Cohort Normalization (4 features)
    8. Composite Indices (4 indices)
    
    Total: 33 base features + 4 composite indices = 37 outputs
    """
    
    def __init__(self):
        self.temporal = TemporalFeatureComputer()
        self.consistency = ConsistencyFeatureComputer()
        self.effort = EffortOutcomeFeatureComputer()
        self.engagement_depth = EngagementDepthComputer()
        self.intent_resp = IntentResponsivenessComputer()
        self.cohort_norm = CohortNormalizationComputer()
        self.composite = CompositeIndexComputer()
    
    def compute_all_features(
        self,
        db: Session,
        student_id: str,
        cohort_id: Optional[str] = None,
        include_cohort_features: bool = False
    ) -> Dict:
        """
        Compute all advanced features for a student
        
        Args:
            db: Database session
            student_id: Student identifier
            cohort_id: Cohort/trimester for normalization
            include_cohort_features: Include cohort-normalized features (faculty-only)
        
        Returns:
            Complete feature dictionary with all 36+ features
        """
        result = {
            'student_id': student_id,
            'computation_timestamp': datetime.now().isoformat(),
            'feature_version': '1.0.0'
        }
        
        # Category 1: Temporal & Trend Features
        result['temporal_features'] = self.temporal.compute_all(db, student_id)
        
        # Category 2: Consistency & Habits
        result['consistency_features'] = self.consistency.compute_all(db, student_id)
        
        # Category 3: Effort-Outcome Mismatch
        result['effort_outcome_features'] = self.effort.compute_all(db, student_id)
        
        # Category 4: Engagement Depth
        result['engagement_depth_features'] = self.engagement_depth.compute_all(db, student_id)
        
        # Category 5-6: Intent & Responsiveness
        result['intent_responsiveness_features'] = self.intent_resp.compute_all(db, student_id)
        
        # Category 7: Cohort Normalization (if requested and cohort_id provided)
        if include_cohort_features and cohort_id:
            result['cohort_features'] = self.cohort_norm.compute_all(db, student_id, cohort_id)
            result['privacy_warning'] = 'COHORT FEATURES INCLUDED - FACULTY USE ONLY'
        else:
            result['cohort_features'] = {'note': 'Not computed - requires faculty access'}
        
        # Category 8: Composite Indices
        result['composite_indices'] = self.composite.compute_all(db, student_id, cohort_id)
        
        # Summary statistics
        result['summary'] = self._generate_summary(result)
        
        return result
    
    def compute_risk_summary(self, db: Session, student_id: str, cohort_id: Optional[str] = None) -> Dict:
        """
        Compute only the high-level risk summary (for dashboard display)
        
        Returns:
            {
                'retention_risk_index': RRI object,
                'disengagement_velocity_index': DVI object,
                'academic_instability_index': AII object,
                'routine_strength_index': RSI object,
                'key_risk_factors': list,
                'recommendations': list
            }
        """
        # Get all features
        all_features = self.compute_all_features(db, student_id, cohort_id)
        
        # Extract indices
        indices = all_features['composite_indices']
        
        # Identify key risk factors
        risk_factors = []
        
        # Check temporal risks
        temporal = all_features['temporal_features']
        if temporal.get('engagement_decay_rate', {}).get('risk_level') == 'high':
            risk_factors.append("Rapid engagement decline")
        if temporal.get('academic_grade_trend_slope', {}).get('risk_level') == 'high':
            risk_factors.append("Declining academic performance")
        if temporal.get('engagement_longest_inactivity_days', {}).get('risk_level') == 'high':
            risk_factors.append("Extended inactivity periods")
        
        # Check consistency risks
        consistency = all_features['consistency_features']
        if consistency.get('consistency_login_regularity_score', {}).get('risk_level') == 'high':
            risk_factors.append("Irregular study routine")
        if consistency.get('consistency_study_streak_days', {}).get('risk_level') == 'high':
            risk_factors.append("No established habit")
        
        # Check responsiveness risks
        intent_resp = all_features['intent_responsiveness_features']
        escalations = intent_resp.get('responsiveness_ignored_escalation_count', {})
        if escalations.get('value', 0) > 0:
            risk_factors.append(f"{escalations['value']} ignored urgent messages")
        
        return {
            'retention_risk_index': indices.get('retention_risk_index'),
            'disengagement_velocity_index': indices.get('disengagement_velocity_index'),
            'academic_instability_index': indices.get('academic_instability_index'),
            'routine_strength_index': indices.get('routine_strength_index'),
            'key_risk_factors': risk_factors[:5],  # Top 5
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_summary(self, features: Dict) -> Dict:
        """Generate summary statistics from all features"""
        high_risk_count = 0
        medium_risk_count = 0
        low_risk_count = 0
        unknown_count = 0
        
        # Count risk levels across all features
        for category in ['temporal_features', 'consistency_features', 'effort_outcome_features',
                        'engagement_depth_features', 'intent_responsiveness_features']:
            if category in features:
                for feature_name, feature_data in features[category].items():
                    if isinstance(feature_data, dict) and 'risk_level' in feature_data:
                        risk = feature_data['risk_level']
                        if risk == 'high' or risk == 'critical':
                            high_risk_count += 1
                        elif risk == 'medium':
                            medium_risk_count += 1
                        elif risk == 'low':
                            low_risk_count += 1
                        else:
                            unknown_count += 1
        
        total_features = high_risk_count + medium_risk_count + low_risk_count + unknown_count
        
        return {
            'total_features_computed': total_features,
            'high_risk_signals': high_risk_count,
            'medium_risk_signals': medium_risk_count,
            'low_risk_signals': low_risk_count,
            'insufficient_data_count': unknown_count,
            'overall_risk_assessment': self._assess_overall_risk(high_risk_count, medium_risk_count, total_features)
        }
    
    def _assess_overall_risk(self, high_count: int, medium_count: int, total: int) -> str:
        """Assess overall risk based on signal distribution"""
        if total == 0:
            return 'unknown'
        
        high_pct = (high_count / total) * 100
        
        if high_pct > 40:
            return 'critical'
        elif high_pct > 25:
            return 'high'
        elif high_pct > 10 or (medium_count / total) > 0.5:
            return 'medium'
        else:
            return 'low'


def compute_advanced_features(db: Session, student_id: str, cohort_id: Optional[str] = None) -> Dict:
    """
    Convenience function to compute all advanced features
    
    Usage:
        from backend.features.advanced_orchestrator import compute_advanced_features
        
        features = compute_advanced_features(db, 'student@example.com', 'T2_2026')
        
        # Access specific features
        grade_trend = features['temporal_features']['academic_grade_trend_slope']
        rri = features['composite_indices']['retention_risk_index']
    """
    orchestrator = AdvancedFeatureOrchestrator()
    return orchestrator.compute_all_features(db, student_id, cohort_id)
