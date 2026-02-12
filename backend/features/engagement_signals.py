"""
Engagement Signal Computation
"""
from typing import Dict, Optional, List
import numpy as np
from datetime import datetime

from backend.features.signal_computer import SignalComputer


class EngagementSignal(SignalComputer):
    """Compute engagement risk signal"""
    
    def __init__(self):
        weights = {
            'attendance_rate': 0.5,
            'platform_time': 0.3,
            'content_interaction': 0.2
        }
        super().__init__(weights)
    
    def compute(self, db_session, student_id: str, trimester: str) -> Dict:
        """
        Compute engagement signal
        
        Returns:
            {
                'signal_value': float (0-100),
                'sub_metrics': dict,
                'source_files': list,
                'calculation_date': str
            }
        """
        from backend.database import FactEngagement
        
        records = db_session.query(FactEngagement).filter_by(
            student_id=student_id
        ).all()
        
        if not records:
            return {'signal_value': None, 'reason': 'No data'}
        
        sub_metrics = {
            'attendance_rate': self._avg_attendance(records),
            'platform_time': self._platform_engagement(records),
            'content_interaction': self._content_score(records)
        }
        
        signal_value = self.compute_weighted_score(sub_metrics)
        
        # Invert: low engagement → high risk
        risk_signal = 100 - signal_value if signal_value is not None else None
        
        return {
            'signal_value': risk_signal,
            'sub_metrics': sub_metrics,
            'source_files': list(set(r.source_file for r in records if r.source_file)),
            'calculation_date': datetime.now().isoformat()
        }
    
    def _avg_attendance(self, records: List) -> Optional[float]:
        """Average attendance percentage"""
        rates = [r.attendance_percentage for r in records 
                if r.attendance_percentage is not None]
        return float(np.mean(rates)) if rates else None
    
    def _platform_engagement(self, records: List) -> Optional[float]:
        """Platform time score (normalized to 0-100)"""
        times = [r.total_time_minutes for r in records if r.total_time_minutes]
        if not times:
            return None
        avg_time = np.mean(times)
        # Assume 120 min/week is 100% engagement
        return min(100.0, (float(avg_time) / 120.0) * 100.0)
    
    def _content_score(self, records: List) -> Optional[float]:
        """Content interaction score"""
        views = [r.content_items_viewed for r in records if r.content_items_viewed]
        if not views:
            return None
        avg_views = np.mean(views)
        # Assume 20 items/week is 100%
        return min(100.0, (float(avg_views) / 20.0) * 100.0)
