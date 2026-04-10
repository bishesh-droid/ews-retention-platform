"""
Student application service orchestration.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import Float, Integer, case, cast, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

import backend.config as settings
from backend.config import RISK_THRESHOLD_HIGH, RISK_THRESHOLD_MEDIUM, trimester_week_number
from backend.database import Course, Enrollment, Student
from backend.domain.student import build_intervention_recommendation
from backend.infrastructure.student_repository import StudentRepository
from backend.database.models.intervention_log import InterventionLog
from backend.services.feature_engineering import FeatureEngineer
from backend.services.calendar_scorer import get_current_week
from backend.services.risk_scoring import RiskScorer


class StudentApplicationService:
    @staticmethod
    def _infer_program_from_student(student: Student) -> str:
        dept = (getattr(student, "parent_department_name", "") or "").lower()
        return "MSc" if "msc" in dept else "BS"

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
        *,
        is_new_student: bool = False,
        week_number: Optional[int] = None,
    ) -> Dict:
        wn = week_number if week_number is not None else trimester_week_number()
        return FeatureEngineer.calculate_all_features(
            enrollment_dicts,
            graded_components=graded_dicts,
            exam_records=exam_dicts,
            is_new_student=is_new_student,
            week_number=wn,
        )

    @staticmethod
    def _derive_risk_fields(
        features: Dict,
        *,
        graded_dicts: Optional[List[Dict]] = None,
        program: Optional[str] = None,
        current_week: Optional[int] = None,
        pred_row: Optional[Any] = None,
    ) -> Dict:
        pred_risk_0_100 = StudentApplicationService._prediction_risk_to_0_100(pred_row)
        if pred_risk_0_100 is None:
            risk_score = RiskScorer.calculate_risk_score(
                features,
                graded_components=graded_dicts or [],
                program=program,
                current_week=current_week,
            )
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
        engagement_pattern = features.get("engagement_pattern", "on_track")
        return {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "name": " ".join(filter(None, [student.first_name, student.last_name])).strip() or student.id,
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
            # BREAKING_CHANGE: renamed from attendance_score in v1.1
            "exam_attendance_score": features.get("exam_attendance_rate"),
            "attendance_score": features.get("exam_attendance_rate"),  # DEPRECATED — remove in v1.2
            "academic_score": features["content_completion_score"],
            "behavioral_score": features["discussion_engagement_score"],
            "stability_score": features["time_investment_score"],
            "engagement_pattern": engagement_pattern,
            "engagement_pattern_label": {
                "disengaged": "Not engaging with platform",
                "struggling": "Active but needs academic support",
                "at_risk_normal": "At risk",
                "on_track": "On track",
            }.get(engagement_pattern, "Unknown"),
            "is_ghost": features.get("ghost_info", {}).get("is_ghost", False),
            "ghost_type": features.get("ghost_info", {}).get("ghost_type"),
            "requires_activation_outreach": features.get("requires_activation_outreach", False),
            "score_basis": "rule_based_formula",
        }

    @staticmethod
    def calculate_student_metrics(
        student: Student,
        enrollment_dicts: List[Dict],
        graded_dicts: Optional[List[Dict]] = None,
        exam_dicts: Optional[List[Dict]] = None,
    ) -> Dict:
        is_new = (student.old_new_student or "").lower() == "new"
        wn = trimester_week_number()
        program = StudentApplicationService._infer_program_from_student(student)
        current_week = get_current_week(settings.TRIMESTER_START_DATE)
        features = StudentApplicationService._calculate_features(
            enrollment_dicts,
            graded_dicts,
            exam_dicts,
            is_new_student=is_new,
            week_number=wn,
        )
        risk_fields = StudentApplicationService._derive_risk_fields(
            features,
            graded_dicts=graded_dicts,
            program=program,
            current_week=current_week,
        )
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
        activation_required: Optional[bool] = None,
        semester_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get paginated students with computed risk metrics.

        Returns dict with:
        - students: List[Dict] — the student records
        - total: int — total count for pagination (accounts for risk filters)
        """
        # D8-3: Default to current semester if not specified
        if semester_name is None:
            semester_name = settings.CURRENT_SEMESTER_NAME

        pred_subq = StudentRepository.latest_prediction_rows_subquery(db)
        base = db.query(Student, pred_subq).outerjoin(pred_subq, pred_subq.c.student_id == Student.id)

        if current_user is not None:
            role = (getattr(current_user, "role", "") or "").lower()
            is_superuser = bool(getattr(current_user, "is_superuser", False))
            if role == "faculty" and not is_superuser:
                dept = getattr(current_user, "department", None)
                if dept:
                    base = base.filter(Student.parent_department_name == dept)

        # Note: Risk filtering is done post-computation (below) using live RiskScorer
        # results rather than stale Prediction table values. This ensures fresh data
        # and works even when Prediction table is empty.

        sort_expr = StudentRepository.sort_expr_for_students(sort_by, order, pred_subq)
        base = base.order_by(*sort_expr) if isinstance(sort_expr, tuple) else base.order_by(sort_expr)
        rows = base.offset(skip).limit(limit).all()

        students: List[Student] = [r[0] for r in rows]
        pred_rows = [r[1] for r in rows]
        student_ids = [s.id for s in students]

        # D5-2: Use pre-computed feature store for list view (fast path)
        from backend.database.models.event import EngineeredFeatures

        feat_map = {
            f.student_id: {
                "assignment_completion_rate": f.assignment_completion_rate,
                "average_grade": f.average_grade,
                "deadline_adherence_score": f.deadline_adherence_score,
                "grade_trend": f.grade_trend,
                "login_frequency": f.login_frequency,
                "avg_session_duration": f.avg_session_duration,
                "video_completion_rate": f.video_completion_rate,
                "platform_interaction_score": f.platform_interaction_score,
                "attendance_rate": f.attendance_rate,
                "activity_regularity_score": f.activity_regularity_score,
                "missed_classes_count": f.missed_classes_count,
                "attendance_trend": f.attendance_trend,
                "engagement_trend": f.engagement_trend,
                "days_inactive": f.days_inactive,
                "declining_performance_flag": f.declining_performance_flag,
                "email_open_rate": f.email_open_rate,
                "message_reply_rate": f.message_reply_rate,
                "avg_response_time_hours": f.avg_response_time_hours,
            }
            for f in db.query(EngineeredFeatures)
            .filter(EngineeredFeatures.student_id.in_(student_ids))
            .all()
        }

        # Fallback: fetch enrollment/graded/exam data for students not in feature store
        missing_ids = [sid for sid in student_ids if sid not in feat_map]
        if missing_ids:
            enrollment_map = StudentRepository.fetch_enrollments_map(db, missing_ids)  # type: ignore[arg-type]
            graded_map = StudentRepository.fetch_graded_map(db, missing_ids)  # type: ignore[arg-type]
            exam_map = StudentRepository.fetch_exam_map(db, missing_ids)  # type: ignore[arg-type]
        else:
            enrollment_map, graded_map, exam_map = {}, {}, {}

        result: List[Dict] = []
        for student, pred_row in zip(students, pred_rows):
            is_new = (student.old_new_student or "").lower() == "new"
            wn = trimester_week_number()
            program = StudentApplicationService._infer_program_from_student(student)
            current_week = get_current_week(settings.TRIMESTER_START_DATE)

            # Read from feature store if available, else compute live
            features = feat_map.get(student.id)  # type: ignore[arg-type]
            if features is None:
                # Fall back to live computation for students not yet in feature store
                features = StudentApplicationService._calculate_features(
                    enrollment_map.get(student.id, []),  # type: ignore[arg-type]
                    graded_map.get(student.id, []),  # type: ignore[arg-type]
                    exam_map.get(student.id, []),  # type: ignore[arg-type]
                    is_new_student=is_new,
                    week_number=wn,
                )

            risk_fields = StudentApplicationService._derive_risk_fields(
                features,
                graded_dicts=graded_map.get(student.id, []),  # type: ignore[arg-type]
                program=program,
                current_week=current_week,
                pred_row=pred_row,
            )
            result.append(StudentApplicationService._build_student_metrics_response(student, features, risk_fields))

        # Post-computation filters for derived fields (risk_score, activation_required)
        # These use LIVE computed values, not stale Prediction table data
        if risk_min is not None:
            rm = float(risk_min)  # Always 0-100 scale, no normalization needed
            result = [s for s in result if s.get("risk_score", 0) >= rm]
        if risk_max is not None:
            rx = float(risk_max)  # Always 0-100 scale, no normalization needed
            result = [s for s in result if s.get("risk_score", 0) <= rx]
        if activation_required is not None:
            result = [s for s in result if s.get("requires_activation_outreach") == activation_required]

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
            "exam_attendance_score",  # BREAKING_CHANGE: renamed from attendance_score in v1.1
            "academic_score",
            "behavioral_score",
            "stability_score",
        ]
        if sort_by in computed_fields:
            result.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=reverse)

        # D5-1: Fix pagination total when risk filter is applied
        # Risk filtering is post-computation — derive count from filtered results
        if risk_min is not None or risk_max is not None:
            total = len(result)
        else:
            total = len(result)  # For DB-filtered case, this matches the query count

        return {
            "students": result,
            "total": total,
        }

    @staticmethod
    def get_student_count_filtered(
        db: Session,
        risk_min: Optional[float] = None,
        risk_max: Optional[float] = None,
        current_user=None,
    ) -> int:
        """
        Get count of students matching filters.

        Note: Risk filtering is NOT applied at the DB level because the Prediction
        table may be empty or stale. To filter by risk, use get_all_students()
        and count the results (risk filter is applied post-computation there).

        This function returns the total count for pagination purposes when
        risk filters are not active.
        """
        base = db.query(func.count(Student.id))

        if current_user is not None:
            role = (getattr(current_user, "role", "") or "").lower()
            is_superuser = bool(getattr(current_user, "is_superuser", False))
            if role == "faculty" and not is_superuser:
                dept = getattr(current_user, "department", None)
                if dept:
                    base = base.filter(Student.parent_department_name == dept)

        # Note: Risk filtering is NOT applied here. The Prediction table may be
        # empty (fresh install) or stale. Risk filtering happens post-computation
        # in get_all_students() using live RiskScorer results.
        # For accurate counts with risk filters, use len(get_all_students(...))

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
        # Calculate ghost student statistics
        ghost_stats = {"never_logged_in": 0, "logged_in_never_started": 0, "total_ghosts": 0}
        students_with_enrollments = db.query(Student).all()
        for student in students_with_enrollments:
            enrollment_dicts = StudentRepository.fetch_enrollments_map(
                db, [student.id]
            ).get(student.id, [])  # type: ignore[arg-type, list-item]
            if enrollment_dicts:
                from backend.services.feature_engineering import FeatureEngineer
                total_logins = sum(e.get("num_logins", 0) or 0 for e in enrollment_dicts)
                ghost_info = FeatureEngineer.detect_ghost_student(enrollment_dicts, total_logins)
                if ghost_info.get("is_ghost"):
                    ghost_stats["total_ghosts"] += 1
                    ghost_type = ghost_info.get("ghost_type")
                    if ghost_type in ghost_stats:
                        ghost_stats[ghost_type] += 1

        return {
            "total_students": int(total_students),
            "at_risk_students": int(high_count),
            "average_risk_score": round(float(avg_risk or 0.0), 2),
            "risk_distribution": {"low": int(low_count), "medium": int(medium_count), "high": int(high_count)},
            "total_enrollments": int(total_enrollments),
            "total_courses": int(total_courses),
            "activation_required_count": ghost_stats["total_ghosts"],
            "ghost_breakdown": {
                "never_logged_in": ghost_stats["never_logged_in"],
                "logged_in_never_started": ghost_stats["logged_in_never_started"],
            },
        }

    @staticmethod
    def get_cohort_engagement_patterns(db: Session, current_user=None) -> Dict[str, int]:
        """
        Calculate engagement pattern distribution across the cohort.

        Returns:
            Dict with counts for each engagement pattern category
        """

        pred_subq = StudentRepository.latest_prediction_rows_subquery(db)
        base = db.query(Student).outerjoin(pred_subq, pred_subq.c.student_id == Student.id)

        if current_user is not None:
            role = (getattr(current_user, "role", "") or "").lower()
            is_superuser = bool(getattr(current_user, "is_superuser", False))
            if role == "faculty" and not is_superuser:
                dept = getattr(current_user, "department", None)
                if dept:
                    base = base.filter(Student.parent_department_name == dept)

        students = base.all()
        if not students:
            return {"disengaged": 0, "struggling": 0, "at_risk_normal": 0, "on_track": 0}

        student_ids = [s.id for s in students]
        enrollment_map = StudentRepository.fetch_enrollments_map(db, student_ids)  # type: ignore[arg-type]
        graded_map = StudentRepository.fetch_graded_map(db, student_ids)  # type: ignore[arg-type]
        exam_map = StudentRepository.fetch_exam_map(db, student_ids)  # type: ignore[arg-type]

        patterns = {"disengaged": 0, "struggling": 0, "at_risk_normal": 0, "on_track": 0}

        for student in students:
            is_new = (student.old_new_student or "").lower() == "new"
            wn = trimester_week_number()
            features = StudentApplicationService._calculate_features(
                enrollment_map.get(student.id, []),  # type: ignore[arg-type]
                graded_map.get(student.id, []),  # type: ignore[arg-type]
                exam_map.get(student.id, []),  # type: ignore[arg-type]
                is_new_student=is_new,
                week_number=wn,
            )
            pattern = features.get("engagement_pattern", "on_track")
            if pattern in patterns:
                patterns[pattern] += 1

        return patterns

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
        sum_completed = db.query(func.coalesce(func.sum(e.content_completed), 0)
                                 ).filter(e.course_id == course_id).scalar() or 0
        sum_time = db.query(func.coalesce(func.sum(e.total_time_spent_seconds), 0)
                            ).filter(e.course_id == course_id).scalar() or 0
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
            db.query(Course.name, func.count(Enrollment.id), func.avg(
                Enrollment.content_completed), func.sum(Enrollment.total_time_spent_seconds))
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
        return {
            "department_summary": department_summary,
            "course_summary": course_summary,
            "total_analyzed": StudentRepository.student_count(db),
        }

    @staticmethod
    def build_prediction_payload(student_metrics: Dict) -> Dict:
        risk = float(student_metrics["risk_score"])
        return {
            "student_id": student_metrics["id"],
            "risk_score": risk / 100.0,
            "engagement_score": (100 - risk) / 100.0,
            "retention_likelihood": student_metrics["retention_likelihood"],
            "model_version": "rule_based_v2",
            "model_type": "rule_based",
            "model_description": "Weighted engagement formula — not a trained ML model",
            "score_basis": "rule_based_formula",
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

    @staticmethod
    def _log_intervention_if_new(
        db: Session,
        student_org_id: str,
        intervention: Dict,
        risk_score: float,
        week_number: int,
        semester: str,
    ) -> Optional[InterventionLog]:
        """
        Log an intervention recommendation if one doesn't already exist for this student-week.

        Only logs for intervention types that are not "none" (skips suppressed interventions).
        """
        from backend.database.models.intervention_log import InterventionLog
        from backend.config import trimester_week_number

        intervention_type = intervention.get("type")
        if not intervention_type or intervention_type == "none":
            return None  # Skip suppressed interventions

        if week_number is None:
            week_number = trimester_week_number()

        log_data = {
            "student_org_id": student_org_id,
            "intervention_type": intervention_type,
            "engagement_pattern": intervention.get("engagement_pattern"),
            "risk_score_at_recommendation": risk_score,
            "week_number": week_number,
            "semester_name": semester,
        }

        # Upsert: insert or ignore on conflict
        stmt = sqlite_insert(InterventionLog).values(**log_data)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['student_org_id', 'week_number', 'semester_name', 'intervention_type']
        )
        db.execute(stmt)
        db.commit()

        # Return the existing or newly created log
        return db.query(InterventionLog).filter(
            InterventionLog.student_org_id == student_org_id,
            InterventionLog.week_number == week_number,
            InterventionLog.semester_name == semester,
            InterventionLog.intervention_type == intervention_type,
        ).first()

    @staticmethod
    def build_and_log_intervention_recommendation(
        db: Session,
        student: Student,
        risk_score: float,
        features: Dict,
    ) -> Dict:
        """
        Build intervention recommendation and log it to InterventionLog.

        Args:
            db: Database session
            student: Student object with org_defined_id
            risk_score: Current risk score
            features: Feature dictionary with engagement_pattern

        Returns:
            Intervention recommendation dictionary
        """
        from backend.services.core.decision_engine import get_intervention_recommendation

        engagement_pattern = features.get("engagement_pattern")
        intervention = get_intervention_recommendation(
            risk_score,
            engagement_pattern=engagement_pattern,
            features=features,
        )

        # Log the intervention (if not suppressed)
        if student.org_defined_id:
            semester = getattr(student, "semester_name", None) or ""
            StudentApplicationService._log_intervention_if_new(
                db=db,
                student_org_id=str(student.org_defined_id),
                intervention=intervention,
                risk_score=risk_score,
                week_number=int(features.get("week_number") or 0),
                semester=semester,
            )

        return intervention
