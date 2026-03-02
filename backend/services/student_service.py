"""
Student Service for EWS Retention Platform.

Integrates feature engineering and risk scoring to provide
comprehensive student engagement data from real XLSX data.
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.services.feature_engineering import FeatureEngineer
from backend.services.risk_scoring import RiskScorer
from backend.database import Student, Course, Enrollment, GradedComponent, ExamRecord, Intervention


class StudentService:
    """
    Service for retrieving and calculating student engagement metrics.
    """

    @staticmethod
    def get_interventions_by_student_id(db: Session, student_id: str) -> List[Intervention]:
        """Get all interventions for a specific student."""
        return db.query(Intervention).filter(Intervention.student_id == student_id).all()

    @staticmethod
    def _get_enrollment_dicts(db: Session, student_id: str) -> List[Dict]:
        """Get enrollment records for a student as dictionaries."""
        enrollments = (
            db.query(Enrollment, Course.name)
            .join(Course, Enrollment.course_id == Course.id, isouter=True)
            .filter(Enrollment.student_id == student_id)
            .all()
        )

        result = []
        for enrollment, course_name in enrollments:
            d = {
                'course_id': enrollment.course_id,
                'course_name': course_name or '',
                'content_completed': enrollment.content_completed,
                'content_required': enrollment.content_required,
                'content_required_w1w2': enrollment.content_required_w1w2,
                'checklist_completed': enrollment.checklist_completed,
                'quiz_completed': enrollment.quiz_completed,
                'total_quiz_attempts': enrollment.total_quiz_attempts,
                'last_quiz_attempt_date': enrollment.last_quiz_attempt_date,
                'discussion_posts_created': enrollment.discussion_posts_created,
                'discussion_post_replies': enrollment.discussion_post_replies,
                'discussion_posts_read': enrollment.discussion_posts_read,
                'last_discussion_post_date': enrollment.last_discussion_post_date,
                'num_assignment_submissions': enrollment.num_assignment_submissions,
                'last_assignment_submission_date': enrollment.last_assignment_submission_date,
                'total_time_spent_seconds': enrollment.total_time_spent_seconds,
                'last_visited_date': enrollment.last_visited_date,
                'last_system_login': enrollment.last_system_login,
                'num_logins': enrollment.num_logins,
                'last_scorm_completion_date': enrollment.last_scorm_completion_date,
                'last_scorm_visit_date': enrollment.last_scorm_visit_date,
            }
            result.append(d)

        return result

    @staticmethod
    def _get_graded_components(db: Session, student_id: str) -> List[Dict]:
        """Get graded quiz/assignment records for a student."""
        records = db.query(GradedComponent).filter(
            GradedComponent.student_id == student_id
        ).all()
        return [
            {
                'component_type': r.component_type,
                'component_number': r.component_number,
                'score': r.score,
                'max_score': r.max_score,
                'missed': r.missed,
                'course_code': r.course_code,
                'course_name': r.course_name,
            }
            for r in records
        ]

    @staticmethod
    def _get_exam_records(db: Session, student_id: str) -> List[Dict]:
        """Get exam records for a student."""
        records = db.query(ExamRecord).filter(
            ExamRecord.student_id == student_id
        ).all()
        return [
            {
                'course_code': r.course_code,
                'course_name': r.course_name,
                'slot': r.slot,
                'marks_obtained': r.marks_obtained,
                'marks_total': r.marks_total,
                'present': r.present,
                'mode': r.mode,
            }
            for r in records
        ]

    @staticmethod
    def calculate_student_metrics(student: Student, enrollment_dicts: List[Dict],
                                  graded_dicts: List[Dict] = None,
                                  exam_dicts: List[Dict] = None) -> Dict:
        """Calculate all metrics for a single student."""
        features = FeatureEngineer.calculate_all_features(
            enrollment_dicts,
            graded_components=graded_dicts,
            exam_records=exam_dicts,
        )
        risk_score = RiskScorer.calculate_risk_score(features)
        risk_category = RiskScorer.get_risk_category(risk_score)
        retention_likelihood = RiskScorer.get_retention_likelihood(risk_score)
        dominant_factor = RiskScorer.get_dominant_risk_factor(features)
        risk_breakdown = RiskScorer.get_risk_breakdown(features)

        return {
            'id': student.id,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'org_defined_id': student.org_defined_id,
            'department': student.parent_department_name,
            'old_new_student': student.old_new_student,
            'is_active': student.is_active,
            'risk_score': risk_score,
            'risk_category': risk_category,
            'retention_likelihood': retention_likelihood,
            'dominant_risk_factor': dominant_factor,
            'risk_breakdown': risk_breakdown,
            'content_completion_score': features['content_completion_score'],
            'w1w2_completion_score': features['w1w2_completion_score'],
            'quiz_engagement_score': features['quiz_engagement_score'],
            'discussion_engagement_score': features['discussion_engagement_score'],
            'login_consistency_score': features['login_consistency_score'],
            'time_investment_score': features['time_investment_score'],
            'assignment_score': features['assignment_score'],
            'graded_quiz_score': features['graded_quiz_score'],
            'graded_assignment_score': features['graded_assignment_score'],
            'exam_score': features['exam_score'],
            'exam_attendance_rate': features['exam_attendance_rate'],
            'zero_progress_ratio': features['zero_progress_ratio'],
            'progress_category': features['progress_category'],
            'trend': features['engagement_trend'],
            'total_courses': features['total_courses'],
            'per_course_breakdown': features['per_course_breakdown'],
            # Compatibility fields for frontend
            'attendance_score': features.get('exam_attendance_rate', 0),
            'academic_score': features['content_completion_score'],
            'behavioral_score': features['discussion_engagement_score'],
            'stability_score': features['time_investment_score'],
        }

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
        """Get all students with calculated metrics, with filtering and pagination."""
        students = db.query(Student).all()

        # Batch-fetch all enrollments
        all_enrollments = (
            db.query(Enrollment, Course.name)
            .join(Course, Enrollment.course_id == Course.id, isouter=True)
            .all()
        )
        enrollment_map = {}
        for enrollment, course_name in all_enrollments:
            if enrollment.student_id not in enrollment_map:
                enrollment_map[enrollment.student_id] = []
            enrollment_map[enrollment.student_id].append({
                'course_id': enrollment.course_id,
                'course_name': course_name or '',
                'content_completed': enrollment.content_completed,
                'content_required': enrollment.content_required,
                'content_required_w1w2': enrollment.content_required_w1w2,
                'checklist_completed': enrollment.checklist_completed,
                'quiz_completed': enrollment.quiz_completed,
                'total_quiz_attempts': enrollment.total_quiz_attempts,
                'last_quiz_attempt_date': enrollment.last_quiz_attempt_date,
                'discussion_posts_created': enrollment.discussion_posts_created,
                'discussion_post_replies': enrollment.discussion_post_replies,
                'discussion_posts_read': enrollment.discussion_posts_read,
                'last_discussion_post_date': enrollment.last_discussion_post_date,
                'num_assignment_submissions': enrollment.num_assignment_submissions,
                'last_assignment_submission_date': enrollment.last_assignment_submission_date,
                'total_time_spent_seconds': enrollment.total_time_spent_seconds,
                'last_visited_date': enrollment.last_visited_date,
                'last_system_login': enrollment.last_system_login,
                'num_logins': enrollment.num_logins,
                'last_scorm_completion_date': enrollment.last_scorm_completion_date,
                'last_scorm_visit_date': enrollment.last_scorm_visit_date,
            })

        # Batch-fetch graded components
        all_graded = db.query(GradedComponent).all()
        graded_map = {}
        for g in all_graded:
            if g.student_id not in graded_map:
                graded_map[g.student_id] = []
            graded_map[g.student_id].append({
                'component_type': g.component_type,
                'component_number': g.component_number,
                'score': g.score,
                'max_score': g.max_score,
                'missed': g.missed,
                'course_code': g.course_code,
                'course_name': g.course_name,
            })

        # Batch-fetch exam records
        all_exams = db.query(ExamRecord).all()
        exam_map = {}
        for e in all_exams:
            if e.student_id not in exam_map:
                exam_map[e.student_id] = []
            exam_map[e.student_id].append({
                'course_code': e.course_code,
                'course_name': e.course_name,
                'slot': e.slot,
                'marks_obtained': e.marks_obtained,
                'marks_total': e.marks_total,
                'present': e.present,
                'mode': e.mode,
            })

        # Calculate metrics for all students
        student_metrics = []
        for student in students:
            enrollments = enrollment_map.get(student.id, [])
            graded = graded_map.get(student.id, [])
            exams = exam_map.get(student.id, [])
            metrics = StudentService.calculate_student_metrics(
                student, enrollments, graded, exams
            )
            student_metrics.append(metrics)

        # Filter
        if risk_min is not None:
            student_metrics = [s for s in student_metrics if s['risk_score'] >= risk_min]
        if risk_max is not None:
            student_metrics = [s for s in student_metrics if s['risk_score'] <= risk_max]

        # Sort
        reverse = (order == 'desc')
        sortable_fields = [
            'risk_score', 'content_completion_score', 'quiz_engagement_score',
            'login_consistency_score', 'time_investment_score',
            'graded_quiz_score', 'graded_assignment_score', 'exam_score',
            'exam_attendance_rate', 'attendance_score', 'academic_score',
            'behavioral_score', 'stability_score',
        ]
        if sort_by in sortable_fields:
            student_metrics.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
        elif sort_by == 'id':
            student_metrics.sort(key=lambda x: x['id'], reverse=reverse)

        # Paginate
        return student_metrics[skip:skip + limit]

    @staticmethod
    def get_overview_stats(db: Session) -> Dict:
        """Get overview statistics for the dashboard."""
        students = db.query(Student).all()
        total_students = len(students)

        if total_students == 0:
            return {
                'total_students': 0,
                'at_risk_students': 0,
                'average_risk_score': 0,
                'risk_distribution': {'low': 0, 'medium': 0, 'high': 0},
                'total_enrollments': 0,
                'total_courses': 0,
            }

        # Batch-fetch enrollments
        all_enrollments = (
            db.query(Enrollment, Course.name)
            .join(Course, Enrollment.course_id == Course.id, isouter=True)
            .all()
        )
        enrollment_map = {}
        for enrollment, course_name in all_enrollments:
            if enrollment.student_id not in enrollment_map:
                enrollment_map[enrollment.student_id] = []
            enrollment_map[enrollment.student_id].append({
                'content_completed': enrollment.content_completed,
                'content_required': enrollment.content_required,
                'content_required_w1w2': enrollment.content_required_w1w2,
                'quiz_completed': enrollment.quiz_completed,
                'total_quiz_attempts': enrollment.total_quiz_attempts,
                'discussion_posts_created': enrollment.discussion_posts_created,
                'discussion_post_replies': enrollment.discussion_post_replies,
                'discussion_posts_read': enrollment.discussion_posts_read,
                'num_assignment_submissions': enrollment.num_assignment_submissions,
                'total_time_spent_seconds': enrollment.total_time_spent_seconds,
                'num_logins': enrollment.num_logins,
            })

        # Batch-fetch graded components
        all_graded = db.query(GradedComponent).all()
        graded_map = {}
        for g in all_graded:
            if g.student_id not in graded_map:
                graded_map[g.student_id] = []
            graded_map[g.student_id].append({
                'component_type': g.component_type,
                'score': g.score,
                'max_score': g.max_score,
                'missed': g.missed,
            })

        # Batch-fetch exam records
        all_exams = db.query(ExamRecord).all()
        exam_map = {}
        for e in all_exams:
            if e.student_id not in exam_map:
                exam_map[e.student_id] = []
            exam_map[e.student_id].append({
                'marks_obtained': e.marks_obtained,
                'marks_total': e.marks_total,
                'present': e.present,
            })

        risk_scores = []
        risk_categories = {'low': 0, 'medium': 0, 'high': 0}

        for student in students:
            enrollments = enrollment_map.get(student.id, [])
            graded = graded_map.get(student.id, [])
            exams = exam_map.get(student.id, [])
            features = FeatureEngineer.calculate_all_features(enrollments, graded, exams)
            risk_score = RiskScorer.calculate_risk_score(features)
            risk_category = RiskScorer.get_risk_category(risk_score)

            risk_scores.append(risk_score)
            risk_categories[risk_category] += 1

        average_risk = sum(risk_scores) / len(risk_scores)
        total_courses = db.query(func.count(Course.id)).scalar()
        total_enrollments = db.query(func.count(Enrollment.id)).scalar()

        return {
            'total_students': total_students,
            'at_risk_students': risk_categories['high'],
            'average_risk_score': round(average_risk, 2),
            'risk_distribution': risk_categories,
            'total_enrollments': total_enrollments,
            'total_courses': total_courses,
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

        enrollments = db.query(Enrollment).filter(Enrollment.course_id == course_id).all()

        zero_progress = sum(1 for e in enrollments if (e.content_completed or 0) == 0)
        low_progress = sum(
            1
            for e in enrollments
            if 0 < (e.content_completed or 0) <= ((e.content_required or 1) * 0.1)
        )
        active = len(enrollments) - zero_progress - low_progress

        return {
            "course_id": course.id,
            "course_name": course.name,
            "total_enrolled": len(enrollments),
            "zero_progress": zero_progress,
            "low_progress_0_10": low_progress,
            "active_above_10": active,
            "avg_content_completed": round(
                sum(e.content_completed or 0 for e in enrollments) / max(len(enrollments), 1),
                2,
            ),
            "avg_time_spent_hours": round(
                sum(e.total_time_spent_seconds or 0 for e in enrollments)
                / max(len(enrollments), 1)
                / 3600,
                2,
            ),
        }

    @staticmethod
    def get_risk_distribution(db: Session) -> Dict:
        """Get risk score distribution and percentiles across all students."""
        students = db.query(Student).all()

        if not students:
            return {"histogram": [], "percentiles": {}}

        # Pre-fetch enrollments
        all_enrollments = db.query(Enrollment).all()
        enrollment_map: Dict[str, List[Dict]] = {}
        for e in all_enrollments:
            if e.student_id not in enrollment_map:
                enrollment_map[e.student_id] = []
            enrollment_map[e.student_id].append(
                {
                    "content_completed": e.content_completed,
                    "content_required": e.content_required,
                    "content_required_w1w2": e.content_required_w1w2,
                    "quiz_completed": e.quiz_completed,
                    "total_quiz_attempts": e.total_quiz_attempts,
                    "discussion_posts_created": e.discussion_posts_created,
                    "discussion_post_replies": e.discussion_post_replies,
                    "discussion_posts_read": e.discussion_posts_read,
                    "num_assignment_submissions": e.num_assignment_submissions,
                    "total_time_spent_seconds": e.total_time_spent_seconds,
                    "num_logins": e.num_logins,
                }
            )

        risk_scores: List[float] = []
        for student in students:
            enrollments = enrollment_map.get(student.id, [])
            features = FeatureEngineer.calculate_all_features(enrollments)
            risk_score = RiskScorer.calculate_risk_score(features)
            risk_scores.append(risk_score)

        # Histogram
        buckets: Dict[str, int] = {}
        for score in risk_scores:
            bucket = int(score // 10) * 10
            bucket_label = f"{bucket}-{bucket + 10}"
            buckets[bucket_label] = buckets.get(bucket_label, 0) + 1

        histogram = [{"range": k, "count": v} for k, v in sorted(buckets.items())]

        # Percentiles
        sorted_scores = sorted(risk_scores)
        n = len(sorted_scores)

        def percentile(p: int) -> float:
            k = (n - 1) * p / 100
            f = int(k)
            c = k - f
            if f + 1 < n:
                return round(
                    sorted_scores[f] + c * (sorted_scores[f + 1] - sorted_scores[f]), 2
                )
            return round(sorted_scores[f], 2)

        return {
            "histogram": histogram,
            "percentiles": {
                "p25": percentile(25),
                "p50": percentile(50),
                "p75": percentile(75),
                "p90": percentile(90),
            },
        }

    @staticmethod
    def get_analytics_data(db: Session) -> Dict:
        """Get analytics data - per-department and per-course engagement summaries."""
        dept_stats = {}
        students = db.query(Student).all()

        all_enrollments = (
            db.query(Enrollment, Course.name)
            .join(Course, Enrollment.course_id == Course.id, isouter=True)
            .all()
        )
        enrollment_map = {}
        for enrollment, course_name in all_enrollments:
            if enrollment.student_id not in enrollment_map:
                enrollment_map[enrollment.student_id] = []
            enrollment_map[enrollment.student_id].append({
                'content_completed': enrollment.content_completed,
                'content_required': enrollment.content_required,
                'content_required_w1w2': enrollment.content_required_w1w2,
                'quiz_completed': enrollment.quiz_completed,
                'total_quiz_attempts': enrollment.total_quiz_attempts,
                'discussion_posts_created': enrollment.discussion_posts_created,
                'discussion_post_replies': enrollment.discussion_post_replies,
                'discussion_posts_read': enrollment.discussion_posts_read,
                'num_assignment_submissions': enrollment.num_assignment_submissions,
                'total_time_spent_seconds': enrollment.total_time_spent_seconds,
                'num_logins': enrollment.num_logins,
            })

        # Batch graded + exams for risk
        all_graded = db.query(GradedComponent).all()
        graded_map = {}
        for g in all_graded:
            if g.student_id not in graded_map:
                graded_map[g.student_id] = []
            graded_map[g.student_id].append({
                'component_type': g.component_type,
                'score': g.score,
                'max_score': g.max_score,
                'missed': g.missed,
            })

        all_exams = db.query(ExamRecord).all()
        exam_map = {}
        for e in all_exams:
            if e.student_id not in exam_map:
                exam_map[e.student_id] = []
            exam_map[e.student_id].append({
                'marks_obtained': e.marks_obtained,
                'marks_total': e.marks_total,
                'present': e.present,
            })

        for student in students:
            dept = student.parent_department_name or 'Unknown'
            if dept not in dept_stats:
                dept_stats[dept] = {'students': 0, 'risk_scores': []}

            enrollments = enrollment_map.get(student.id, [])
            graded = graded_map.get(student.id, [])
            exams = exam_map.get(student.id, [])
            features = FeatureEngineer.calculate_all_features(enrollments, graded, exams)
            risk_score = RiskScorer.calculate_risk_score(features)

            dept_stats[dept]['students'] += 1
            dept_stats[dept]['risk_scores'].append(risk_score)

        department_summary = []
        for dept, data in dept_stats.items():
            scores = data['risk_scores']
            department_summary.append({
                'department': dept,
                'student_count': data['students'],
                'avg_risk_score': round(sum(scores) / len(scores), 2) if scores else 0,
            })

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
                'course': name,
                'enrollments': count or 0,
                'avg_content_completed': round(avg_completed or 0, 2),
                'total_time_hours': round((total_time or 0) / 3600, 2),
            })

        return {
            'department_summary': department_summary,
            'course_summary': course_summary,
            'total_analyzed': len(students),
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
