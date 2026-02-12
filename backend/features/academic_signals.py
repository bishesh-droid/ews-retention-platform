"""
Academic Performance Signal Computation
"""
from typing import Dict, Optional, List
import numpy as np
from datetime import datetime

from backend.features.signal_computer import SignalComputer


class AcademicPerformanceSignal(SignalComputer):
    """Compute academic performance risk signal"""
    
    def __init__(self):
        weights = {
            'quiz_completion_rate': 0.3,
            'quiz_average_score': 0.3,
            'exam_participation': 0.2,
            'exam_score': 0.2
        }
        super().__init__(weights)
    
    def compute(self, db_session, student_id: str, trimester: str) -> Dict:
        """
        Compute academic performance signal
        
        Returns:
            {
                'signal_value': float (0-100),
                'sub_metrics': dict,
                'source_files': list,
                'calculation_date': str
            }
        """
        from backend.database import FactAcademicPerformance
        
        # Query all academic records for student
        records = db_session.query(FactAcademicPerformance).filter_by(
            student_id=student_id
        ).all()
        
        if not records:
            return {'signal_value': None, 'reason': 'No data'}
        
        # Separate by assessment type
        quiz_records = [r for r in records if r.assessment_type == 'Quiz']
        exam_records = [r for r in records if r.assessment_type == 'Exam']
        
        # Compute sub-metrics
        sub_metrics = {
            'quiz_completion_rate': self._quiz_completion_rate(quiz_records),
            'quiz_average_score': self._quiz_average_score(quiz_records),
            'exam_participation': self._exam_participation(exam_records),
            'exam_score': self._exam_average_score(exam_records)
        }
        
        signal_value = self.compute_weighted_score(sub_metrics)
        
        # Invert: low performance → high risk
        risk_signal = 100 - signal_value if signal_value is not None else None
        
        return {
            'signal_value': risk_signal,
            'sub_metrics': sub_metrics,
            'source_files': list(set(r.source_file for r in records if r.source_file)),
            'calculation_date': datetime.now().isoformat()
        }
    
    def _quiz_completion_rate(self, records: List) -> Optional[float]:
        """% of quizzes submitted"""
        if not records:
            return None
        submitted = sum(1 for r in records if r.submitted)
        return (submitted / len(records)) * 100
    
    def _quiz_average_score(self, records: List) -> Optional[float]:
        """Average quiz score"""
        scores = [r.percentage for r in records if r.percentage is not None]
        return float(np.mean(scores)) if scores else None
    
    def _exam_participation(self, records: List) -> Optional[float]:
        """Exam participation rate"""
        if not records:
            return None
        participated = sum(1 for r in records if r.submitted)
        return (participated / len(records)) * 100
    
    def _exam_average_score(self, records: List) -> Optional[float]:
        """Average exam score"""
        scores = [r.percentage for r in records if r.percentage is not None]
        return float(np.mean(scores)) if scores else None
