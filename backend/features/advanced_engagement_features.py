"""
Advanced Engagement, Intent & Responsiveness Features
Depth-focused engagement quality and commitment signals
"""
from typing import Dict, Optional
import numpy as np
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session


class EngagementDepthComputer:
    """Compute engagement depth and quality features"""
    
    def compute_all(self, db: Session, student_id: str) -> Dict:
        """Compute all engagement depth features"""
        return {
            'engagement_active_passive_video_ratio': self.active_passive_video_ratio(db, student_id),
            'engagement_content_revisit_rate': self.content_revisit_rate(db, student_id),
            'engagement_forum_interaction_depth': self.forum_interaction_depth(db, student_id),
            'engagement_assessment_preview_rate': self.assessment_preview_rate(db, student_id),
            'computation_timestamp': datetime.now().isoformat()
        }
    
    def active_passive_video_ratio(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 4.1: Active vs Passive Video Engagement Ratio
        
        Note: Requires detailed video interaction logs
        """
        return {
            'value': None,
            'interpretation': 'Requires video interaction event logs',
            'risk_level': 'unknown',
            'note': 'Needs pause/rewind/speed_change/note events per video'
        }
    
    def content_revisit_rate(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 4.2: Content Revisit Frequency
        
        Percentage of content items accessed 2+ times
        """
        from backend.database import FactEngagement
        from sqlalchemy import func
        
        # Aggregate content views
        content_access = db.query(
            func.count(FactEngagement.engagement_id).label('access_count')
        ).filter(
            FactEngagement.student_id == student_id,
            FactEngagement.content_items_viewed > 0
        ).group_by(
            FactEngagement.metric_date  # Proxy: revisit if viewed on multiple dates
        ).all()
        
        if not content_access:
            return {
                'value': None,
                'interpretation': 'No content access data',
                'risk_level': 'unknown'
            }
        
        # Simplified: Use repeated daily access as proxy for revisit behavior  
        # Full implementation would track individual content_id access patterns
        
        return {
            'value': None,
            'interpretation': 'Requires granular content_id tracking',
            'risk_level': 'unknown',
            'note': 'Full implementation needs content-level access logs'
        }
    
    def forum_interaction_depth(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 4.3: Forum Interaction Depth
        
        Ratio of posts to reads (active contributor vs passive lurker)
        """
        from backend.database import FactEngagement
        from sqlalchemy import func
        
        forum_data = db.query(
            func.sum(FactEngagement.discussion_posts).label('total_posts'),
            func.sum(FactEngagement.discussion_reads).label('total_reads')
        ).filter(
            FactEngagement.student_id == student_id
        ).first()
        
        if not forum_data or not forum_data.total_reads:
            return {
                'value': None,
                'interpretation': 'No forum activity',
                'risk_level': 'high'
            }
        
        posts = forum_data.total_posts or 0
        reads = forum_data.total_reads or 0
        
        if reads == 0:
            return {
                'value': 0,
                'interpretation': 'No forum engagement',
                'risk_level': 'high'
            }
        
        depth_ratio = posts / reads
        
        # Interpretation
        if depth_ratio > 0.1:
            interpretation = f"Active contributor (ratio: {depth_ratio:.3f})"
            risk_level = 'low'
        elif depth_ratio > 0.05:
            interpretation = f"Moderate participation (ratio: {depth_ratio:.3f})"
            risk_level = 'medium'
        else:
            interpretation = f"Passive lurker (ratio: {depth_ratio:.3f})"
            risk_level = 'high'
        
        return {
            'value': float(depth_ratio),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'total_posts': posts,
            'total_reads': reads
        }
    
    def assessment_preview_rate(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 4.4: Assessment Preview-Without-Attempt Behavior
        
        Note: Requires assessment open/view tracking separate from submission
        """
        return {
            'value': None,
            'interpretation': 'Requires assessment view tracking',
            'risk_level': 'unknown',
            'note': 'Needs assessment_opened events separate from submission'
        }


class IntentResponsivenessComputer:
    """Compute intent strength and responsiveness dynamics"""
    
    def compute_all(self, db: Session, student_id: str) -> Dict:
        """Compute all intent and responsiveness features"""
        return {
            'intent_certificate_proximity_engagement': self.certificate_proximity(db, student_id),
            'intent_exam_registration_timeliness': self.exam_registration_timing(db, student_id),
            'intent_course_exploration_score': self.course_exploration(db, student_id),
            'responsiveness_latency_trend': self.response_latency_trend(db, student_id),
            'responsiveness_ignored_escalation_count': self.ignored_escalations(db, student_id),
            'responsiveness_reminder_effectiveness_rate': self.reminder_effectiveness(db, student_id),
            'computation_timestamp': datetime.now().isoformat()
        }
    
    def certificate_proximity(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 5.1: Certificate Proximity Behavior
        
        Engagement change when within 2 weeks of completion
        
        Note: Requires course completion tracking
        """
        return {
            'value': None,
            'interpretation': 'Requires completion percentage tracking',
            'risk_level': 'unknown',
            'note': 'Needs module/content completion progress data'
        }
    
    def exam_registration_timing(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 5.2: Exam Registration Timeliness
        
        Note: Requires exam registration event tracking
        """
        return {
            'value': None,
            'interpretation': 'Requires registration event logs',
            'risk_level': 'unknown',
            'note': 'Needs exam_registration_date and exam_deadline fields'
        }
    
    def course_exploration(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 5.3: Course Exploration Depth
        
        Percentage of optional/supplementary content explored
        
        Note: Requires content categorization (required vs optional)
        """
        return {
            'value': None,
            'interpretation': 'Requires content type classification',
            'risk_level': 'unknown',
            'note': 'Needs is_optional/is_supplementary content flags'
        }
    
    def response_latency_trend(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 6.1: Response Latency Trend
        
        Slope of average response time over last 5 communications
        """
        from backend.database import FactIntentResponsiveness
        
        # Query last 5 submitted responsiveness records  
        try:
            responses = db.query(FactIntentResponsiveness).filter(
                FactIntentResponsiveness.student_id == student_id,
                FactIntentResponsiveness.response_time_hours.isnot(None)
            ).order_by(
                FactIntentResponsiveness.message_sent_date.desc()
            ).limit(5).all()
        except:
            return {
                'value': None,
                'interpretation': 'fact_intent_responsiveness table not available',
                'risk_level': 'unknown'
            }
        
        if len(responses) < 3:
            return {
                'value': None,
                'interpretation': 'Insufficient communication data',
                'risk_level': 'unknown'
            }
        
        # Get response times in chronological order
        latencies = [r.response_time_hours for r in reversed(responses)]
        
        # Linear regression slope
        from scipy.stats import linregress
        indices = list(range(len(latencies)))
        slope, _, r_value, _, _ = linregress(indices, latencies)
        
        # Interpretation
        if slope < 1:
            interpretation = f"Maintaining responsiveness ({slope:+.1f} hrs/msg)"
            risk_level = 'low'
        elif slope < 5:
            interpretation = f"Moderate delay increase ({slope:+.1f} hrs/msg)"
            risk_level = 'medium'
        else:
            interpretation = f"Rapid responsiveness decline ({slope:+.1f} hrs/msg)"
            risk_level = 'high'
        
        return {
            'value': float(slope),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'recent_latencies': latencies,
            'r_squared': float(r_value ** 2)
        }
    
    def ignored_escalations(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 6.3: Ignored Escalation Count
        
        Number of escalated (urgent) messages ignored
        """
        from backend.database import FactIntentResponsiveness
        
        # Note: Current schema doesn't have message priority/escalation tracking
        # Using support_emails_read as proxy
        try:
            records = db.query(FactIntentResponsiveness).filter(
                FactIntentResponsiveness.student_id == student_id
            ).all()
            
            # Proxy: lack of email opens despite sends
            ignored_count = sum(1 for r in records if r.welcome_email_opened == False)
        except:
            return {
                'value': None,
                'interpretation': 'Escalation tracking not available',
                'risk_level': 'unknown'
            }
        
        # Interpretation
        if ignored_count == 0:
            interpretation = "Responding to escalations"
            risk_level = 'low'
        elif ignored_count <= 2:
            interpretation = f"Some ignored escalations ({ignored_count})"
            risk_level = 'medium'
        else:
            interpretation = f"Systematic avoidance ({ignored_count} ignored)"
            risk_level = 'critical'
        
        return {
            'value': ignored_count,
            'interpretation': interpretation,
            'risk_level': risk_level
        }
    
    def reminder_effectiveness(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 6.4: Reminder Effectiveness Curve
        
        Percentage of reminders triggering action within 48h
        
        Note: Requires reminder→action correlation tracking
        """
        return {
            'value': None,
            'interpretation': 'Requires reminder outcome tracking',
            'risk_level': 'unknown',
            'note': 'Needs reminder_id linked to subsequent_login_within_48h'
        }


class CohortNormalizationComputer:
    """Compute peer-relative (cohort-normalized) features"""
    
    def __init__(self, cohort_field: str = 'trimester'):
        self.cohort_field = cohort_field
    
    def compute_all(self, db: Session, student_id: str, cohort_id: str) -> Dict:
        """Compute all cohort-normalized features"""
        return {
            'cohort_performance_percentile': self.performance_percentile(db, student_id, cohort_id),
            'cohort_engagement_deviation': self.engagement_deviation(db, student_id, cohort_id),
            'cohort_churn_similarity_score': self.churn_similarity(db, student_id),
            'cohort_difficulty_adjusted_score': self.difficulty_adjusted_score(db, student_id, cohort_id),
            'computation_timestamp': datetime.now().isoformat(),
            'privacy_note': 'FACULTY ONLY - Never shown to students'
        }
    
    def performance_percentile(self, db: Session, student_id: str, cohort_id: str) -> Optional[Dict]:
        """
        Feature 7.1: Performance Percentile Within Cohort
        
        Student's performance percentile within same trimester/program
        
        SAFEGUARD: Faculty-only, never shown to students
        """
        from backend.database import FactAcademicPerformance
        from sqlalchemy import func
        
        # Student's average
        student_avg = db.query(
            func.avg(FactAcademicPerformance.percentage)
        ).filter(
            FactAcademicPerformance.student_id == student_id,
            FactAcademicPerformance.percentage.isnot(None)
        ).scalar()
        
        if not student_avg:
            return {
                'value': None,
                'interpretation': 'No performance data',
                'risk_level': 'unknown',
                'privacy_level': 'FACULTY_ONLY'
            }
        
        # Cohort averages
        cohort_avgs = db.query(
            FactAcademicPerformance.student_id,
            func.avg(FactAcademicPerformance.percentage).label('avg_score')
        ).join(
            FactAcademicPerformance.student_id
        ).filter(
            FactAcademicPerformance.trimester == cohort_id
        ).group_by(
            FactAcademicPerformance.student_id
        ).all()
        
        if len(cohort_avgs) < 10:
            return {
                'value': None,
                'interpretation': 'Cohort too small for comparison',
                'risk_level': 'unknown',
                'privacy_level': 'FACULTY_ONLY'
            }
        
        # Calculate percentile
        cohort_scores = [avg for _, avg in cohort_avgs if avg]
        percentile = (sum(1 for score in cohort_scores if score < student_avg) / len(cohort_scores)) * 100
        
        # Interpretation
        if percentile > 75:
            interpretation = f"Above average ({percentile:.0f}th percentile)"
            risk_level = 'low'
        elif percentile > 25:
            interpretation = f"Average range ({percentile:.0f}th percentile)"
            risk_level = 'medium'
        else:
            interpretation = f"Below average ({percentile:.0f}th percentile)"  
            risk_level = 'high'
        
        return {
            'value': float(percentile),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'student_avg': float(student_avg),
            'cohort_avg': float(np.mean(cohort_scores)),
            'cohort_size': len(cohort_avgs),
            'privacy_level': 'FACULTY_ONLY'
        }
    
    def engagement_deviation(self, db: Session, student_id: str, cohort_id: str) -> Optional[Dict]:
        """
        Feature 7.2: Engagement Deviation from Cohort Mean
        
        Z-score of engagement relative to cohort
        
        SAFEGUARD: Faculty-only
        """
        from backend.database import FactEngagement
        from sqlalchemy import func
        
        # Student's average weekly engagement
        student_avg = db.query(
            func.avg(FactEngagement.total_time_minutes)
        ).filter(
            FactEngagement.student_id == student_id
        ).scalar()
        
        if not student_avg:
            return {
                'value': None,
                'interpretation': 'No engagement data',
                'risk_level': 'unknown',
                'privacy_level': 'FACULTY_ONLY'
            }
        
        # Cohort engagement distribution
        cohort_engagement = db.query(
            FactEngagement.student_id,
            func.avg(FactEngagement.total_time_minutes).label('avg_time')
        ).group_by(
            FactEngagement.student_id
        ).all()
        
        if len(cohort_engagement) < 10:
            return {
                'value': None,
                'interpretation': 'Insufficient cohort data',
                'risk_level': 'unknown',
                'privacy_level': 'FACULTY_ONLY'
            }
        
        cohort_times = [time for _, time in cohort_engagement if time]
        cohort_mean = np.mean(cohort_times)
        cohort_std = np.std(cohort_times)
        
        if cohort_std == 0:
            z_score = 0
        else:
            z_score = (student_avg - cohort_mean) / cohort_std
        
        # Interpretation
        if z_score > 1:
            interpretation = f"Above average (+{z_score:.1f} SD)"
            risk_level = 'low'
        elif z_score > -1:
            interpretation = f"Normal range ({z_score:+.1f} SD)"
            risk_level = 'medium'
        else:
            interpretation = f"Below average ({z_score:.1f} SD)"
            risk_level = 'high'
        
        return {
            'value': float(z_score),
            'interpretation': interpretation,
            'risk_level': risk_level,
            'student_minutes': float(student_avg),
            'cohort_mean_minutes': float(cohort_mean),
            'privacy_level': 'FACULTY_ONLY'
        }
    
    def churn_similarity(self, db: Session, student_id: str) -> Optional[Dict]:
        """
        Feature 7.3: Similarity to Past Churned Students
        
        Pattern matching to historical dropout profiles
        
        Note: Requires historical churn data and feature vectors
        """
        return {
            'value': None,
            'interpretation': 'Requires historical churn pattern database',
            'risk_level': 'unknown',
            'note': 'Needs labeled historical dropout data for pattern matching',
            'privacy_level': 'FACULTY_ONLY'
        }
    
    def difficulty_adjusted_score(self, db: Session, student_id: str, cohort_id: str) -> Optional[Dict]:
        """
        Feature 7.4: Course Difficulty Normalization
        
        Student's score adjusted for course difficulty (cohort performance)
        
        SAFEGUARD: Used alongside raw scores, not replacement
        """
        from backend.database import FactAcademicPerformance
        from sqlalchemy import func
        
        # Student's score
        student_score = db.query(
            func.avg(FactAcademicPerformance.percentage)
        ).filter(
            FactAcademicPerformance.student_id == student_id
        ).scalar()
        
        if not student_score:
            return {
                'value': None,
                'interpretation': 'No performance data',
                'risk_level': 'unknown',
                'privacy_level': 'FACULTY_ONLY'
            }
        
        # Course difficulty (inverse of cohort average)
        cohort_avg = db.query(
            func.avg(FactAcademicPerformance.percentage)
        ).filter(
            FactAcademicPerformance.trimester == cohort_id
        ).scalar()
        
        if not cohort_avg:
            return {
                'value': student_score,
                'interpretation': 'No cohort data for adjustment',
                'risk_level': 'unknown',
                'privacy_level': 'FACULTY_ONLY'
            }
        
        # Difficulty adjustment
        difficulty = 100 - cohort_avg
        
        if difficulty > 50:  # Hard course
            adjustment = difficulty * 0.1
        else:  # Easy course
            adjustment = -difficulty * 0.1
        
        adjusted_score = min(100, max(0, student_score + adjustment))
        
        return {
            'value': float(adjusted_score),
            'interpretation': f"Adjusted: {adjusted_score:.1f}% (Raw: {student_score:.1f}%)",
            'risk_level': 'medium',
            'raw_score': float(student_score),
            'cohort_avg': float(cohort_avg),
            'difficulty_level': 'high' if difficulty > 50 else 'low',
            'privacy_level': 'FACULTY_ONLY'
        }
