"""
Consistency & Habit Formation Features
Measure routine strength and behavioral stability
"""
from typing import Dict, Optional, List
import numpy as np
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session


class ConsistencyFeatureComputer:
    """Compute consistency and habit-related retention features"""
    
    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days
    
    def compute_all(self, db: Session, student_id: str) -> Dict:
        """Compute all consistency features"""
        return {
            'consistency_login_regularity_score': self.login_regularity_score(db, student_id),
            'consistency_study_streak_days': self.study_streak_strength(db, student_id),
            'consistency_recovery_speed_days': self.recovery_speed(db, student_id),
            'consistency_weekend_weekday_ratio': self.weekend_weekday_ratio(db, student_id),
            'consistency_late_night_ratio': self.late_night_ratio(db, student_id),
            'computation_timestamp': datetime.now().isoformat()
        }
    
    def login_regularity_score(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 2.1: Login Regularity Score
        
        Consistency of login timing across days (0-100)
        Lower variance = higher regularity = stronger habit
        """
        from backend.database import FactEngagement
        from sqlalchemy import func
        
        cutoff_date = date.today() - timedelta(days=self.lookback_days)
        
        # Get daily login counts
        daily_logins = db.query(
            FactEngagement.metric_date,
            func.sum(FactEngagement.login_count).label('daily_count')
        ).filter(
            FactEngagement.student_id == student_id,
            FactEngagement.metric_date >= cutoff_date
        ).group_by(
            FactEngagement.metric_date
        ).all()
        
        if len(daily_logins) < 7:
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown'
            }
        
        login_counts = [count for _, count in daily_logins if count]
        
        if not login_counts or np.mean(login_counts) == 0:
            return {
                'value': 0,
                'interpretation': 'No login activity',
                'risk_level': 'critical'
            }
        
        # Coefficient of variation
        cv = np.std(login_counts) / np.mean(login_counts)
        
        # Convert to regularity score (inverse of variation)
        regularity_score = max(0, 100 - (cv * 100))
        
        # Interpretation
        if regularity_score > 70:
            interpretation = f"Highly regular routine (score: {regularity_score:.0f})"
            risk_level = 'low'
        elif regularity_score > 40:
            interpretation = f"Moderate regularity (score: {regularity_score:.0f})"
            risk_level = 'medium'
        else:
            interpretation = f"Irregular/sporadic (score: {regularity_score:.0f})"
            risk_level = 'high'
        
        return {
            'value': float(regularity_score),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'coefficient_variation': float(cv),
            'avg_daily_logins': float(np.mean(login_counts))
        }
    
    def study_streak_strength(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 2.2: Study Streak Strength
        
        Current consecutive days with meaningful activity (>20 min platform time)
        """
        from backend.database import FactEngagement
        
        # Get recent engagement data
        engagements = db.query(FactEngagement).filter(
            FactEngagement.student_id == student_id,
            FactEngagement.metric_date >= date.today() - timedelta(days=60)
        ).order_by(
            FactEngagement.metric_date.desc()
        ).all()
        
        if not engagements:
            return {
                'value': 0,
                'interpretation': 'No activity',
                'risk_level': 'critical'
            }
        
        # Calculate current streak
        streak = 0
        meaningful_threshold = 20  # minutes
        
        for engagement in engagements:
            if (engagement.total_time_minutes or 0) >= meaningful_threshold:
                streak += 1
            else:
                break  # Streak broken
        
        # Interpretation
        if streak >= 14:
            interpretation = f"Strong habit ({streak} day streak 🔥)"
            risk_level = 'low'
        elif streak >= 7:
            interpretation = f"Moderate habit ({streak} day streak)"
            risk_level = 'medium'
        else:
            interpretation = f"Weak/no habit ({streak} day streak)"
            risk_level = 'high'
        
        return {
            'value': streak,
            'interpretation': interpretation,
            'risk_level': risk_level,
            'threshold_minutes': meaningful_threshold
        }
    
    def recovery_speed(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 2.3: Recovery Speed After Inactivity
        
        Average days to return to baseline activity after 5+ day gaps
        """
        from backend.database import FactEngagement
        from sqlalchemy import func
        
        # Get daily activity levels
        daily_activity = db.query(
            FactEngagement.metric_date,
            func.sum(FactEngagement.total_time_minutes).label('daily_minutes')
        ).filter(
            FactEngagement.student_id == student_id,
            FactEngagement.metric_date >= date.today() - timedelta(days=90)
        ).group_by(
            FactEngagement.metric_date
        ).order_by(
            FactEngagement.metric_date
        ).all()
        
        if len(daily_activity) < 14:
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown'
            }
        
        # Calculate baseline (median of active days)
        active_days = [minutes for _, minutes in daily_activity if minutes and minutes > 0]
        baseline_activity = np.median(active_days) if active_days else 0
        
        # Find gaps of 5+ days
        dates = [d for d, _ in daily_activity]
        recovery_speeds = []
        
        for i in range(1, len(dates)):
            gap = (dates[i] - dates[i-1]).days
            
            if gap >= 5:
                # Found a gap, now measure recovery time
                recovery_days = 0
                for j in range(i, min(i + 14, len(daily_activity))):
                    _, minutes = daily_activity[j]
                    if (minutes or 0) >= baseline_activity * 0.8:
                        recovery_days = j - i
                        break
                
                if recovery_days > 0:
                    recovery_speeds.append(recovery_days)
        
        if not recovery_speeds:
            return {
                'value': None,
                'interpretation': 'No recovery events to measure',
                'risk_level': 'medium'
            }
        
        avg_recovery = float(np.mean(recovery_speeds))
        
        # Interpretation
        if avg_recovery < 2:
            interpretation = f"Quick recovery ({avg_recovery:.1f} days avg)"
            risk_level = 'low'
        elif avg_recovery < 5:
            interpretation = f"Moderate recovery ({avg_recovery:.1f} days avg)"
            risk_level = 'medium'
        else:
            interpretation = f"Slow recovery ({avg_recovery:.1f} days avg)"
            risk_level = 'high'
        
        return {
            'value': avg_recovery,
            'interpretation': interpretation,
            'risk_level': risk_level,
            'recovery_events': len(recovery_speeds),
            'baseline_activity_minutes': float(baseline_activity)
        }
    
    def weekend_weekday_ratio(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 2.4: Weekend vs Weekday Activity Ratio
        
        Ratio of weekend activity to weekday activity
        """
        from backend.database import FactEngagement
        from sqlalchemy import func, extract
        
        cutoff_date = date.today() - timedelta(days=self.lookback_days)
        
        engagements = db.query(
            FactEngagement.metric_date,
            FactEngagement.total_time_minutes
        ).filter(
            FactEngagement.student_id == student_id,
            FactEngagement.metric_date >= cutoff_date
        ).all()
        
        if not engagements:
            return {
                'value': None,
                'interpretation': 'No activity data',
                'risk_level': 'critical'
            }
        
        weekday_time = 0
        weekend_time = 0
        
        for dt, minutes in engagements:
            if minutes:
                # weekday() returns 5,6 for Saturday, Sunday
                if dt.weekday() >= 5:
                    weekend_time += minutes
                else:
                    weekday_time += minutes
        
        if weekday_time == 0:
            return {
                'value': None,
                'interpretation': 'No weekday activity',
                'risk_level': 'critical'
            }
        
        ratio = weekend_time / weekday_time
        
        # Interpretation
        if ratio > 0.5:
            interpretation = f"Balanced study across week (ratio: {ratio:.2f})"
            risk_level = 'low'
        elif ratio > 0.2:
            interpretation = f"Weekend catch-up pattern (ratio: {ratio:.2f})"
            risk_level = 'medium'
        else:
            interpretation = f"Weekend disengagement (ratio: {ratio:.2f})"
            risk_level = 'high'
        
        return {
            'value': float(ratio),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'weekday_minutes': weekday_time,
            'weekend_minutes': weekend_time
        }
    
    def late_night_ratio(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 2.5: Late-Night Activity Ratio
        
        Percentage of activity occurring 11pm-5am (burnout indicator)
        
        Note: Requires session timestamps from raw event logs
        """
        # This would ideally use detailed session timestamps
        # For now, returning placeholder structure
        
        # TODO: Implement when raw event logs with timestamps are available
        
        return {
            'value': None,
            'interpretation': 'Requires detailed session timestamps',
            'risk_level': 'unknown',
            'note': 'Feature requires raw platform event logs with hour-level granularity'
        }


class EffortOutcomeFeatureComputer:
    """Compute effort vs outcome mismatch features"""
    
    def compute_all(self, db: Session, student_id: str) -> Dict:
        """Compute all effort-outcome features"""
        return {
            'effort_time_to_score_ratio': self.time_to_score_ratio(db, student_id),
            'effort_retake_improvement_rate': self.retake_improvement(db, student_id),
            'effort_practice_exam_gap': self.practice_exam_gap(db, student_id),
            'effort_procrastination_index': self.procrastination_index(db, student_id),
            'computation_timestamp': datetime.now().isoformat()
        }
    
    def time_to_score_ratio(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 3.1: Time-Spent-to-Score Ratio
        
        Platform time invested per percentage point earned (minutes/point)
        """
        from backend.database import FactAcademicPerformance, FactEngagement
        
        # Get recent assessments
        assessments = db.query(FactAcademicPerformance).filter(
            FactAcademicPerformance.student_id == student_id,
            FactAcademicPerformance.submitted == True,
            FactAcademicPerformance.percentage.isnot(None),
            FactAcademicPerformance.assessment_date >= date.today() - timedelta(days=60)
        ).all()
        
        if not assessments:
            return {
                'value': None,
                'interpretation': 'No recent assessments',
                'risk_level': 'unknown'
            }
        
        ratios = []
        
        for assessment in assessments:
            # Get study time in 7 days before assessment
            study_start = assessment.assessment_date - timedelta(days=7)
            
            study_time = db.query(FactEngagement).filter(
                FactEngagement.student_id == student_id,
                FactEngagement.metric_date >= study_start,
                FactEngagement.metric_date < assessment.assessment_date
            ).all()
            
            total_study_minutes = sum(e.total_time_minutes or 0 for e in study_time)
            
            if assessment.percentage > 0:
                ratio = total_study_minutes / assessment.percentage
                ratios.append(ratio)
        
        if not ratios:
            return {
                'value': None,
                'interpretation': 'Unable to compute',
                'risk_level': 'unknown'
            }
        
        avg_ratio = float(np.mean(ratios))
        
        # Interpretation
        if avg_ratio < 5:
            interpretation = f"Efficient learning ({avg_ratio:.1f} min/point)"
            risk_level = 'low'
        elif avg_ratio < 10:
            interpretation = f"Average efficiency ({avg_ratio:.1f} min/point)"
            risk_level = 'medium'
        else:
            interpretation = f"Low ROI ({avg_ratio:.1f} min/point)"
            risk_level = 'high'
        
        return {
            'value': avg_ratio,
            'interpretation': interpretation,
            'risk_level': risk_level,
            'assessments_analyzed': len(ratios)
        }
    
    def retake_improvement(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 3.2: Retake Improvement Rate
        
        Average improvement on retaken assessments
        
        Note: Requires attempt_number field in fact_academic_performance
        """
        # TODO: Add attempt_number to schema if needed
        
        return {
            'value': None,
            'interpretation': 'Requires attempt tracking in data model',
            'risk_level': 'unknown',
            'note': 'Feature requires assessment attempt number field'
        }
    
    def practice_exam_gap(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 3.3: Practice vs Exam Performance Gap
        
        Difference between quiz average and exam score
        """
        from backend.database import FactAcademicPerformance
        
        # Get quizzes and exams
        quizzes = db.query(FactAcademicPerformance).filter(
            FactAcademicPerformance.student_id == student_id,
            FactAcademicPerformance.assessment_type == 'Quiz',
            FactAcademicPerformance.percentage.isnot(None)
        ).all()
        
        exams = db.query(FactAcademicPerformance).filter(
            FactAcademicPerformance.student_id == student_id,
            FactAcademicPerformance.assessment_type == 'Exam',
            FactAcademicPerformance.percentage.isnot(None)
        ).all()
        
        if not quizzes or not exams:
            return {
                'value': None,
                'interpretation': 'Insufficient assessment data',
                'risk_level': 'unknown'
            }
        
        quiz_avg = float(np.mean([q.percentage for q in quizzes]))
        exam_avg = float(np.mean([e.percentage for e in exams]))
        
        gap = quiz_avg - exam_avg
        
        # Interpretation
        if gap < 10:
            interpretation = f"Consistent performance (gap: {gap:+.1f}%)"
            risk_level = 'low'
        elif gap < 20:
            interpretation = f"Moderate gap ({gap:+.1f}%)"
            risk_level = 'medium'
        else:
            interpretation = f"Large performance gap ({gap:+.1f}%)"
            risk_level = 'high'
        
        return {
            'value': float(gap),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'quiz_avg': quiz_avg,
            'exam_avg': exam_avg
        }
    
    def procrastination_index(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 3.4: Assessment Procrastination Index
        
        Percentage of assignments submitted in last 20% of deadline window
        
        Note: Requires submission and deadline timestamps
        """
        from backend.database import FactAcademicPerformance
        
        # Check if we have late_submission data as proxy
        assessments = db.query(FactAcademicPerformance).filter(
            FactAcademicPerformance.student_id == student_id,
            FactAcademicPerformance.submitted == True
        ).all()
        
        if not assessments:
            return {
                'value': None,
                'interpretation': 'No submission data',
                'risk_level': 'unknown'
            }
        
        # Use late_submission as proxy indicator
        late_count = sum(1 for a in assessments if a.late_submission)
        total_count = len(assessments)
        
        procrastination_pct = (late_count / total_count) * 100
        
        # Interpretation
        if procrastination_pct < 20:
            interpretation = f"Good planning ({procrastination_pct:.0f}% late)"
            risk_level = 'low'
        elif procrastination_pct < 50:
            interpretation = f"Moderate procrastination ({procrastination_pct:.0f}% late)"
            risk_level = 'medium'
        else:
            interpretation = f"Chronic procrastination ({procrastination_pct:.0f}% late)"
            risk_level = 'high'
        
        return {
            'value': float(procrastination_pct),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'late_submissions': late_count,
            'total_submissions': total_count,
            'note': 'Using late_submission flag as proxy for last-minute pattern'
        }
