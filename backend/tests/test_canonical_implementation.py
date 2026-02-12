"""
Test script for risk scoring logic
Validates that risk scores are always within 0-100 bounds
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, DimStudent
from backend.features.risk_scorer import RiskScorer


def test_risk_score_bounds():
    """Test that risk scores are always within 0-100"""
    print("="*80)
    print("RISK SCORE BOUNDS TEST")
    print("="*80)
    
    db = SessionLocal()
    scorer = RiskScorer()
    
    try:
        # Get all students
        students = db.query(DimStudent).limit(10).all()
        
        if not students:
            print("⚠ No students in database. Run ETL pipeline first.")
            return False
        
        print(f"\\nTesting risk scores for {len(students)} students...")
        
        issues = []
        
        for student in students:
            result = scorer.compute_risk_score(db, student.student_id, 'T1-2025')
            
            risk_score = result.get('risk_score')
            
            if risk_score is not None:
                # Check bounds
                if risk_score < 0:
                    issues.append(f"{student.student_id}: risk_score < 0 ({risk_score})")
                
                if risk_score > 100:
                    issues.append(f"{student.student_id}: risk_score > 100 ({risk_score})")
                
                if risk_score == -1:
                    issues.append(f"{student.student_id}: risk_score = -1 (FORBIDDEN)")
                
                print(f"  ✓ {student.student_id}: risk_score = {risk_score} ({result['risk_level']})")
            else:
                print(f"  ⚠ {student.student_id}: risk_score = NULL (insufficient data)")
        
        print(f"\\n{'='*80}")
        
        if issues:
            print(f"❌ FAILED: Found {len(issues)} bound violations")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("✅ PASSED: All risk scores within 0-100 bounds")
            return True
            
    finally:
        db.close()


def test_signal_computation():
    """Test individual signal computations"""
    print("\\n" + "="*80)
    print("SIGNAL COMPUTATION TEST")
    print("="*80)
    
    from backend.features.academic_signals import AcademicPerformanceSignal
    from backend.features.engagement_signals import EngagementSignal
    
    db = SessionLocal()
    
    try:
        student = db.query(DimStudent).first()
        
        if not student:
            print("⚠ No students in database")
            return False
        
        print(f"\\nTesting signals for: {student.student_id}")
        
        # Academic signal
        academic = AcademicPerformanceSignal().compute(db, student.student_id, 'T1-2025')
        print(f"\\n  Academic Performance Signal:")
        print(f"    Value: {academic.get('signal_value')}")
        print(f"    Sub-metrics: {academic.get('sub_metrics')}")
        
        # Engagement signal
        engagement = EngagementSignal().compute(db, student.student_id, 'T1-2025')
        print(f"\\n  Engagement Signal:")
        print(f"    Value: {engagement.get('signal_value')}")
        print(f"    Sub-metrics: {engagement.get('sub_metrics')}")
        
        print("\\n✅ Signal computation completed")
        return True
        
    finally:
        db.close()


if __name__ == "__main__":
    print("\\nEWS Risk Scoring Tests\\n")
    
    test1 = test_risk_score_bounds()
    test2 = test_signal_computation()
    
    if test1 and test2:
        print("\\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\\n❌ Some tests failed")
        sys.exit(1)
