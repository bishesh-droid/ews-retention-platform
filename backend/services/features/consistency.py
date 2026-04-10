"""
Consistency Feature Extractor
------------------------------
Extracts behavioral consistency features from enrollment data.

Domain: Consistency (Behavioral Patterns)
- Login recency and patterns
- Zero progress detection
- Ghost student detection
- Engagement trends over time
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class ConsistencyFeatures:
    """Typed dataclass for behavioral consistency features."""
    engagement_trend: str                      # "active", "declining", "inactive"
    is_ghost: bool                             # True if ghost student detected
    ghost_type: Optional[str]                   # "never_logged_in" or "logged_in_never_started"
    zero_progress_course_count: int            # Number of courses with 0 progress
    total_enrolled_courses: int                # Total number of enrolled courses
    total_time_seconds: float                  # Total time spent across all courses


class ConsistencyFeatureExtractor:
    """
    Extracts behavioral consistency features from enrollment records.

    Analyzes login patterns, progress consistency, and ghost student detection.
    """

    @staticmethod
    def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp string to datetime."""
        if not ts:
            return None
        try:
            ts_clean = ts.replace('Z', '+00:00')
            return datetime.fromisoformat(ts_clean)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_non_negative(value: object) -> float:
        """Parse value as non-negative float."""
        try:
            v = float(value or 0)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0
        import math
        if not math.isfinite(v):
            return 0.0
        return max(0.0, v)

    def extract(self, enrollments: List[Dict], total_login_count: int) -> ConsistencyFeatures:
        """
        Extract all consistency features from enrollment data.

        Args:
            enrollments: List of enrollment dictionaries
            total_login_count: Total logins across all courses for the student

        Returns:
            ConsistencyFeatures dataclass with calculated features
        """
        ghost_info = self._detect_ghost_student(enrollments, total_login_count)

        return ConsistencyFeatures(
            engagement_trend=self._get_engagement_trend(enrollments),
            is_ghost=ghost_info["is_ghost"],
            ghost_type=ghost_info["ghost_type"],
            zero_progress_course_count=ghost_info["zero_progress_course_count"],
            total_enrolled_courses=ghost_info["total_enrolled_courses"],
            total_time_seconds=ghost_info["total_time_seconds"]
        )

    def _get_engagement_trend(self, enrollments: List[Dict]) -> str:
        """
        Determine engagement trend by comparing login recency.

        Returns:
            "active" - substantial recent activity (last 2 weeks)
            "declining" - has activity but mostly not recent
            "inactive" - no meaningful recent activity
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
            parsed_raw = [self._parse_timestamp(ts) for ts in activity_timestamps if ts]
            parsed: List[datetime] = [p for p in parsed_raw if p is not None]
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

        # Active: substantial recent activity in last two weeks
        if ratio_14 >= 0.5:
            return "active"
        # Declining: has activity, but mostly not recent
        if ratio_30 >= 0.25:
            return "declining"
        return "inactive"

    def _detect_ghost_student(self, enrollments: List[Dict], student_login_count: int) -> Dict:
        """
        Detect "ghost" students with zero meaningful engagement.

        Ghost types:
        - never_logged_in: Zero logins to the LMS
        - logged_in_never_started: Has logged in but never accessed content

        Args:
            enrollments: List of enrollment dictionaries
            student_login_count: Total number of logins across all courses

        Returns:
            Dictionary with ghost detection results
        """
        total_courses = len(enrollments)
        zero_progress_courses = sum(
            1 for e in enrollments if (e.get("content_completed") or 0) == 0
        )
        total_time = sum(e.get("total_time_spent", 0) or 0 for e in enrollments)

        if total_courses == 0:
            return {
                "is_ghost": False,
                "ghost_type": None,
                "zero_progress_course_count": 0,
                "total_enrolled_courses": 0,
                "total_time_seconds": 0
            }

        all_zero_progress = zero_progress_courses == total_courses

        if student_login_count == 0:
            ghost_type = "never_logged_in"
            is_ghost = True
        elif all_zero_progress and total_time < 300:
            ghost_type = "logged_in_never_started"
            is_ghost = True
        else:
            ghost_type = None
            is_ghost = False

        return {
            "is_ghost": is_ghost,
            "ghost_type": ghost_type,
            "zero_progress_course_count": zero_progress_courses,
            "total_enrolled_courses": total_courses,
            "total_time_seconds": total_time,
        }
