"""
FeatureEngineer Composer
-------------------------
Composes all 4 domain extractors and maintains the public interface.

This class is backward-compatible with the original FeatureEngineer API:
- get_features(student_id, db) returns the same feature dict structure
- No route handlers need to be updated
"""

from typing import Dict, List, Optional, Callable, Any
from sqlalchemy.orm import Session

from .academic import AcademicFeatureExtractor, AcademicFeatures
from .engagement import EngagementFeatureExtractor, EngagementFeatures
from .consistency import ConsistencyFeatureExtractor, ConsistencyFeatures
from .intent import IntentFeatureExtractor, IntentFeatures


class FeatureEngineer:
    """
    Composer class that orchestrates all 4 domain feature extractors.

    Maintains backward compatibility with the original God class API.
    The public interface (get_features) remains unchanged.
    """

    # Class constants for new student tolerance (weeks 1-3)
    NEW_STUDENT_TOLERANCE_MULTIPLIER = 1.20

    def __init__(self, registry_lookup: Optional[Callable] = None):
        """
        Initialize all 4 domain extractors.

        Args:
            registry_lookup: Optional callable for course content registry lookups
        """
        self.academic_extractor = AcademicFeatureExtractor()
        self.engagement_extractor = EngagementFeatureExtractor(registry_lookup=registry_lookup)
        self.consistency_extractor = ConsistencyFeatureExtractor()
        self.intent_extractor = IntentFeatureExtractor()

    def get_features(
        self,
        student_id: str,
        db: Session,
        is_new_student: bool = False,
        week_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate all features for a student (PUBLIC INTERFACE - UNCHANGED).

        This method maintains backward compatibility with the original API.
        Route handlers do not need to be updated.

        Args:
            student_id: The student's unique identifier
            db: Database session for fetching enrollment/grade data
            is_new_student: If True, apply early-term tolerance (weeks 1-3)
            week_number: Current trimester week (1-based)

        Returns:
            Dictionary with all calculated features (same structure as original)
        """
        # Fetch raw data from database
        enrollments = self._fetch_enrollments(student_id, db)
        graded_components = self._fetch_graded_components(student_id, db)
        exam_records = self._fetch_exam_records(student_id, db)

        # Calculate total login count for consistency features
        total_logins = sum(e.get("num_logins", 0) or 0 for e in enrollments)
        total_time = sum(e.get("total_time_spent", 0) or 0 for e in enrollments)

        # Extract features by domain
        academic = self.academic_extractor.extract(graded_components, exam_records)
        engagement = self.engagement_extractor.extract(enrollments, week_number)
        consistency = self.consistency_extractor.extract(enrollments, total_logins)

        # Intent requires combined signals from other domains
        intent = self.intent_extractor.extract(
            content_completion_score=engagement.content_completion_score,
            login_consistency_score=engagement.login_consistency_score,
            time_investment_score=engagement.time_investment_score,
            graded_quiz_score=academic.graded_quiz_score,
            risk_score=0.0,  # Will be calculated separately by risk model
            total_login_count=total_logins,
            total_time_seconds=total_time
        )

        # Assemble final feature dictionary (maintains original structure)
        features = self._assemble_features(
            academic, engagement, consistency, intent
        )

        # Apply new student tolerance if applicable
        if is_new_student and week_number is not None and week_number <= 3:
            features = self._apply_new_student_tolerance(features)

        return features

    def _assemble_features(
        self,
        academic: AcademicFeatures,
        engagement: EngagementFeatures,
        consistency: ConsistencyFeatures,
        intent: IntentFeatures
    ) -> Dict[str, Any]:
        """Assemble domain features into the original feature dict structure."""
        return {
            # Academic features
            "graded_quiz_score": academic.graded_quiz_score,
            "graded_assignment_score": academic.graded_assignment_score,
            "exam_score": academic.exam_score,
            "exam_attendance_rate": academic.exam_attendance_rate,
            "academic_flags": academic.academic_flags,

            # Engagement features
            "content_completion_score": engagement.content_completion_score,
            "w1w2_completion_score": engagement.w1w2_completion_score,
            "quiz_engagement_score": engagement.quiz_engagement_score,
            "discussion_engagement_score": engagement.discussion_engagement_score,
            "login_consistency_score": engagement.login_consistency_score,
            "time_investment_score": engagement.time_investment_score,
            "assignment_score": engagement.assignment_score,
            "zero_progress_ratio": engagement.zero_progress_ratio,
            "progress_category": engagement.progress_category,
            "per_course_breakdown": engagement.per_course_breakdown,
            "self_directed_learning_score": engagement.self_directed_learning_score,

            # Consistency features
            "engagement_trend": consistency.engagement_trend,
            "ghost_info": {
                "is_ghost": consistency.is_ghost,
                "ghost_type": consistency.ghost_type,
                "zero_progress_course_count": consistency.zero_progress_course_count,
                "total_enrolled_courses": consistency.total_enrolled_courses,
                "total_time_seconds": consistency.total_time_seconds,
            },

            # Intent features
            "engagement_pattern": intent.engagement_pattern,

            # Metadata
            "total_courses": consistency.total_enrolled_courses,
        }

    def _apply_new_student_tolerance(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply 20% boost to select scores for new students in weeks 1-3.

        New students may have lower initial engagement as they orient to the platform.
        """
        tolerance_fields = ["content_completion_score", "login_consistency_score"]

        for field in tolerance_fields:
            if features.get(field) is not None:
                features[field] = min(
                    100.0,
                    features[field] * self.NEW_STUDENT_TOLERANCE_MULTIPLIER
                )

        return features

    def _fetch_enrollments(self, student_id: str, db: Session) -> List[Dict]:
        """Fetch enrollment records for a student from the database."""
        # This is a stub - implement based on your actual data access pattern
        # Example: return EnrollmentService.get_student_enrollments(db, student_id)
        from backend.services.student_service import StudentService
        return StudentService.get_enrollments_for_student(db, student_id)

    def _fetch_graded_components(self, student_id: str, db: Session) -> List[Dict]:
        """Fetch graded quiz/assignment records for a student."""
        from backend.services.student_service import StudentService
        return StudentService.get_graded_components_for_student(db, student_id)

    def _fetch_exam_records(self, student_id: str, db: Session) -> List[Dict]:
        """Fetch exam records for a student."""
        from backend.services.student_service import StudentService
        return StudentService.get_exam_records_for_student(db, student_id)

    # =========================================================================
    # Static methods for backward compatibility
    # These delegate to the appropriate extractor
    # =========================================================================

    @staticmethod
    def calculate_content_completion_score(
        enrollments: List[Dict],
        registry_lookup=None
    ) -> Optional[float]:
        """Backward-compatible static method."""
        extractor = EngagementFeatureExtractor(registry_lookup=registry_lookup)
        return extractor._calculate_content_completion_score(enrollments)

    @staticmethod
    def calculate_all_features(
        enrollments: List[Dict],
        graded_components: List[Dict] = None,
        exam_records: List[Dict] = None,
        is_new_student: bool = False,
        week_number: Optional[int] = None,
        registry_lookup=None,
    ) -> Dict:
        """
        Backward-compatible static method for direct feature calculation.

        This allows existing code that calls FeatureEngineer.calculate_all_features()
        to continue working without changes.
        """
        academic_extractor = AcademicFeatureExtractor()
        engagement_extractor = EngagementFeatureExtractor(registry_lookup=registry_lookup)
        consistency_extractor = ConsistencyFeatureExtractor()
        intent_extractor = IntentFeatureExtractor()

        graded_components = graded_components or []
        exam_records = exam_records or []
        total_logins = sum(e.get("num_logins", 0) or 0 for e in enrollments)
        total_time = sum(e.get("total_time_spent", 0) or 0 for e in enrollments)

        academic = academic_extractor.extract(graded_components, exam_records)
        engagement = engagement_extractor.extract(enrollments, week_number)
        consistency = consistency_extractor.extract(enrollments, total_logins)
        intent = intent_extractor.extract(
            content_completion_score=engagement.content_completion_score,
            login_consistency_score=engagement.login_consistency_score,
            time_investment_score=engagement.time_investment_score,
            graded_quiz_score=academic.graded_quiz_score,
            risk_score=0.0,
            total_login_count=total_logins,
            total_time_seconds=total_time
        )

        engineer = FeatureEngineer(registry_lookup=registry_lookup)
        features = engineer._assemble_features(academic, engagement, consistency, intent)

        if is_new_student and week_number is not None and week_number <= 3:
            features = engineer._apply_new_student_tolerance(features)

        return features
