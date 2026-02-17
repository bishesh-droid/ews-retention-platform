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
            completed = e.get('content_completed', 0) or 0
            required = e.get('content_required', 0) or 0
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
            completed = e.get('content_completed', 0) or 0
            required_w1w2 = e.get('content_required_w1w2', 0) or 0
            # Completed capped at w1w2 required
            capped = min(completed, required_w1w2)
            total_completed += capped
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
        total_quizzes = sum(e.get('quiz_completed', 0) or 0 for e in enrollments)
        total_attempts = sum(e.get('total_quiz_attempts', 0) or 0 for e in enrollments)

        if not enrollments:
            return 0.0

        # Average quizzes per course
        avg_quizzes = total_quizzes / len(enrollments)

        # Normalize: assume ~20 quizzes per course is excellent
        quiz_score = min(100.0, (avg_quizzes / 20.0) * 100)

        # Bonus for attempt-to-completion ratio (shows persistence)
        if total_quizzes > 0 and total_attempts > total_quizzes:
            persistence_bonus = min(10.0, ((total_attempts / total_quizzes) - 1) * 5)
            quiz_score = min(100.0, quiz_score + persistence_bonus)

        return round(quiz_score, 2)

    @staticmethod
    def calculate_discussion_engagement_score(enrollments: List[Dict]) -> float:
        """
        Calculate discussion participation score.

        Data Used: discussion_posts_created, discussion_post_replies,
                   discussion_posts_read per enrollment

        Returns:
            Score [0-100] based on discussion activity
        """
        total_created = sum(e.get('discussion_posts_created', 0) or 0 for e in enrollments)
        total_replies = sum(e.get('discussion_post_replies', 0) or 0 for e in enrollments)
        total_read = sum(e.get('discussion_posts_read', 0) or 0 for e in enrollments)

        if not enrollments:
            return 0.0

        # Weighted: creating > replying > reading
        weighted_activity = (total_created * 3) + (total_replies * 2) + (total_read * 0.5)

        # Normalize per course: assume 30 weighted activity points per course is good
        avg_per_course = weighted_activity / len(enrollments)
        score = min(100.0, (avg_per_course / 30.0) * 100)

        return round(score, 2)

    @staticmethod
    def calculate_login_consistency_score(enrollments: List[Dict]) -> float:
        """
        Calculate login consistency from login counts.

        Data Used: num_logins, last_system_login per enrollment

        Returns:
            Score [0-100] based on login frequency
        """
        total_logins = sum(e.get('num_logins', 0) or 0 for e in enrollments)

        if not enrollments:
            return 0.0

        # Average logins per course
        avg_logins = total_logins / len(enrollments)

        # Normalize: assume 100 logins per course is very active
        score = min(100.0, (avg_logins / 100.0) * 100)

        return round(score, 2)

    @staticmethod
    def calculate_time_investment_score(enrollments: List[Dict]) -> float:
        """
        Calculate time investment score from content time.

        Data Used: total_time_spent_seconds per enrollment

        Returns:
            Score [0-100] based on time spent in content
        """
        total_seconds = sum(e.get('total_time_spent_seconds', 0) or 0 for e in enrollments)

        if not enrollments:
            return 0.0

        # Average hours per course
        avg_hours = (total_seconds / 3600) / len(enrollments)

        # Normalize: assume 20 hours per course is good engagement
        score = min(100.0, (avg_hours / 20.0) * 100)

        return round(score, 2)

    @staticmethod
    def calculate_assignment_score(enrollments: List[Dict]) -> float:
        """
        Calculate assignment submission activity.

        Data Used: num_assignment_submissions per enrollment

        Returns:
            Score [0-100] based on assignment activity
        """
        total_submissions = sum(e.get('num_assignment_submissions', 0) or 0 for e in enrollments)

        if not enrollments:
            return 0.0

        avg_submissions = total_submissions / len(enrollments)

        # Normalize: assume 5 submissions per course is good
        score = min(100.0, (avg_submissions / 5.0) * 100)

        return round(score, 2)

    @staticmethod
    def calculate_zero_progress_ratio(enrollments: List[Dict]) -> float:
        """
        Calculate what fraction of courses have zero content completion.

        Returns:
            Ratio [0-1], where 0 = all courses have some progress, 1 = all zero
        """
        if not enrollments:
            return 1.0

        zero_count = sum(1 for e in enrollments if (e.get('content_completed', 0) or 0) == 0)
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
            completed = e.get('content_completed', 0) or 0
            required = e.get('content_required_w1w2', 0) or 0
            total_completed += min(completed, required)
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

        total_logins = sum(e.get('num_logins', 0) or 0 for e in enrollments)
        total_completed = sum(e.get('content_completed', 0) or 0 for e in enrollments)

        if total_logins == 0 and total_completed == 0:
            return "inactive"
        elif total_logins < 10 or total_completed < 5:
            return "declining"
        else:
            return "active"

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
            total = e.get('marks_total', 0) or 0
            present = e.get('present', True)

            if not present:
                scores.append(0.0)
            elif total > 0:
                obtained = e.get('marks_obtained') or 0
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

        attended = sum(1 for e in exam_records if e.get('present', True))
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
