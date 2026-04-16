"""
Compatibility facade for student workflows.

New code should use `backend.application.student.student_application_service`
and `backend.infrastructure.student_repository` directly.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend.application.student import StudentApplicationService
from backend.infrastructure.student_repository import StudentRepository


class StudentService:
    """Legacy facade kept for backward compatibility across routes/controllers."""

    @staticmethod
    def get_interventions_by_student_id(db: Session, student_id: str):
        return StudentRepository.get_interventions_by_student_id(db, student_id)

    @staticmethod
    def _get_enrollment_dicts(db: Session, student_id: str) -> List[Dict]:
        return StudentRepository.fetch_enrollments_map(db, [student_id]).get(
            student_id, []
        )

    @staticmethod
    def _get_graded_components(db: Session, student_id: str) -> List[Dict]:
        return StudentRepository.fetch_graded_map(db, [student_id]).get(student_id, [])

    @staticmethod
    def _get_exam_records(db: Session, student_id: str) -> List[Dict]:
        return StudentRepository.fetch_exam_map(db, [student_id]).get(student_id, [])

    @staticmethod
    def _fetch_enrollments_map(
        db: Session, student_ids: List[str]
    ) -> Dict[str, List[Dict]]:
        return StudentRepository.fetch_enrollments_map(db, student_ids)

    @staticmethod
    def _fetch_graded_map(db: Session, student_ids: List[str]) -> Dict[str, List[Dict]]:
        return StudentRepository.fetch_graded_map(db, student_ids)

    @staticmethod
    def _fetch_exam_map(db: Session, student_ids: List[str]) -> Dict[str, List[Dict]]:
        return StudentRepository.fetch_exam_map(db, student_ids)

    @staticmethod
    def calculate_student_metrics(
        student, enrollment_dicts: List[Dict], graded_dicts=None, exam_dicts=None
    ) -> Dict:
        return StudentApplicationService.calculate_student_metrics(
            student, enrollment_dicts, graded_dicts, exam_dicts
        )

    @staticmethod
    def get_student_by_id(
        db: Session, student_id: str, current_user=None
    ) -> Optional[Dict]:
        return StudentApplicationService.get_student_by_id(
            db, student_id, current_user=current_user
        )

    @staticmethod
    def get_all_students(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "risk_score",
        order: str = "desc",
        risk_min: Optional[float] = None,
        risk_max: Optional[float] = None,
        current_user=None,
    ) -> List[Dict]:
        return StudentApplicationService.get_all_students(
            db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            order=order,
            risk_min=risk_min,
            risk_max=risk_max,
            current_user=current_user,
        )

    @staticmethod
    def get_student_count_filtered(
        db: Session,
        risk_min: Optional[float] = None,
        risk_max: Optional[float] = None,
        current_user=None,
    ) -> int:
        return StudentApplicationService.get_student_count_filtered(
            db, risk_min=risk_min, risk_max=risk_max, current_user=current_user
        )

    @staticmethod
    def get_latest_risk_scores_for_students(
        db: Session, student_ids: List[str]
    ) -> Dict[str, float]:
        return StudentRepository.get_latest_risk_scores_for_students(db, student_ids)

    @staticmethod
    def get_overview_stats(db: Session) -> Dict:
        return StudentApplicationService.get_overview_stats(db)

    @staticmethod
    def get_courses(db: Session) -> List[Dict]:
        return StudentApplicationService.get_courses(db)

    @staticmethod
    def get_course_engagement(db: Session, course_id: str) -> Optional[Dict]:
        return StudentApplicationService.get_course_engagement(db, course_id)

    @staticmethod
    def get_risk_distribution(db: Session) -> Dict:
        return StudentApplicationService.get_risk_distribution(db)

    @staticmethod
    def get_analytics_data(db: Session) -> Dict:
        return StudentApplicationService.get_analytics_data(db)

    @staticmethod
    def build_prediction_payload(student_metrics: Dict) -> Dict:
        return StudentApplicationService.build_prediction_payload(student_metrics)

    @staticmethod
    def build_intervention_recommendation(risk_score: float) -> Dict:
        return StudentApplicationService.build_intervention_recommendation(risk_score)

    @staticmethod
    def get_student_count(db: Session) -> int:
        return StudentRepository.student_count(db)
