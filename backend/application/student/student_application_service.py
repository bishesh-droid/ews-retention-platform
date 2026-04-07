"""
Student application service orchestration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import Float, Integer, case, cast, func
from sqlalchemy.orm import Session

from backend.config import RISK_THRESHOLD_HIGH, RISK_THRESHOLD_MEDIUM
from backend.database import Course, Enrollment, Student
from backend.domain.student import build_intervention_recommendation
from backend.infrastructure.student_repository import StudentRepository
from backend.services.feature_engineering import FeatureEngineer
from backend.services.risk_scoring import RiskScorer


class StudentApplicationService:
    @staticmethod
    def _prediction_risk_to_0_100(pred_row: Any) -> Optional[float]:
        if pred_row is None:
            return None
        return RiskScorer.normalize_risk_to_0_100(getattr(pred_row, "risk_score", None))

    @staticmethod
    def _calculate_features(
        enrollment_dicts: List[Dict],
        graded_dicts: Optional[List[Dict]] = None,
        exam_dicts: Optional[List[Dict]] = None,
    ) -> Dict:
        return FeatureEngineer.calculate_all_features(
            enrollment_dicts,
            graded_components=graded_dicts,
            exam_records=exam_dicts,
        )

    @staticmethod
    def _derive_risk_fields(features: Dict, pred_row: Optional[Any] = None) -> Dict:
        pred_risk_0_100 = StudentApplicationService._prediction_risk_to_0_100(pred_row)
        if pred_risk_0_100 is None:
            risk_score = RiskScorer.calculate_risk_score(features)
            retention_likelihood = RiskScorer.get_retention_likelihood(risk_score)
        else:
            risk_score = pred_risk_0_100
            retention_likelihood = getattr(pred_row, "retention_likelihood", None) or RiskScorer.get_retention_likelihood(
                risk_score
            )
        return {
            "risk_score": risk_score,
            "risk_category": RiskScorer.get_risk_category(risk_score),
            "retention_likelihood": retention_likelihood,
            "dominant_risk_factor": RiskScorer.get_dominant_risk_factor(features),
            "risk_breakdown": RiskScorer.get_risk_breakdown(features),
        }

    @staticmethod
    def _build_student_metrics_response(student: Student, features: Dict, risk_fields: Dict) -> Dict:
        return {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "org_defined_id": student.org_defined_id,
            "department": student.parent_department_name,
            "old_new_student": student.old_new_student,
            "is_active": student.is_active,
            "risk_score": risk_fields["risk_score"],
            "risk_category": risk_fields["risk_category"],
            "retention_likelihood": risk_fields["retention_likelihood"],
            "dominant_risk_factor": risk_fields["dominant_risk_factor"],
            "risk_breakdown": risk_fields["risk_breakdown"],
            "content_completion_score": features["content_completion_score"],
            "w1w2_completion_score": features["w1w2_completion_score"],
            "quiz_engagement_score": features["quiz_engagement_score"],
            "discussion_engagement_score": features["discussion_engagement_score"],
            "login_consistency_score": features["login_consistency_score"],
            "time_investment_score": features["time_investment_score"],
            "assignment_score": features["assignment_score"],
            "graded_quiz_score": features["graded_quiz_score"],
            "graded_assignment_score": features["graded_assignment_score"],
            "exam_score": features["exam_score"],
            "exam_attendance_rate": features["exam_attendance_rate"],
            "zero_progress_ratio": features["zero_progress_ratio"],
            "progress_category": features["progress_category"],
            "trend": features["engagement_trend"],
            "total_courses": features["total_courses"],
            "per_course_breakdown": features["per_course_breakdown"],
            "attendance_score": features.get("exam_attendance_rate", 0),
            "academic_score": features["content_completion_score"],
            "behavioral_score": features["discussion_engagement_score"],
            "stability_score": features["time_investment_score"],
        }

    @staticmethod
    def calculate_student_metrics(
        student: Student,
        enrollment_dicts: List[Dict],
        graded_dicts: Optional[List[Dict]] = None,
        exam_dicts: Optional[List[Dict]] = None,
    ) -> Dict:
        features = StudentApplicationService._calculate_features(enrollment_dicts, graded_dicts, exam_dicts)
        risk_fields = StudentApplicationService._derive_risk_fields(features)
        return StudentApplicationService._build_student_metrics_response(student, features, risk_fields)

    @staticmethod
    def get_student_by_id(db: Session, student_id: str, current_user=None) -> Optional[Dict]:
        student = StudentRepository.get_student_by_id_scoped(db, student_id, current_user=current_user)
        if not student:
            return None
        enrollment_dicts = StudentRepository.fetch_enrollments_map(db, [student_id]).get(student_id, [])
        graded_dicts = StudentRepository.fetch_graded_map(db, [student_id]).get(student_id, [])
        exam_dicts = StudentRepository.fetch_exam_map(db, [student_id]).get(student_id, [])
        return StudentApplicationService.calculate_student_metrics(student, enrollment_dicts, graded_dicts, exam_dicts)

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
        pred_subq = StudentRepository.latest_prediction_rows_subquery(db)
        base = db.query(Student, pred_subq).outerjoin(pred_subq, pred_subq.c.student_id == Student.id)

        if current_user is not None:
            role = (getattr(current_user, "role", "") or "").lower()
            is_superuser = bool(getattr(current_user, "is_superuser", False))
            if role == "faculty" and not is_superuser:
                dept = getattr(current_user, "department", None)
                if dept:
                    base = base.filter(Student.parent_department_name == dept)

        risk_expr = cast(pred_subq.c.risk_score, Float)
        if risk_min is not None:
            rm = float(risk_min) / 100.0 if float(risk_min) > 1.0 else float(risk_min)
            base = base.filter(risk_expr.isnot(None)).filter(risk_expr >= rm)
        if risk_max is not None:
            rx = float(risk_max) / 100.0 if float(risk_max) > 1.0 else float(risk_max)
            base = base.filter(risk_expr.isnot(None)).filter(risk_expr <= rx)

        sort_expr = StudentRepository.sort_expr_for_students(sort_by, order, pred_subq)
        base = base.order_by(*sort_expr) if isinstance(sort_expr, tuple) else base.order_by(sort_expr)
        rows = base.offset(skip).limit(limit).all()

        students: List[Student] = [r[0] for r in rows]
        pred_rows = [r[1] for r in rows]
        student_ids = [s.id for s in students]

        enrollment_map = StudentRepository.fetch_enrollments_map(db, student_ids)
        graded_map = StudentRepository.fetch_graded_map(db, student_ids)
        exam_map = StudentRepository.fetch_exam_map(db, student_ids)

        result: List[Dict] = []
        for student, pred_row in zip(students, pred_rows):
            features = StudentApplicationService._calculate_features(
                enrollment_map.get(student.id, []),
                graded_map.get(student.id, []),
                exam_map.get(student.id, []),
            )
            risk_fields = StudentApplicationService._derive_risk_fields(features, pred_row=pred_row)
            result.append(StudentApplicationService._build_student_metrics_response(student, features, risk_fields))

        reverse = order == "desc"
        computed_fields = [
            "content_completion_score",
            "quiz_engagement_score",
            "login_consistency_score",
            "time_investment_score",
            "graded_quiz_score",
            "graded_assignment_score",
            "exam_score",
            "exam_attendance_rate",
            "attendance_score",
            "academic_score",
            "behavioral_score",
            "stability_score",
        ]
        if sort_by in computed_fields:
            result.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=reverse)
        return result

    @staticmethod
    def get_student_count_filtered(
        db: Session,
        risk_min: Optional[float] = None,
        risk_max: Optional[float] = None,
        current_user=None,
    ) -> int:
        pred_subq = StudentRepository.latest_prediction_rows_subquery(db)
        base = db.query(func.count(Student.id)).outerjoin(pred_subq, pred_subq.c.student_id == Student.id)

        if current_user is not None:
            role = (getattr(current_user, "role", "") or "").lower()
            is_superuser = bool(getattr(current_user, "is_superuser", False))
            if role == "faculty" and not is_superuser:
                dept = getattr(current_user, "department", None)
                if dept:
                    base = base.filter(Student.parent_department_name == dept)

        risk_expr = cast(pred_subq.c.risk_score, Float)
        if risk_min is not None:
            rm = float(risk_min) / 100.0 if float(risk_min) > 1.0 else float(risk_min)
            base = base.filter(risk_expr.isnot(None)).filter(risk_expr >= rm)
        if risk_max is not None:
            rx = float(risk_max) / 100.0 if float(risk_max) > 1.0 else float(risk_max)
            base = base.filter(risk_expr.isnot(None)).filter(risk_expr <= rx)
        return int(base.scalar() or 0)

    @staticmethod
    def get_overview_stats(db: Session) -> Dict:
        total_students = StudentRepository.student_count(db)
        total_courses = db.query(func.count(Course.id)).scalar() or 0
        total_enrollments = db.query(func.count(Enrollment.id)).scalar() or 0
        if total_students == 0:
            return {
                "total_students": 0,
                "at_risk_students": 0,
                "average_risk_score": 0,
                "risk_distribution": {"low": 0, "medium": 0, "high": 0},
                "total_enrollments": 0,
                "total_courses": 0,
            }

        pred = StudentRepository.latest_prediction_rows_subquery(db)
        risk = cast(pred.c.risk_score, Float)
        risk_0_100 = case((risk <= 1.0, risk * 100.0), else_=risk)
        avg_risk = db.query(func.avg(risk_0_100)).select_from(pred).filter(risk.isnot(None)).scalar()

        low_count = (
            db.query(func.count(pred.c.student_id))
            .select_from(pred)
            .filter(risk.isnot(None))
            .filter(risk_0_100 < RISK_THRESHOLD_MEDIUM)
            .scalar()
            or 0
        )
        medium_count = (
            db.query(func.count(pred.c.student_id))
            .select_from(pred)
            .filter(risk.isnot(None))
            .filter(risk_0_100 >= RISK_THRESHOLD_MEDIUM)
            .filter(risk_0_100 < RISK_THRESHOLD_HIGH)
            .scalar()
            or 0
        )
        high_count = (
            db.query(func.count(pred.c.student_id))
            .select_from(pred)
            .filter(risk.isnot(None))
            .filter(risk_0_100 >= RISK_THRESHOLD_HIGH)
            .scalar()
            or 0
        )
        return {
            "total_students": int(total_students),
            "at_risk_students": int(high_count),
            "average_risk_score": round(float(avg_risk or 0.0), 2),
            "risk_distribution": {"low": int(low_count), "medium": int(medium_count), "high": int(high_count)},
            "total_enrollments": int(total_enrollments),
            "total_courses": int(total_courses),
        }

    @staticmethod
    def get_courses(db: Session) -> List[Dict]:
        return StudentRepository.get_courses(db)

    @staticmethod
    def get_course_engagement(db: Session, course_id: str) -> Optional[Dict]:
        course = StudentRepository.get_course(course_id, db)
        if not course:
            return None
        e = Enrollment
        total_enrolled = db.query(func.count(e.id)).filter(e.course_id == course_id).scalar() or 0
        sum_completed = db.query(func.coalesce(func.sum(e.content_completed), 0)).filter(e.course_id == course_id).scalar() or 0
        sum_time = db.query(func.coalesce(func.sum(e.total_time_spent_seconds), 0)).filter(e.course_id == course_id).scalar() or 0
        zero_progress = (
            db.query(func.count(e.id))
            .filter(e.course_id == course_id)
            .filter(func.coalesce(e.content_completed, 0) == 0)
            .scalar()
            or 0
        )
        low_progress = (
            db.query(func.count(e.id))
            .filter(e.course_id == course_id)
            .filter(func.coalesce(e.content_completed, 0) > 0)
            .filter(func.coalesce(e.content_required, 1) > 0)
            .filter(func.coalesce(e.content_completed, 0) <= (func.coalesce(e.content_required, 1) * 0.1))
            .scalar()
            or 0
        )
        active = int(total_enrolled) - int(zero_progress) - int(low_progress)
        return {
            "course_id": course.id,
            "course_name": course.name,
            "total_enrolled": int(total_enrolled),
            "zero_progress": int(zero_progress),
            "low_progress_0_10": int(low_progress),
            "active_above_10": int(active),
            "avg_content_completed": round(float(sum_completed) / max(int(total_enrolled), 1), 2),
            "avg_time_spent_hours": round(float(sum_time) / max(int(total_enrolled), 1) / 3600.0, 2),
        }

    @staticmethod
    def get_risk_distribution(db: Session) -> Dict:
        pred = StudentRepository.latest_prediction_rows_subquery(db)
        risk = cast(pred.c.risk_score, Float)
        risk_0_100 = case((risk <= 1.0, risk * 100.0), else_=risk)
        n = db.query(func.count(pred.c.student_id)).select_from(pred).filter(risk.isnot(None)).scalar() or 0
        if n == 0:
            return {"histogram": [], "percentiles": {}}

        bucket_idx = cast(risk_0_100 / 10.0, Integer)
        bucket_start = bucket_idx * 10
        bucket_rows = (
            db.query(bucket_start.label("start"), func.count().label("count"))
            .select_from(pred)
            .filter(risk.isnot(None))
            .group_by(bucket_start)
            .order_by(bucket_start.asc())
            .all()
        )
        histogram = [{"range": f"{int(start)}-{int(start) + 10}", "count": int(count)} for start, count in bucket_rows]

        def kth_value(pct: int) -> float:
            k = int((n - 1) * pct / 100)
            row = (
                db.query(risk_0_100)
                .select_from(pred)
                .filter(risk.isnot(None))
                .order_by(risk_0_100.asc())
                .offset(k)
                .limit(1)
                .scalar()
            )
            return round(float(row or 0.0), 2)

        return {"histogram": histogram, "percentiles": {"p25": kth_value(25), "p50": kth_value(50), "p75": kth_value(75), "p90": kth_value(90)}}

    @staticmethod
    def get_analytics_data(db: Session) -> Dict:
        pred = StudentRepository.latest_prediction_rows_subquery(db)
        risk = cast(pred.c.risk_score, Float)
        risk_0_100 = case((risk <= 1.0, risk * 100.0), else_=risk)
        dept_rows = (
            db.query(
                func.coalesce(Student.parent_department_name, "Unknown").label("department"),
                func.count(Student.id).label("student_count"),
                func.avg(risk_0_100).label("avg_risk_score"),
            )
            .outerjoin(pred, pred.c.student_id == Student.id)
            .group_by(func.coalesce(Student.parent_department_name, "Unknown"))
            .order_by(func.count(Student.id).desc())
            .all()
        )
        department_summary = [
            {"department": dept, "student_count": int(count or 0), "avg_risk_score": round(float(avg or 0.0), 2)}
            for dept, count, avg in dept_rows
        ]
        course_stats = (
            db.query(Course.name, func.count(Enrollment.id), func.avg(Enrollment.content_completed), func.sum(Enrollment.total_time_spent_seconds))
            .join(Enrollment, Course.id == Enrollment.course_id, isouter=True)
            .group_by(Course.name)
            .all()
        )
        course_summary = [
            {
                "course": name,
                "enrollments": count or 0,
                "avg_content_completed": round(avg_completed or 0, 2),
                "total_time_hours": round((total_time or 0) / 3600, 2),
            }
            for name, count, avg_completed, total_time in course_stats
        ]
        return {"department_summary": department_summary, "course_summary": course_summary, "total_analyzed": StudentRepository.student_count(db)}

    @staticmethod
    def build_prediction_payload(student_metrics: Dict) -> Dict:
        risk = float(student_metrics["risk_score"])
        return {
            "student_id": student_metrics["id"],
            "risk_score": risk / 100.0,
            "engagement_score": (100 - risk) / 100.0,
            "retention_likelihood": student_metrics["retention_likelihood"],
            "model_version": "rule_based_v2",
            "signal_breakdown": {
                "academic_signal_score": student_metrics.get("content_completion_score", 0) / 100.0,
                "engagement_signal_score": student_metrics.get("quiz_engagement_score", 0) / 100.0,
                "consistency_signal_score": student_metrics.get("login_consistency_score", 0) / 100.0,
                "intent_signal_score": student_metrics.get("assignment_score", 0) / 100.0,
                "responsiveness_signal_score": student_metrics.get("discussion_engagement_score", 0) / 100.0,
            },
            "top_risk_factors": [student_metrics.get("dominant_risk_factor", "Unknown")],
            "prediction_error": False,
        }

    @staticmethod
    def build_intervention_recommendation(risk_score: float) -> Dict:
        return build_intervention_recommendation(risk_score)
