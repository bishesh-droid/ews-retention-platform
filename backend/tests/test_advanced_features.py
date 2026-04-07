"""
Advanced Features Test Suite
Test all 36 advanced retention features
"""
import pytest
pytest.skip(
    "Legacy `backend/features/*` package removed; active pipeline is `backend/services/feature_engineering.py`.",
    allow_module_level=True,
)

from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, DimStudent, FactAcademicPerformance, FactEngagement, FactIntentResponsiveness


@pytest.fixture
def test_db():
    """Create in-memory test database"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_student(test_db):
    """Create sample student with test data"""
    student_id = 'test@example.com'
    
    # Create student
    student = DimStudent(
        student_id=student_id,
        student_name='Test Student',
        program='MSc',
        cohort='T2_2026',
        trimester=2
    )
    test_db.add(student)
    
    # Add academic performance data (declining trend)
    base_date = date.today() - timedelta(days=60)
    scores = [85, 82, 78, 75, 70]  # Declining
    
    for i, score in enumerate(scores):
        assessment = FactAcademicPerformance(
            student_id=student_id,
            trimester='T2_2026',
            assessment_type='Quiz',
            assessment_name=f'Quiz {i+1}',
            assessment_date=base_date + timedelta(days=i*10),
            max_score=100,
            scored=score,
            percentage=score,
            submitted=True,
            late_submission=(i >= 3)  # Last 2 were late
        )
        test_db.add(assessment)
    
    # Add engagement data (declining)
    for week in range(1, 5):
        # Declining weekly engagement
        time_minutes = 300 - (week * 50)  # 300, 250, 200, 150
        engagement = FactEngagement(
            student_id=student_id,
            metric_week=week,
            metric_date=base_date + timedelta(weeks=week-1),
            total_time_minutes=time_minutes,
            login_count=10 - week,  # Declining logins
            live_sessions_attended=2 - (week // 2),
            discussion_posts=1,
            discussion_reads=50
        )
        test_db.add(engagement)
    
    # Add responsiveness data
    for i in range(3):
        resp = FactIntentResponsiveness(
            student_id=student_id,
            message_sent_date=datetime.now() - timedelta(days=20-i*7),
            response_received=True,
            response_time_hours=12 + (i * 8),  # Increasing latency
            message_type='email'
        )
        test_db.add(resp)
    
    test_db.commit()
    return student_id


class TestTemporalFeatures:
    """Test temporal and trend-based features"""
    
    def test_grade_trend_slope(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.temporal.compute_all(test_db, sample_student)
        
        grade_trend = features['academic_grade_trend_slope']
        assert grade_trend is not None
        assert grade_trend['value'] is not None
        # Should detect declining trend
        assert grade_trend['value'] < 0
        assert grade_trend['risk_level'] in ['medium', 'high']
    
    def test_score_volatility(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.temporal.compute_all(test_db, sample_student)
        
        volatility = features['academic_score_volatility']
        assert volatility is not None
        assert volatility['value'] is not None
        assert volatility['value'] > 0
    
    def test_engagement_decay_rate(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.temporal.compute_all(test_db, sample_student)
        
        decay = features['engagement_decay_rate']
        assert decay is not None
        # Should detect declining engagement
        if decay['value'] is not None:
            assert decay['trend_direction'] in ['declining', 'stable']


class TestConsistencyFeatures:
    """Test consistency and habit formation features"""
    
    def test_login_regularity(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.consistency.compute_all(test_db, sample_student)
        
        regularity = features['consistency_login_regularity_score']
        assert regularity is not None
        # Should be computable with sample data
        if regularity['value'] is not None:
            assert 0 <= regularity['value'] <= 100
    
    def test_study_streak(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.consistency.compute_all(test_db, sample_student)
        
        streak = features['consistency_study_streak_days']
        assert streak is not None
        assert streak['value'] is not None
        assert streak['value'] >= 0


class TestEffortOutcomeFeatures:
    """Test effort vs outcome mismatch features"""
    
    def test_practice_exam_gap(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        
        # Add exam data
        exam = FactAcademicPerformance(
            student_id=sample_student,
            trimester='T2_2026',
            assessment_type='Exam',
            assessment_name='Midterm',
            assessment_date=date.today() - timedelta(days=10),
            max_score=100,
            scored=65,
            percentage=65,
            submitted=True
        )
        test_db.add(exam)
        test_db.commit()
        
        features = orchestrator.effort.compute_all(test_db, sample_student)
        
        gap = features['effort_practice_exam_gap']
        assert gap is not None
        # Quiz avg is ~78, exam is 65, so gap should be positive
        if gap['value'] is not None:
            assert gap['value'] > 0
    
    def test_procrastination_index(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.effort.compute_all(test_db, sample_student)
        
        procrastination = features['effort_procrastination_index']
        assert procrastination is not None
        # Should show some procrastination (2/5 late in sample data)


class TestEngagementDepthFeatures:
    """Test engagement depth and quality features"""
    
    def test_forum_interaction_depth(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.engagement_depth.compute_all(test_db, sample_student)
        
        forum = features['engagement_forum_interaction_depth']
        assert forum is not None
        if forum['value'] is not None:
            # Has 1 post and 50 reads per week = low ratio
            assert forum['value'] < 0.1
            assert forum['risk_level'] in ['medium', 'high']


class TestResponsivenessFeatures:
    """Test responsiveness dynamics features"""
    
    def test_response_latency_trend(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.intent_resp.compute_all(test_db, sample_student)
        
        latency = features['responsiveness_latency_trend']
        assert latency is not None
        # Should detect increasing latency
        if latency['value'] is not None:
            assert latency['value'] > 0  # Positive slope = increasing delays
    
    def test_ignored_escalations(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        
        # Add record with no email opens (proxy for ignored)
        ignored = FactIntentResponsiveness(
            student_id=sample_student,
            welcome_email_opened=False,
            support_emails_read=0
        )
        test_db.add(ignored)
        test_db.commit()
        
        features = orchestrator.intent_resp.compute_all(test_db, sample_student)
        
        escalations = features['responsiveness_ignored_escalation_count']
        assert escalations is not None


class TestCompositeIndices:
    """Test composite explainable indices"""
    
    def test_disengagement_velocity_index(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.compute_all_features(test_db, sample_student)
        
        dvi = features['composite_indices']['disengagement_velocity_index']
        assert dvi is not None
        # Should show some disengagement
        if dvi['value'] is not None:
            assert 0 <= dvi['value'] <= 100
            assert 'components' in dvi
            assert 'interpretation' in dvi
    
    def test_academic_instability_index(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.compute_all_features(test_db, sample_student)
        
        aii = features['composite_indices']['academic_instability_index']
        assert aii is not None
        # Should detect some instability from declining grades
        if aii['value'] is not None:
            assert 0 <= aii['value'] <= 100
    
    def test_retention_risk_index(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        features = orchestrator.compute_all_features(test_db, sample_student)
        
        rri = features['composite_indices']['retention_risk_index']
        assert rri is not None
        
        if rri['value'] is not None:
            assert 0 <= rri['value'] <= 100
            assert rri['risk_level'] in ['low', 'medium', 'high', 'critical']
            assert 'recommended_actions' in rri
            assert 'dropout_probability' in rri


class TestOrchestrator:
    """Test master orchestrator"""
    
    def test_compute_all_features(self, test_db, sample_student):
        features = compute_advanced_features(test_db, sample_student, 'T2_2026')
        
        assert 'student_id' in features
        assert features['student_id'] == sample_student
        
        assert 'temporal_features' in features
        assert 'consistency_features' in features
        assert 'effort_outcome_features' in features
        assert 'engagement_depth_features' in features
        assert 'intent_responsiveness_features' in features
        assert 'composite_indices' in features
        
        assert 'summary' in features
        assert features['summary']['total_features_computed'] > 0
    
    def test_compute_risk_summary(self, test_db, sample_student):
        orchestrator = AdvancedFeatureOrchestrator()
        summary = orchestrator.compute_risk_summary(test_db, sample_student, 'T2_2026')
        
        assert 'retention_risk_index' in summary
        assert 'disengagement_velocity_index' in summary
        assert 'key_risk_factors' in summary
        assert isinstance(summary['key_risk_factors'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
