"""
Student Service for EWS Retention Platform.

Integrates feature engineering and risk scoring to provide
comprehensive student engagement data from real XLSX data.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case, cast, Integer, Float

from backend.services.feature_engineering import FeatureEngineer
from backend.services.risk_scoring import RiskScorer
from backend.database import Student, Course, Enrollment, GradedComponent, ExamRecord, Intervention, Prediction


class StudentService:
    """
    Service for retrieving and calculating student engagement metrics.
    """

    # ------------------------------------------------------------------ #
    # Internal helpers (data access + batching)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _latest_prediction_subquery(db: Session):
        """(student_id, max_ts) for latest prediction per student."""
        return (
            db.query(
                Prediction.student_id.label("student_id"),
                func.max(Prediction.prediction_timestamp).label("max_ts"),
            )
            .group_by(Prediction.student_id)
            .subquery()
        )

    @staticmethod
    def _latest_prediction_subq(db: Session):
        """Subquery of latest Prediction rows (one per student where present)."""
        latest = StudentService._latest_prediction_subquery(db)
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
    def _prediction_risk_to_0_100(pred_row: Any) -> Optional[float]:
        """Convert Prediction.risk_score (0-1) to API's 0-100 scale."""
        if pred_row is None:
            return None
        raw = getattr(pred_row, "risk_score", None)
        if raw is None:
            return None
        try:
            v = float(raw)
        except Exception:
            return None
        if not (v == v):
            return None
        if 0.0 <= v <= 1.0:
            v *= 100.0
        return max(0.0, min(100.0, round(v, 2)))

    @staticmethod
    def _enrollment_to_dict(enrollment: Enrollment, course_name: Optional[str]) -> Dict:
        return {
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

    @staticmethod
    def _graded_component_to_dict(component: GradedComponent) -> Dict:
        return {
            "component_type": component.component_type,
            "component_number": component.component_number,
            "score": component.score,
            "max_score": component.max_score,
            "missed": component.missed,
            "course_code": component.course_code,
            "course_name": component.course_name,
        }

    @staticmethod
    def _exam_record_to_dict(exam: ExamRecord) -> Dict:
        return {
            "course_code": exam.course_code,
            "course_name": exam.course_name,
            "slot": exam.slot,
            "marks_obtained": exam.marks_obtained,
            "marks_total": exam.marks_total,
            "present": exam.present,
            "mode": exam.mode,
        }

    @staticmethod
    def _fetch_enrollments_map(db: Session, student_ids: List[str]) -> Dict[str, List[Dict]]:
        if not student_ids:
            return {}
        rows = (
            db.query(Enrollment, Course.name)
            .join(Course, Enrollment.course_id == Course.id, isouter=True)
            .filter(Enrollment.student_id.in_(student_ids))
            .all()
        )
        enrollment_map: Dict[str, List[Dict]] = {sid: [] for sid in student_ids}
        for enrollment, course_name in rows:
            enrollment_map.setdefault(enrollment.student_id, []).append(
                StudentService._enrollment_to_dict(enrollment, course_name)
            )
        return enrollment_map

    @staticmethod
    def _fetch_graded_map(db: Session, student_ids: List[str]) -> Dict[str, List[Dict]]:
        if not student_ids:
            return {}
        rows = db.query(GradedComponent).filter(GradedComponent.student_id.in_(student_ids)).all()
        graded_map: Dict[str, List[Dict]] = {sid: [] for sid in student_ids}
        for g in rows:
            graded_map.setdefault(g.student_id, []).append(StudentService._graded_component_to_dict(g))
        return graded_map

    @staticmethod
    def _fetch_exam_map(db: Session, student_ids: List[str]) -> Dict[str, List[Dict]]:
        if not student_ids:
            return {}
        rows = db.query(ExamRecord).filter(ExamRecord.student_id.in_(student_ids)).all()
        exam_map: Dict[str, List[Dict]] = {sid: [] for sid in student_ids}
        for e in rows:
            exam_map.setdefault(e.student_id, []).append(StudentService._exam_record_to_dict(e))
        return exam_map

    @staticmethod
    def _sort_expr_for_students(sort_by: str, order: str, pred_subq):
        """DB ordering where possible; otherwise falls back to latest prediction risk."""
        direction = {"asc": lambda x: x.asc(), "desc": lambda x: x.desc()}.get(order, lambda x: x.desc())

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
        if sort_by == "risk_score":
            return (case((risk.is_(None), 1), else_=0), direction(risk))
        return (case((risk.is_(None), 1), else_=0), direction(risk))

    @staticmethod
    def get_interventions_by_student_id(db: Session, student_id: str) -> List[Intervention]:
        """Get all interventions for a specific student."""
        return db.query(Intervention).filter(Intervention.student_id == student_id).all()

    @staticmethod
    def _get_enrollment_dicts(db: Session, student_id: str) -> List[Dict]:
        """Get enrollment records for a student as dictionaries."""
        return StudentService._fetch_enrollments_map(db, [student_id]).get(student_id, [])

    @staticmethod
    def _get_graded_components(db: Session, student_id: str) -> List[Dict]:
        """Get graded quiz/assignment records for a student."""
        return StudentService._fetch_graded_map(db, [student_id]).get(student_id, [])

    @staticmethod
    def _get_exam_records(db: Session, student_id: str) -> List[Dict]:
        """Get exam records for a student."""
        return StudentService._fetch_exam_map(db, [student_id]).get(student_id, [])

    # ------------------------------------------------------------------ #
    # Internal helpers (feature computation + scoring + shaping)
    # ------------------------------------------------------------------ #

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
        pred_risk_0_100 = StudentService._prediction_risk_to_0_100(pred_row)
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
            # Compatibility fields for frontend
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
        """Calculate all metrics for a single student."""
        features = StudentService._calculate_features(enrollment_dicts, graded_dicts, exam_dicts)
        risk_fields = StudentService._derive_risk_fields(features)
        return StudentService._build_student_metrics_response(student, features, risk_fields)

    @staticmethod
    def get_student_by_id(db: Session, student_id: str) -> Optional[Dict]:
        """Get student with calculated metrics by ID."""
        student = db.query(Student).filter(Student.id == student_id).first()

        if not student:
            return None

        enrollment_dicts = StudentService._get_enrollment_dicts(db, student_id)
        graded_dicts = StudentService._get_graded_components(db, student_id)
        exam_dicts = StudentService._get_exam_records(db, student_id)
        return StudentService.calculate_student_metrics(
            student, enrollment_dicts, graded_dicts, exam_dicts
        )

    @staticmethod
    def get_all_students(db: Session, skip: int = 0, limit: int = 100,
                         sort_by: str = 'risk_score', order: str = 'desc',
                         risk_min: Optional[float] = None,
                         risk_max: Optional[float] = None) -> List[Dict]:
        """
        Get students with calculated metrics, with filtering and pagination.

        Key optimizations:
        - Pagination moved to DB via offset/limit.
        - Avoids full-table loads by fetching only the requested page.
        - Eliminates N+1 by batch-loading enrollments/graded/exams for page IDs.
        - Avoids recomputing risk for ordering/filtering by using latest stored Predictions.
        """

        pred_subq = StudentService._latest_prediction_subq(db)
        base = db.query(Student, pred_subq).outerjoin(pred_subq, pred_subq.c.student_id == Student.id)

        risk_expr = cast(pred_subq.c.risk_score, Float)
        if risk_min is not None:
            rm = float(risk_min) / 100.0 if float(risk_min) > 1.0 else float(risk_min)
            base = base.filter(risk_expr.isnot(None)).filter(risk_expr >= rm)
        if risk_max is not None:
            rx = float(risk_max) / 100.0 if float(risk_max) > 1.0 else float(risk_max)
            base = base.filter(risk_expr.isnot(None)).filter(risk_expr <= rx)

        sort_expr = StudentService._sort_expr_for_students(sort_by, order, pred_subq)
        if isinstance(sort_expr, tuple):
            base = base.order_by(*sort_expr)
        else:
            base = base.order_by(sort_expr)

        rows = base.offset(skip).limit(limit).all()
        students: List[Student] = [r[0] for r in rows]
        pred_rows = [r[1] for r in rows]
        student_ids = [s.id for s in students]

        enrollment_map = StudentService._fetch_enrollments_map(db, student_ids)
        graded_map = StudentService._fetch_graded_map(db, student_ids)
        exam_map = StudentService._fetch_exam_map(db, student_ids)

        result: List[Dict] = []
        for student, pred_row in zip(students, pred_rows):
            enrollments = enrollment_map.get(student.id, [])
            graded = graded_map.get(student.id, [])
            exams = exam_map.get(student.id, [])

            features = StudentService._calculate_features(enrollments, graded, exams)
            risk_fields = StudentService._derive_risk_fields(features, pred_row=pred_row)
            result.append(StudentService._build_student_metrics_response(student, features, risk_fields))

        # Preserve legacy in-page sorting for computed fields (response structure unchanged).
        reverse = (order == "desc")
        sortable_fields = [
            "risk_score",
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
        if sort_by in sortable_fields:
            result.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=reverse)
        elif sort_by == "id":
            result.sort(key=lambda x: x["id"], reverse=reverse)

        return result

    @staticmethod
    def get_overview_stats(db: Session) -> Dict:
        """Get overview statistics for the dashboard."""
        total_students = db.query(func.count(Student.id)).scalar() or 0
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

        pred = StudentService._latest_prediction_subq(db)
        risk = cast(pred.c.risk_score, Float)
        risk_0_100 = case((risk <= 1.0, risk * 100.0), else_=risk)

        avg_risk = (
            db.query(func.avg(risk_0_100))
            .select_from(pred)
            .filter(risk.isnot(None))
            .scalar()
        )
        avg_risk_val = round(float(avg_risk or 0.0), 2)

        # Counts by category from thresholds used by RiskScorer.
        low_count = (
            db.query(func.count(pred.c.student_id))
            .select_from(pred)
            .filter(risk.isnot(None))
            .filter(risk_0_100 < RiskScorer.RISK_THRESHOLDS["low"])
            .scalar()
            or 0
        )
        medium_count = (
            db.query(func.count(pred.c.student_id))
            .select_from(pred)
            .filter(risk.isnot(None))
            .filter(risk_0_100 >= RiskScorer.RISK_THRESHOLDS["low"])
            .filter(risk_0_100 < RiskScorer.RISK_THRESHOLDS["medium"])
            .scalar()
            or 0
        )
        high_count = (
            db.query(func.count(pred.c.student_id))
            .select_from(pred)
            .filter(risk.isnot(None))
            .filter(risk_0_100 >= RiskScorer.RISK_THRESHOLDS["medium"])
            .scalar()
            or 0
        )

        return {
            "total_students": int(total_students),
            "at_risk_students": int(high_count),
            "average_risk_score": avg_risk_val,
            "risk_distribution": {
                "low": int(low_count),
                "medium": int(medium_count),
                "high": int(high_count),
            },
            "total_enrollments": int(total_enrollments),
            "total_courses": int(total_courses),
        }

    @staticmethod
    def get_courses(db: Session) -> List[Dict]:
        """Get all courses with content requirements."""
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
    def get_course_engagement(db: Session, course_id: str) -> Optional[Dict]:
        """Get engagement breakdown for a specific course."""
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return None
        e = Enrollment

        total_enrolled = db.query(func.count(e.id)).filter(e.course_id == course_id).scalar() or 0
        sum_completed = (
            db.query(func.coalesce(func.sum(e.content_completed), 0))
            .filter(e.course_id == course_id)
            .scalar()
            or 0
        )
        sum_time = (
            db.query(func.coalesce(func.sum(e.total_time_spent_seconds), 0))
            .filter(e.course_id == course_id)
            .scalar()
            or 0
        )

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
        avg_completed = round(float(sum_completed) / max(int(total_enrolled), 1), 2)
        avg_time_hours = round(float(sum_time) / max(int(total_enrolled), 1) / 3600.0, 2)

        return {
            "course_id": course.id,
            "course_name": course.name,
            "total_enrolled": int(total_enrolled),
            "zero_progress": int(zero_progress),
            "low_progress_0_10": int(low_progress),
            "active_above_10": int(active),
            "avg_content_completed": avg_completed,
            "avg_time_spent_hours": avg_time_hours,
        }

    @staticmethod
    def get_risk_distribution(db: Session) -> Dict:
        """Get risk score distribution and percentiles across all students."""
        pred = StudentService._latest_prediction_subq(db)
        risk = cast(pred.c.risk_score, Float)
        risk_0_100 = case((risk <= 1.0, risk * 100.0), else_=risk)

        n = (
            db.query(func.count(pred.c.student_id))
            .select_from(pred)
            .filter(risk.isnot(None))
            .scalar()
            or 0
        )
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

        return {
            "histogram": histogram,
            "percentiles": {
                "p25": kth_value(25),
                "p50": kth_value(50),
                "p75": kth_value(75),
                "p90": kth_value(90),
            },
        }

    @staticmethod
    def get_analytics_data(db: Session) -> Dict:
        """Get analytics data - per-department and per-course engagement summaries."""
        pred = StudentService._latest_prediction_subq(db)
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
            {
                "department": dept,
                "student_count": int(count or 0),
                "avg_risk_score": round(float(avg or 0.0), 2),
            }
            for dept, count, avg in dept_rows
        ]

        # Per-course enrollment stats
        course_stats = (
            db.query(
                Course.name,
                func.count(Enrollment.id),
                func.avg(Enrollment.content_completed),
                func.sum(Enrollment.total_time_spent_seconds),
            )
            .join(Enrollment, Course.id == Enrollment.course_id, isouter=True)
            .group_by(Course.name)
            .all()
        )

        course_summary = []
        for name, count, avg_completed, total_time in course_stats:
            course_summary.append({
                "course": name,
                "enrollments": count or 0,
                "avg_content_completed": round(avg_completed or 0, 2),
                "total_time_hours": round((total_time or 0) / 3600, 2),
            })

        return {
            "department_summary": department_summary,
            "course_summary": course_summary,
            "total_analyzed": int(db.query(func.count(Student.id)).scalar() or 0),
        }

    # ------------------------------------------------------------------ #
    # Prediction helpers (used by controllers)
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_prediction_payload(student_metrics: Dict) -> Dict:
        """
        Build a consistent prediction payload from a student metrics dict.

        This keeps controllers free of transformation logic while preserving
        the existing response shape expected by the frontend.
        """
        risk = student_metrics["risk_score"]
        payload = {
            "student_id": student_metrics["id"],
            "risk_score": risk / 100.0,
            "engagement_score": (100 - risk) / 100.0,
            "retention_likelihood": student_metrics["retention_likelihood"],
            "model_version": "rule_based_v2",
            "signal_breakdown": {
                "academic_signal_score": student_metrics.get("graded_quiz_score", 0) / 100.0,
                "engagement_signal_score": student_metrics.get("content_completion_score", 0) / 100.0,
                "consistency_signal_score": student_metrics.get("exam_attendance_rate", 0) / 100.0,
                "intent_signal_score": student_metrics.get("graded_assignment_score", 0) / 100.0,
                "responsiveness_signal_score": student_metrics.get("exam_score", 0) / 100.0,
            },
            "top_risk_factors": [student_metrics.get("dominant_risk_factor", "Unknown")],
            "prediction_error": False,
        }
        return payload

    @staticmethod
    def build_intervention_recommendation(risk_score: float) -> Dict:
        """
        Derive intervention recommendation from a risk score.
        Keeps business rules centralised in the service layer.
        """
        if risk_score >= 80:
            category = "urgent"
            action = "Immediate outreach required"
            channels = ["whatsapp", "phone", "email"]
            team = "sales"
        elif risk_score >= 60:
            category = "mentor_outreach"
            action = "Schedule mentor meeting"
            channels = ["email", "mentor_call"]
            team = "faculty"
        elif risk_score >= 40:
            category = "gentle_reminder"
            action = "Send encouragement email"
            channels = ["email"]
            team = "automated"
        else:
            category = "no_action"
            action = "No intervention needed"
            channels = []
            team = "none"

        return {
            "threshold_category": category,
            "action_type": action,
            "channels": channels,
            "assigned_team": team,
            "priority": "critical" if risk_score >= 80 else "high" if risk_score >= 60 else "medium" if risk_score >= 40 else "low",
            "urgency": category,
            "description": action,
        }

    @staticmethod
    def get_student_count(db: Session) -> int:
        """Return the total number of students in the database."""
        return db.query(func.count(Student.id)).scalar() or 0
