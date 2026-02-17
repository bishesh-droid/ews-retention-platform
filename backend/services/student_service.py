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
