"""
Infrastructure data access for student workflows.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import Float, and_, case, cast, func
from sqlalchemy.orm import Session

from backend.database import (
    Course,
    Enrollment,
    ExamRecord,
    GradedComponent,
    Intervention,
    Prediction,
    Student,
)


class StudentRepository:
    @staticmethod
    def latest_prediction_subquery(db: Session):
        return (
            db.query(
                Prediction.student_id.label("student_id"),
                func.max(Prediction.prediction_timestamp).label("max_ts"),
            )
            .group_by(Prediction.student_id)
            .subquery()
        )

    @staticmethod
    def latest_prediction_rows_subquery(db: Session):
        latest = StudentRepository.latest_prediction_subquery(db)
        return (
            db.query(Prediction)
            .join(
                latest,
                and_(
                    Prediction.student_id == latest.c.student_id,
                    Prediction.prediction_timestamp == latest.c.max_ts,
                ),
            )
            .subquery()
        )

    @staticmethod
    def sort_expr_for_students(sort_by: str, order: str, pred_subq):
        direction = {"asc": lambda x: x.asc(), "desc": lambda x: x.desc()}.get(
            order, lambda x: x.desc()
        )
        student_cols = {
            "id": Student.id,
            "first_name": Student.first_name,
            "last_name": Student.last_name,
            "org_defined_id": Student.org_defined_id,
            "department": Student.parent_department_name,
            "old_new_student": Student.old_new_student,
            "is_active": Student.is_active,
        }
        if sort_by in student_cols:
            return direction(student_cols[sort_by])
        risk = cast(pred_subq.c.risk_score, Float)
        return (case((risk.is_(None), 1), else_=0), direction(risk))

    @staticmethod
    def get_interventions_by_student_id(
        db: Session, student_id: str
    ) -> List[Intervention]:
        return (
            db.query(Intervention).filter(Intervention.student_id == student_id).all()
        )

    @staticmethod
    def get_student_by_id_scoped(
        db: Session, student_id: str, current_user=None
    ) -> Optional[Student]:
        query = db.query(Student).filter(Student.id == student_id)
        if current_user is not None:
            role = (getattr(current_user, "role", "") or "").lower()
            is_superuser = bool(getattr(current_user, "is_superuser", False))
            if role == "faculty" and not is_superuser:
                dept = getattr(current_user, "department", None)
                if dept:
                    query = query.filter(Student.parent_department_name == dept)
        return query.first()

    @staticmethod
    def fetch_enrollments_map(
        db: Session, student_ids: List[str]
    ) -> Dict[str, List[Dict]]:
        if not student_ids:
            return {}
        rows = (
            db.query(Enrollment, Course.name)
            .join(Course, Enrollment.course_id == Course.id, isouter=True)
            .filter(Enrollment.student_id.in_(student_ids))
            .all()
        )
        out: Dict[str, List[Dict]] = {sid: [] for sid in student_ids}
        for enrollment, course_name in rows:
            out.setdefault(enrollment.student_id, []).append(
                {
                    "course_id": enrollment.course_id,
                    "course_name": course_name or "",
                    "content_completed": enrollment.content_completed,
                    "content_required": enrollment.content_required,
                    "content_required_w1w2": enrollment.content_required_w1w2,
                    "checklist_completed": enrollment.checklist_completed,
                    "quiz_completed": enrollment.quiz_completed,
                    "total_quiz_attempts": enrollment.total_quiz_attempts,
                    "last_quiz_attempt_date": enrollment.last_quiz_attempt_date,
                    "discussion_posts_created": enrollment.discussion_posts_created,
                    "discussion_post_replies": enrollment.discussion_post_replies,
                    "discussion_posts_read": enrollment.discussion_posts_read,
                    "last_discussion_post_date": enrollment.last_discussion_post_date,
                    "num_assignment_submissions": enrollment.num_assignment_submissions,
                    "last_assignment_submission_date": enrollment.last_assignment_submission_date,
                    "total_time_spent_seconds": enrollment.total_time_spent_seconds,
                    "last_visited_date": enrollment.last_visited_date,
                    "last_system_login": enrollment.last_system_login,
                    "num_logins": enrollment.num_logins,
                    "last_scorm_completion_date": enrollment.last_scorm_completion_date,
                    "last_scorm_visit_date": enrollment.last_scorm_visit_date,
                }
            )
        return out

    @staticmethod
    def fetch_graded_map(db: Session, student_ids: List[str]) -> Dict[str, List[Dict]]:
        if not student_ids:
            return {}
        rows = (
            db.query(GradedComponent)
            .filter(GradedComponent.student_id.in_(student_ids))
            .all()
        )
        out: Dict[str, List[Dict]] = {sid: [] for sid in student_ids}
        for g in rows:
            sid = g.student_id or ""
            out.setdefault(sid, []).append(
                {
                    "component_type": g.component_type,
                    "component_number": g.component_number,
                    "score": g.score,
                    "max_score": g.max_score,
                    "missed": g.missed,
                    "course_code": g.course_code,
                    "course_name": g.course_name,
                }
            )
        return out

    @staticmethod
    def fetch_exam_map(db: Session, student_ids: List[str]) -> Dict[str, List[Dict]]:
        if not student_ids:
            return {}
        rows = (
            db.query(ExamRecord)
            .filter(
                ExamRecord.student_id.in_(student_ids),
                ExamRecord.course_code != "EXAM_DEFAULT",
            )
            .all()
        )
        out: Dict[str, List[Dict]] = {sid: [] for sid in student_ids}
        for e in rows:
            sid = e.student_id or ""
            out.setdefault(sid, []).append(
                {
                    "course_code": e.course_code,
                    "course_name": e.course_name,
                    "slot": e.slot,
                    "marks_obtained": e.marks_obtained,
                    "marks_total": e.marks_total,
                    "present": e.present,
                    "mode": e.mode,
                }
            )
        return out

    @staticmethod
    def get_courses(db: Session) -> List[Dict]:
        courses = db.query(Course).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "semester": c.semester_name,
                "content_required_w1w2": c.content_required_w1w2,
                "content_required_total": c.content_required_total,
                "week1_content": c.week1_content,
                "week2_content": c.week2_content,
            }
            for c in courses
        ]

    @staticmethod
    def get_course(course_id: str, db: Session):
        return db.query(Course).filter(Course.id == course_id).first()

    @staticmethod
    def get_latest_risk_scores_for_students(
        db: Session, student_ids: List[str]
    ) -> Dict[str, float]:
        if not student_ids:
            return {}
        latest = (
            db.query(
                Prediction.student_id.label("student_id"),
                func.max(Prediction.prediction_timestamp).label("max_ts"),
            )
            .filter(Prediction.student_id.in_(student_ids))
            .group_by(Prediction.student_id)
            .subquery()
        )
        rows = (
            db.query(Prediction.student_id, Prediction.risk_score)
            .join(
                latest,
                and_(
                    Prediction.student_id == latest.c.student_id,
                    Prediction.prediction_timestamp == latest.c.max_ts,
                ),
            )
            .all()
        )
        out: Dict[str, float] = {}
        for sid, raw in rows:
            if raw is None:
                continue
            try:
                v = float(raw)
            except Exception:
                continue
            if 0.0 <= v <= 1.0:
                v *= 100.0
            out[sid] = max(0.0, min(100.0, round(v, 2)))
        return out

    @staticmethod
    def student_count(db: Session) -> int:
        return int(db.query(func.count(Student.id)).scalar() or 0)
