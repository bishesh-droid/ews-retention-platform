"""
Temporal & Trend-Based Features
Detect deteriorating patterns before they become critical
"""
from typing import Dict, Optional, List, Tuple
import numpy as np
from datetime import datetime, date, timedelta
from scipy.stats import linregress
from sqlalchemy.orm import Session


class TemporalFeatureComputer:
    """Compute temporal and trend-based retention features"""
    
    def __init__(self, lookback_days: int = 30, min_data_points: int = 3):
        """
        Args:
            lookback_days: Days of history to analyze
            min_data_points: Minimum data points required for trend analysis
        """
        self.lookback_days = lookback_days
        self.min_data_points = min_data_points
    
    def compute_all(self, db: Session, student_id: str) -> Dict:
        """
        Compute all temporal features for a student
        
        Returns:
            Dictionary with all temporal feature values and metadata
        """
        return {
            'academic_grade_trend_slope': self.grade_trend_slope(db, student_id),
            'academic_score_volatility': self.score_volatility(db, student_id),
            'academic_recent_vs_historical_delta': self.recent_vs_historical_delta(db, student_id),
            'engagement_decay_rate': self.engagement_decay_rate(db, student_id),
            'engagement_longest_inactivity_days': self.longest_inactivity_gap(db, student_id),
            'engagement_session_frequency_trend': self.session_frequency_trend(db, student_id),
            'computation_timestamp': datetime.now().isoformat()
        }
    
    def grade_trend_slope(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 1.1: Grade Trend Slope
        
        Linear regression slope of assessment scores over last 5 assessments
        
        Returns:
            {
                'value': float (points per day),
                'interpretation': str,
                'risk_level': str,
                'data_points': int,
                'r_squared': float
            }
        """
        from backend.database import FactAcademicPerformance
        
        # Query last 5 submitted assessments
        assessments = db.query(FactAcademicPerformance).filter(
            FactAcademicPerformance.student_id == student_id,
            FactAcademicPerformance.submitted == True,
            FactAcademicPerformance.percentage.isnot(None)
        ).order_by(
            FactAcademicPerformance.assessment_date.desc()
        ).limit(5).all()
        
        if len(assessments) < self.min_data_points:
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown',
                'data_points': len(assessments)
            }
        
        # Prepare data for regression
        dates = [a.assessment_date for a in reversed(assessments)]
        scores = [a.percentage for a in reversed(assessments)]
        
        # Convert dates to numeric (days since first assessment)
        min_date = min(dates)
        dates_numeric = [(d - min_date).days for d in dates]
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = linregress(dates_numeric, scores)
        
        # Interpretation
        if slope > 0.5:
            interpretation = f"Improving (+{slope:.2f}%/day)"
            risk_level = 'low'
        elif slope > -0.5:
            interpretation = f"Stable ({slope:.2f}%/day)"
            risk_level = 'medium'
        else:
            interpretation = f"Declining ({slope:.2f}%/day)"
            risk_level = 'high'
        
        return {
            'value': float(slope),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'data_points': len(assessments),
            'r_squared': float(r_value ** 2),
            'recent_scores': scores[-3:]  # Last 3 for context
        }
    
    def score_volatility(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 1.2: Assessment Score Volatility
        
        Standard deviation of last 5 assessment scores
        
        Returns:
            {
                'value': float (standard deviation),
                'interpretation': str,
                'risk_level': str,
                'coefficient_variation': float
            }
        """
        from backend.database import FactAcademicPerformance
        
        assessments = db.query(FactAcademicPerformance).filter(
            FactAcademicPerformance.student_id == student_id,
            FactAcademicPerformance.submitted == True,
            FactAcademicPerformance.percentage.isnot(None)
        ).order_by(
            FactAcademicPerformance.assessment_date.desc()
        ).limit(5).all()
        
        if len(assessments) < self.min_data_points:
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown'
            }
        
        scores = [a.percentage for a in assessments]
        
        volatility = float(np.std(scores))
        mean_score = float(np.mean(scores))
        cv = (volatility / mean_score) if mean_score > 0 else 0
        
        # Interpretation
        if volatility < 5:
            interpretation = f"Consistent (SD={volatility:.1f})"
            risk_level = 'low'
        elif volatility < 15:
            interpretation = f"Moderate variability (SD={volatility:.1f})"
            risk_level = 'medium'
        else:
            interpretation = f"Unstable (SD={volatility:.1f})"
            risk_level = 'high'
        
        return {
            'value': volatility,
            'interpretation': interpretation,
            'risk_level': risk_level,
            'coefficient_variation': float(cv),
            'mean_score': mean_score,
            'score_range': [float(min(scores)), float(max(scores))]
        }
    
    def recent_vs_historical_delta(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 1.3: Recent vs Historical Performance Delta
        
        Difference between recent (last 3) and historical average
        
        Returns:
            {
                'value': float (percentage point difference),
                'interpretation': str,
                'risk_level': str,
                'recent_avg': float,
                'historical_avg': float
            }
        """
        from backend.database import FactAcademicPerformance
        
        all_assessments = db.query(FactAcademicPerformance).filter(
            FactAcademicPerformance.student_id == student_id,
            FactAcademicPerformance.submitted == True,
            FactAcademicPerformance.percentage.isnot(None)
        ).order_by(
            FactAcademicPerformance.assessment_date.desc()
        ).all()
        
        if len(all_assessments) < 6:  # Need at least 6 for meaningful comparison
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown'
            }
        
        recent_scores = [a.percentage for a in all_assessments[:3]]
        historical_scores = [a.percentage for a in all_assessments[3:]]
        
        recent_avg = float(np.mean(recent_scores))
        historical_avg = float(np.mean(historical_scores))
        delta = recent_avg - historical_avg
        
        # Interpretation
        if delta > 10:
            interpretation = f"Recent surge (+{delta:.1f}%)"
            risk_level = 'low'
        elif delta > -10:
            interpretation = f"Stable ({delta:+.1f}%)"
            risk_level = 'medium'
        else:
            interpretation = f"Recent decline ({delta:.1f}%)"
            risk_level = 'high'
        
        return {
            'value': float(delta),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'recent_avg': recent_avg,
            'historical_avg': historical_avg,
            'recent_scores': recent_scores
        }
    
    def engagement_decay_rate(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 1.4: Engagement Decay Rate
        
        Week-over-week percentage decline in platform time
        
        Returns:
            {
                'value': float (average weekly % change),
                'interpretation': str,
                'risk_level': str,
                'weekly_times': list
            }
        """
        from backend.database import FactEngagement
        
        cutoff_date = date.today() - timedelta(days=28)  # 4 weeks
        
        # Get weekly engagement totals
        engagements = db.query(
            FactEngagement.metric_week,
            FactEngagement.total_time_minutes
        ).filter(
            FactEngagement.student_id == student_id,
            FactEngagement.metric_date >= cutoff_date
        ).all()
        
        if len(engagements) < 4:
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown'
            }
        
        # Aggregate by week
        weekly_times = {}
        for week, minutes in engagements:
            if week not in weekly_times:
                weekly_times[week] = 0
            weekly_times[week] += minutes or 0
        
        # Calculate week-over-week changes
        sorted_weeks = sorted(weekly_times.keys())
        weekly_changes = []
        
        for i in range(1, len(sorted_weeks)):
            prev_time = weekly_times[sorted_weeks[i-1]]
            curr_time = weekly_times[sorted_weeks[i]]
            
            if prev_time > 0:
                pct_change = ((curr_time - prev_time) / prev_time) * 100
                weekly_changes.append(pct_change)
        
        if not weekly_changes:
            return {'value': None, 'interpretation': 'Unable to compute', 'risk_level': 'unknown'}
        
        decay_rate = float(np.mean(weekly_changes))
        
        # Interpretation
        if decay_rate > 5:
            interpretation = f"Increasing engagement (+{decay_rate:.1f}%/week)"
            risk_level = 'low'
        elif decay_rate > -10:
            interpretation = f"Stable ({decay_rate:+.1f}%/week)"
            risk_level = 'medium'
        else:
            interpretation = f"Rapid disengagement ({decay_rate:.1f}%/week)"
            risk_level = 'high'
        
        return {
            'value': decay_rate,
            'interpretation': interpretation,
            'risk_level': risk_level,
            'weekly_times': [weekly_times[w] for w in sorted_weeks],
            'trend_direction': 'declining' if decay_rate < -5 else 'stable' if decay_rate < 5 else 'improving'
        }
    
    def longest_inactivity_gap(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 1.5: Longest Inactivity Gap
        
        Maximum consecutive days without platform login in last 30 days
        
        Returns:
            {
                'value': int (days),
                'interpretation': str,
                'risk_level': str,
                'gap_start_date': str,
                'gap_end_date': str
            }
        """
        from backend.database import FactEngagement
        from sqlalchemy import func, distinct
        
        cutoff_date = date.today() - timedelta(days=30)
        
        # Get distinct login dates
        login_dates = db.query(
            distinct(FactEngagement.metric_date)
        ).filter(
            FactEngagement.student_id == student_id,
            FactEngagement.metric_date >= cutoff_date,
            FactEngagement.login_count > 0
        ).order_by(
            FactEngagement.metric_date
        ).all()
        
        if len(login_dates) < 2:
            return {
                'value': (date.today() - cutoff_date).days if len(login_dates) == 0 else 0,
                'interpretation': 'No recent activity' if len(login_dates) == 0 else 'Single login',
                'risk_level': 'critical' if len(login_dates) == 0 else 'high'
            }
        
        # Extract dates
        dates = [d[0] for d in login_dates]
        
        # Calculate gaps
        gaps = []
        gap_info = []
        
        for i in range(1, len(dates)):
            gap_days = (dates[i] - dates[i-1]).days - 1
            if gap_days > 0:
                gaps.append(gap_days)
                gap_info.append({
                    'gap_days': gap_days,
                    'start': dates[i-1],
                    'end': dates[i]
                })
        
        if not gaps:
            longest_gap = 0
            longest_gap_info = None
        else:
            longest_gap = max(gaps)
            longest_gap_info = max(gap_info, key=lambda x: x['gap_days'])
        
        # Interpretation
        if longest_gap < 3:
            interpretation = f"Active engagement ({longest_gap} day max gap)"
            risk_level = 'low'
        elif longest_gap < 7:
            interpretation = f"Moderate inactivity ({longest_gap} day gap)"
            risk_level = 'medium'
        else:
            interpretation = f"Extended absence ({longest_gap} day gap)"
            risk_level = 'high'
        
        result = {
            'value': longest_gap,
            'interpretation': interpretation,
            'risk_level': risk_level
        }
        
        if longest_gap_info:
            result.update({
                'gap_start_date': longest_gap_info['start'].isoformat(),
                'gap_end_date': longest_gap_info['end'].isoformat()
            })
        
        return result
    
    def session_frequency_trend(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 1.6: Session Frequency Trend
        
        Slope of logins per week over last 4 weeks
        
        Returns:
            {
                'value': float (logins per week change rate),
                'interpretation': str,
                'risk_level': str,
                'weekly_logins': list
            }
        """
        from backend.database import FactEngagement
        from sqlalchemy import func
        
        cutoff_date = date.today() - timedelta(days=28)
        
        # Get weekly login counts
        weekly_data = db.query(
            FactEngagement.metric_week,
            func.sum(FactEngagement.login_count).label('total_logins')
        ).filter(
            FactEngagement.student_id == student_id,
            FactEngagement.metric_date >= cutoff_date
        ).group_by(
            FactEngagement.metric_week
        ).order_by(
            FactEngagement.metric_week
        ).all()
        
        if len(weekly_data) < self.min_data_points:
            return {
                'value': None,
                'interpretation': 'Insufficient data',
                'risk_level': 'unknown'
            }
        
        weeks = [w[0] for w in weekly_data]
        logins = [w[1] or 0 for w in weekly_data]
        
        # Linear regression
        week_indices = list(range(len(weeks)))
        slope, intercept, r_value, p_value, std_err = linregress(week_indices, logins)
        
        # Interpretation
        if slope > 0.5:
            interpretation = f"Increasing frequency (+{slope:.1f} logins/week)"
            risk_level = 'low'
        elif slope > -1:
            interpretation = f"Stable ({slope:+.1f} logins/week)"
            risk_level = 'medium'
        else:
            interpretation = f"Declining frequency ({slope:.1f} logins/week)"
            risk_level = 'high'
        
        return {
            'value': float(slope),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'weekly_logins': logins,
            'r_squared': float(r_value ** 2)
        }
