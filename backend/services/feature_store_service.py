from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List

from backend.database import EngineeredFeatures, Enrollment, Student, GradedComponent
from backend.services.analytics_service import AnalyticsService

class FeatureStoreService:
    @staticmethod
    def precompute_all_features(db: Session):
        """
        Iterates through all students and precomputes retention features.
        """
        students = db.query(Student).all()
        for student in students:
            FeatureStoreService.compute_student_features(db, student.id)
        
        db.commit()

    @staticmethod
    def compute_student_features(db: Session, student_id: str):
        """
        Computes features for a single student and saves to EngineeredFeatures.
        """
        enrollments = db.query(Enrollment).filter(Enrollment.student_id == student_id).all()
        graded = db.query(GradedComponent).filter(GradedComponent.student_id == student_id).all()
        
        # Calculate derived metrics
        attendance_rate = 0.0
        if enrollments:
            # Simple average across enrollments
            attendance_rate = sum(e.num_logins for e in enrollments) / len(enrollments) # simplified
        
        grade_trend = 0.0
        if graded:
            # logic for grade trend...
            pass
            
        # Update or create features record
        features = db.query(EngineeredFeatures).filter(
            EngineeredFeatures.student_id == student_id,
            EngineeredFeatures.computation_date == datetime.utcnow().date()
        ).first()

        if not features:
            features = EngineeredFeatures(
                student_id=student_id,
                computation_date=datetime.utcnow().date()
            )
            db.add(features)

        features.attendance_rate = attendance_rate
        features.grade_trend = grade_trend
        features.login_frequency = sum(e.num_logins for e in enrollments)
        # Add more features...
        
        return features
