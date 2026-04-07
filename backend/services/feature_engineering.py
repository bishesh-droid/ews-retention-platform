"""
Feature Engineering Service for EWS Retention Platform.

Derives engagement metrics from the Engagement_Analysis.xlsx data.
All features are calculated from Enrollment records per student.

Feature Categories:
- Content Engagement: content completion rate across courses
- Quiz Engagement: quiz completion and attempt patterns
- Discussion Engagement: posts created, replies, reads
- Login Consistency: login frequency and recency
- Time Investment: total time spent in content
"""

from typing import Dict, List, Optional
from datetime import datetime
import math


class FeatureEngineer:
    """
    Calculates engagement features from enrollment data.
    All methods work with lists of enrollment dictionaries.
    """

    @staticmethod
    def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime."""
        if not ts:
            return None
        try:
            # Handle the format: 2025-12-28T06:42:30.8300000Z
            ts_clean = ts.replace('Z', '+00:00')
            return datetime.fromisoformat(ts_clean)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_non_negative(value: object) -> float:
        """Pure helper: parse value as non-negative float."""
        try:
            v = float(value or 0)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(v):
            return 0.0
        return max(0.0, v)

    @staticmethod
    def _adaptive_saturation_score(values: List[float], min_scale: float = 1.0, max_scale: float = 1000.0) -> float:
        """
        Pure helper: data-driven normalization using exponential saturation.

        Instead of fixed divisors (e.g., /20, /100), scale is inferred from the
        student's own positive-value distribution (median of non-zero values).
        This reduces off-distribution behavior while preserving monotonicity.
        """
        clean = [FeatureEngineer._to_non_negative(v) for v in values]
        if not clean:
            return 0.0

        positives = sorted(v for v in clean if v > 0)
        if not positives:
            return 0.0

        mid = len(positives) // 2
        if len(positives) % 2 == 0:
            scale = (positives[mid - 1] + positives[mid]) / 2.0
        else:
            scale = positives[mid]
        scale = max(min_scale, min(max_scale, scale))

        avg_value = sum(clean) / len(clean)
        score = 100.0 * (1.0 - math.exp(-avg_value / scale))
        return round(max(0.0, min(100.0, score)), 2)

    @staticmethod
    def _w1w2_completed_for_enrollment(e: Dict) -> float:
        """
        Pure helper for leakage-safe W1/W2 completion numerator.

        Preference order:
        1) explicit `content_completed_w1w2` (true same-window numerator)
        2) fallback to capped cumulative completion if week-specific field absent
        """
        required_w1w2 = FeatureEngineer._to_non_negative(e.get("content_required_w1w2", 0))
        explicit = e.get("content_completed_w1w2")
        if explicit is not None:
            completed = FeatureEngineer._to_non_negative(explicit)
            return min(completed, required_w1w2)

        # Backward-compatible fallback when source data lacks W1/W2 completed field.
        cumulative = FeatureEngineer._to_non_negative(e.get("content_completed", 0))
        return min(cumulative, required_w1w2)

    @staticmethod
    def calculate_content_completion_score(enrollments: List[Dict]) -> float:
        """
        Calculate overall content completion rate across all courses.

        Data Used: content_completed, content_required per enrollment

        Returns:
            Score [0-100], where 100 = all content completed in all courses
        """
        total_completed = 0
        total_required = 0

        for e in enrollments:
            completed = FeatureEngineer._to_non_negative(e.get('content_completed', 0))
            required = FeatureEngineer._to_non_negative(e.get('content_required', 0))
            total_completed += completed
            total_required += required

        if total_required == 0:
            return 0.0

        score = (total_completed / total_required) * 100
        return round(min(100.0, score), 2)

    @staticmethod
    def calculate_w1w2_completion_score(enrollments: List[Dict]) -> float:
        """
        Calculate content completion rate for weeks 1 & 2 specifically.

        Data Used: content_completed, content_required_w1w2 per enrollment

        Returns:
            Score [0-100] for W1&2 content progress
        """
        total_completed = 0
        total_required = 0

        for e in enrollments:
            required_w1w2 = FeatureEngineer._to_non_negative(e.get('content_required_w1w2', 0))
            total_completed += FeatureEngineer._w1w2_completed_for_enrollment(e)
            total_required += required_w1w2

        if total_required == 0:
            return 0.0

        score = (total_completed / total_required) * 100
        return round(min(100.0, score), 2)

    @staticmethod
    def calculate_quiz_engagement_score(enrollments: List[Dict]) -> float:
        """
        Calculate quiz engagement from completion and attempts.

        Data Used: quiz_completed, total_quiz_attempts per enrollment

        Returns:
            Score [0-100] based on quiz activity
        """
        if not enrollments:
            return 0.0

        quiz_per_course = [FeatureEngineer._to_non_negative(e.get('quiz_completed', 0)) for e in enrollments]
        attempts_per_course = [FeatureEngineer._to_non_negative(e.get('total_quiz_attempts', 0)) for e in enrollments]

        completion_component = FeatureEngineer._adaptive_saturation_score(quiz_per_course, min_scale=1.0, max_scale=200.0)
        attempt_component = FeatureEngineer._adaptive_saturation_score(attempts_per_course, min_scale=1.0, max_scale=300.0)

        # Completion carries more signal than raw attempts.
        return round((completion_component * 0.7) + (attempt_component * 0.3), 2)

    @staticmethod
    def calculate_discussion_engagement_score(enrollments: List[Dict]) -> float:
        """
        Calculate discussion participation score.

        Data Used: discussion_posts_created, discussion_post_replies,
                   discussion_posts_read per enrollment

        Returns:
            Score [0-100] based on discussion activity
        """
        if not enrollments:
            return 0.0

        # Weighted: creating > replying > reading
        weighted_activity = []
        for e in enrollments:
            created = FeatureEngineer._to_non_negative(e.get('discussion_posts_created', 0))
            replies = FeatureEngineer._to_non_negative(e.get('discussion_post_replies', 0))
            read = FeatureEngineer._to_non_negative(e.get('discussion_posts_read', 0))
            weighted_activity.append((created * 3.0) + (replies * 2.0) + (read * 0.5))

        return FeatureEngineer._adaptive_saturation_score(weighted_activity, min_scale=1.0, max_scale=500.0)

    @staticmethod
    def calculate_login_consistency_score(enrollments: List[Dict]) -> float:
        """
        Calculate login consistency from login counts.

        Data Used: num_logins, last_system_login per enrollment

        Returns:
            Score [0-100] based on login frequency
        """
        if not enrollments:
            return 0.0

        logins_per_course = [FeatureEngineer._to_non_negative(e.get('num_logins', 0)) for e in enrollments]
        return FeatureEngineer._adaptive_saturation_score(logins_per_course, min_scale=1.0, max_scale=500.0)

    @staticmethod
    def calculate_time_investment_score(enrollments: List[Dict]) -> float:
        """
        Calculate time investment score from content time.

        Data Used: total_time_spent_seconds per enrollment

        Returns:
            Score [0-100] based on time spent in content
        """
        if not enrollments:
            return 0.0

        hours_per_course = [
            FeatureEngineer._to_non_negative(e.get('total_time_spent_seconds', 0)) / 3600.0
            for e in enrollments
        ]
        return FeatureEngineer._adaptive_saturation_score(hours_per_course, min_scale=0.5, max_scale=200.0)

    @staticmethod
    def calculate_assignment_score(enrollments: List[Dict]) -> float:
        """
        Calculate assignment submission activity.

        Data Used: num_assignment_submissions per enrollment

        Returns:
            Score [0-100] based on assignment activity
        """
        if not enrollments:
            return 0.0

        submissions_per_course = [
            FeatureEngineer._to_non_negative(e.get('num_assignment_submissions', 0))
            for e in enrollments
        ]
        return FeatureEngineer._adaptive_saturation_score(submissions_per_course, min_scale=1.0, max_scale=100.0)

    @staticmethod
    def calculate_zero_progress_ratio(enrollments: List[Dict]) -> float:
        """
        Calculate what fraction of courses have zero content completion.

        Returns:
            Ratio [0-1], where 0 = all courses have some progress, 1 = all zero
        """
        if not enrollments:
            return 1.0

        zero_count = sum(
            1 for e in enrollments
            if FeatureEngineer._to_non_negative(e.get('content_completed', 0)) <= 0.0
        )
        return round(zero_count / len(enrollments), 4)

    @staticmethod
    def get_progress_category(enrollments: List[Dict]) -> str:
        """
        Classify student into progress bucket based on W1&2 content.

        Returns:
            "0%", "0-10%", or ">10%"
        """
        total_completed = 0
        total_required_w1w2 = 0

        for e in enrollments:
            required = FeatureEngineer._to_non_negative(e.get('content_required_w1w2', 0))
            total_completed += FeatureEngineer._w1w2_completed_for_enrollment(e)
            total_required_w1w2 += required

        if total_required_w1w2 == 0:
            return "0%"

        pct = (total_completed / total_required_w1w2) * 100

        if pct == 0:
            return "0%"
        elif pct <= 10:
            return "0-10%"
        else:
            return ">10%"

    @staticmethod
    def get_engagement_trend(enrollments: List[Dict]) -> str:
        """
        Determine engagement trend by comparing login recency.

        Returns:
            "active", "declining", or "inactive"
        """
        if not enrollments:
            return "inactive"

        now = datetime.utcnow()
        recent_14 = 0
        recent_30 = 0
        any_activity = 0

        for e in enrollments:
            activity_timestamps = [
                e.get("last_system_login"),
                e.get("last_visited_date"),
                e.get("last_assignment_submission_date"),
                e.get("last_quiz_attempt_date"),
                e.get("last_discussion_post_date"),
                e.get("last_scorm_visit_date"),
                e.get("last_scorm_completion_date"),
            ]
            parsed = [FeatureEngineer._parse_timestamp(ts) for ts in activity_timestamps if ts]
            parsed = [p for p in parsed if p is not None]
            if not parsed:
                continue
            any_activity += 1
            most_recent = max(parsed)
            age_days = (now - most_recent.replace(tzinfo=None)).days
            if age_days <= 14:
                recent_14 += 1
            if age_days <= 30:
                recent_30 += 1

        if any_activity == 0:
            return "inactive"

        ratio_14 = recent_14 / len(enrollments)
        ratio_30 = recent_30 / len(enrollments)

        # Active: substantial recent activity in last two weeks.
        if ratio_14 >= 0.5:
            return "active"
        # Declining: has activity, but mostly not recent.
        if ratio_30 >= 0.25:
            return "declining"
        return "inactive"

    @staticmethod
    def get_per_course_breakdown(enrollments: List[Dict]) -> List[Dict]:
        """
        Get per-course engagement breakdown.

        Returns:
            List of per-course engagement summaries
        """
        breakdown = []
        for e in enrollments:
            content_req = e.get('content_required', 0) or 0
            content_done = e.get('content_completed', 0) or 0
            pct = round((content_done / content_req * 100), 2) if content_req > 0 else 0.0

            breakdown.append({
                "course_id": e.get('course_id'),
                "course_name": e.get('course_name', ''),
                "content_completed": content_done,
                "content_required": content_req,
                "completion_pct": pct,
                "quiz_completed": e.get('quiz_completed', 0) or 0,
                "total_quiz_attempts": e.get('total_quiz_attempts', 0) or 0,
                "discussion_posts": e.get('discussion_posts_created', 0) or 0,
                "time_spent_hours": round((e.get('total_time_spent_seconds', 0) or 0) / 3600, 2),
                "logins": e.get('num_logins', 0) or 0,
                "assignments_submitted": e.get('num_assignment_submissions', 0) or 0,
            })

        return breakdown

    @staticmethod
    def calculate_graded_quiz_score(graded_components: List[Dict]) -> float:
        """
        Calculate average graded quiz score as percentage.

        Data Used: GradedComponent records where component_type='quiz'

        Returns:
            Score [0-100], where 100 = perfect on all quizzes
        """
        quizzes = [g for g in graded_components if g.get('component_type') == 'quiz']
        if not quizzes:
            return 0.0

        scores = []
        for q in quizzes:
            max_score = q.get('max_score', 0) or 0
            if max_score <= 0:
                continue
            score = q.get('score')
            if score is None or q.get('missed', False):
                scores.append(0.0)  # Missed quiz = 0
            else:
                scores.append(min(100.0, (score / max_score) * 100))

        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 2)

    @staticmethod
    def calculate_graded_assignment_score(graded_components: List[Dict]) -> float:
        """
        Calculate average graded assignment score as percentage.

        Data Used: GradedComponent records where component_type='assignment'

        Returns:
            Score [0-100]
        """
        assignments = [g for g in graded_components if g.get('component_type') == 'assignment']
        if not assignments:
            return 0.0

        scores = []
        for a in assignments:
            max_score = a.get('max_score', 0) or 0
            if max_score <= 0:
                continue
            score = a.get('score')
            if score is None or a.get('missed', False):
                scores.append(0.0)
            else:
                scores.append(min(100.0, (score / max_score) * 100))

        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 2)

    @staticmethod
    def calculate_exam_score(exam_records: List[Dict]) -> float:
        """
        Calculate exam performance score.

        Combines marks percentage with attendance penalty.
        Absent exams count as 0 marks.

        Returns:
            Score [0-100]
        """
        if not exam_records:
            return 0.0

        scores = []
        for e in exam_records:
            total = FeatureEngineer._to_non_negative(e.get('marks_total', 0))
            present = bool(e.get('present', False))

            if not present:
                scores.append(0.0)
            elif total > 0:
                obtained = FeatureEngineer._to_non_negative(e.get('marks_obtained'))
                scores.append(min(100.0, (obtained / total) * 100))

        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 2)

    @staticmethod
    def calculate_exam_attendance_rate(exam_records: List[Dict]) -> float:
        """
        Calculate what percentage of exams the student attended.

        Returns:
            Rate [0-100]
        """
        if not exam_records:
            return 0.0

        attended = sum(1 for e in exam_records if bool(e.get('present', False)))
        return round((attended / len(exam_records)) * 100, 2)

    @staticmethod
    def calculate_all_features(enrollments: List[Dict],
                               graded_components: List[Dict] = None,
                               exam_records: List[Dict] = None) -> Dict:
        """
        Calculate all engagement features for a student.

        Args:
            enrollments: List of enrollment dictionaries for one student
            graded_components: List of graded quiz/assignment records
            exam_records: List of exam records

        Returns:
            Dictionary with all calculated features
        """
        features = {
            "content_completion_score": FeatureEngineer.calculate_content_completion_score(enrollments),
            "w1w2_completion_score": FeatureEngineer.calculate_w1w2_completion_score(enrollments),
            "quiz_engagement_score": FeatureEngineer.calculate_quiz_engagement_score(enrollments),
            "discussion_engagement_score": FeatureEngineer.calculate_discussion_engagement_score(enrollments),
            "login_consistency_score": FeatureEngineer.calculate_login_consistency_score(enrollments),
            "time_investment_score": FeatureEngineer.calculate_time_investment_score(enrollments),
            "assignment_score": FeatureEngineer.calculate_assignment_score(enrollments),
            "zero_progress_ratio": FeatureEngineer.calculate_zero_progress_ratio(enrollments),
            "progress_category": FeatureEngineer.get_progress_category(enrollments),
            "engagement_trend": FeatureEngineer.get_engagement_trend(enrollments),
            "per_course_breakdown": FeatureEngineer.get_per_course_breakdown(enrollments),
            "total_courses": len(enrollments),
        }

        if graded_components:
            features["graded_quiz_score"] = FeatureEngineer.calculate_graded_quiz_score(graded_components)
            features["graded_assignment_score"] = FeatureEngineer.calculate_graded_assignment_score(graded_components)
        else:
            features["graded_quiz_score"] = 0.0
            features["graded_assignment_score"] = 0.0

        if exam_records:
            features["exam_score"] = FeatureEngineer.calculate_exam_score(exam_records)
            features["exam_attendance_rate"] = FeatureEngineer.calculate_exam_attendance_rate(exam_records)
        else:
            features["exam_score"] = 0.0
            features["exam_attendance_rate"] = 0.0

        return features
