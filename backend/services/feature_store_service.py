from sqlalchemy.orm import Session
from datetime import datetime

from backend.database import EngineeredFeatures, Enrollment, Student, GradedComponent


class FeatureStoreService:
    @staticmethod
    def precompute_all_features(db: Session):
        """
        Iterates through all students and precomputes retention features.
        """
        students = db.query(Student).all()
        for student in students:
            FeatureStoreService.compute_student_features(db, str(student.id))
        # Persist pending changes to the DB transaction; caller commits.
        db.flush()

    @staticmethod
    def compute_student_features(db: Session, student_id: str):
        """
        Computes features for a single student and saves to EngineeredFeatures.
        """
        enrollments = (
            db.query(Enrollment).filter(Enrollment.student_id == student_id).all()
        )
        graded = (
            db.query(GradedComponent)
            .filter(GradedComponent.student_id == student_id)
            .all()
        )

        # Calculate derived metrics
        attendance_rate = 0.0
        if enrollments:
            # Simple average across enrollments
            attendance_rate = sum(int(e.num_logins or 0) for e in enrollments) / len(
                enrollments
            )  # type: ignore[arg-type]

        grade_trend = 0.0
        if graded:
            # logic for grade trend...
            pass

        # Update or create features record
        features = (
            db.query(EngineeredFeatures)
            .filter(
                EngineeredFeatures.student_id == student_id,
                EngineeredFeatures.computation_date == datetime.utcnow().date(),
            )
            .first()
        )

        if not features:
            features = EngineeredFeatures(
                student_id=student_id, computation_date=datetime.utcnow().date()
            )
            db.add(features)

        features.attendance_rate = attendance_rate  # type: ignore[assignment]
        features.grade_trend = grade_trend  # type: ignore[assignment]
        features.login_frequency = sum(
            int(e.num_logins or 0) for e in enrollments
        )  # type: ignore[assignment, arg-type]
        # Add more features...

        return features
