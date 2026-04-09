"""
Engagement Feature Extractor
-----------------------------
Extracts LMS engagement features from enrollment data.

Domain: Engagement (LMS Activity)
- Content completion (mandatory and optional courses)
- Quiz engagement (completion + attempts)
- Discussion participation
- Time investment
- Assignment submissions
- Per-course breakdown
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
import math


@dataclass
class EngagementFeatures:
    """Typed dataclass for LMS engagement features."""
    content_completion_score: Optional[float]   # Overall content completion [0-100]
    w1w2_completion_score: float                # Week 1-2 completion [0-100]
    quiz_engagement_score: float                # Quiz activity [0-100]
    discussion_engagement_score: float          # Forum participation [0-100]
    login_consistency_score: float              # Login frequency [0-100]
    time_investment_score: float                # Time spent [0-100]
    assignment_score: float                     # Assignment submissions [0-100]
    zero_progress_ratio: float                  # Fraction of courses with 0 progress [0-1]
    progress_category: str                       # "0%", "0-10%", or ">10%"
    per_course_breakdown: List[Dict] = field(default_factory=list)
    self_directed_learning_score: float = 0.0   # Optional course engagement [0-100]


class EngagementFeatureExtractor:
    """
    Extracts engagement features from enrollment records.
    
    Takes only enrollment data slice as input.
    """

    def __init__(self, registry_lookup: Optional[Callable] = None):
        self.registry_lookup = registry_lookup

    @staticmethod
    def _to_non_negative(value: object) -> float:
        """Parse value as non-negative float."""
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
        Data-driven normalization using exponential saturation.
        Scale is inferred from student's own positive-value distribution.
        """
        clean = [max(0.0, float(v)) for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
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

    def extract(self, enrollments: List[Dict], week_number: Optional[int] = None) -> EngagementFeatures:
        """
        Extract all engagement features from enrollment data.
        
        Args:
            enrollments: List of enrollment dictionaries
            week_number: Current trimester week (affects W1/W2 calculation)
            
        Returns:
            EngagementFeatures dataclass with calculated scores
        """
        content_completion = self._calculate_content_completion_score(enrollments)
        
        # After week 2, use full-term completion to avoid misleading W1/W2-only
        if week_number is None or week_number <= 2:
            w1w2_completion = self._calculate_w1w2_completion_score(enrollments)
        else:
            w1w2_completion = content_completion if content_completion else 0.0

        return EngagementFeatures(
            content_completion_score=content_completion,
            w1w2_completion_score=w1w2_completion,
            quiz_engagement_score=self._calculate_quiz_engagement_score(enrollments),
            discussion_engagement_score=self._calculate_discussion_engagement_score(enrollments),
            login_consistency_score=self._calculate_login_consistency_score(enrollments),
            time_investment_score=self._calculate_time_investment_score(enrollments),
            assignment_score=self._calculate_assignment_score(enrollments),
            zero_progress_ratio=self._calculate_zero_progress_ratio(enrollments),
            progress_category=self._get_progress_category(enrollments),
            per_course_breakdown=self._get_per_course_breakdown(enrollments),
            self_directed_learning_score=self._calculate_self_directed_learning_score(enrollments)
        )

    def _calculate_content_completion_score(self, enrollments: List[Dict]) -> Optional[float]:
        """Calculate content completion rate across mandatory courses only."""
        mandatory = [e for e in enrollments if not e.get("is_optional", False)]
        
        total_completed = 0
        total_required = 0

        for e in mandatory:
            done = e.get('content_completed') or 0
            req = e.get('content_required') or 0

            if req == 0 and self.registry_lookup:
                req = self.registry_lookup(
                    e.get('course_offering_code'),
                    e.get('semester_name')
                ) or 0

            if req > 0:
                total_completed += done
                total_required += req

        if total_required == 0:
            return None
        return round(min(100.0, (total_completed / total_required) * 100), 2)

    def _calculate_w1w2_completion_score(self, enrollments: List[Dict]) -> float:
        """Calculate content completion rate for weeks 1 & 2 specifically."""
        total_completed = 0
        total_required = 0

        for e in enrollments:
            required_w1w2 = self._to_non_negative(e.get('content_required_w1w2', 0))
            
            # Prefer explicit W1/W2 completion field if available
            explicit = e.get("content_completed_w1w2")
            if explicit is not None:
                completed = self._to_non_negative(explicit)
            else:
                cumulative = self._to_non_negative(e.get("content_completed", 0))
                completed = min(cumulative, required_w1w2)
            
            total_completed += completed
            total_required += required_w1w2

        if total_required == 0:
            return 0.0
        return round(min(100.0, (total_completed / total_required) * 100), 2)

    def _calculate_quiz_engagement_score(self, enrollments: List[Dict]) -> float:
        """Calculate quiz engagement from completion and attempts."""
        if not enrollments:
            return 0.0

        quiz_per_course = [self._to_non_negative(e.get('quiz_completed', 0)) for e in enrollments]
        attempts_per_course = [self._to_non_negative(e.get('total_quiz_attempts', 0)) for e in enrollments]

        completion_component = self._adaptive_saturation_score(quiz_per_course, 1.0, 200.0)
        attempt_component = self._adaptive_saturation_score(attempts_per_course, 1.0, 300.0)

        return round((completion_component * 0.7) + (attempt_component * 0.3), 2)

    def _calculate_discussion_engagement_score(self, enrollments: List[Dict]) -> float:
        """Calculate discussion participation score."""
        if not enrollments:
            return 0.0

        weighted_activity = []
        for e in enrollments:
            created = self._to_non_negative(e.get('discussion_posts_created', 0))
            replies = self._to_non_negative(e.get('discussion_post_replies', 0))
            read = self._to_non_negative(e.get('discussion_posts_read', 0))
            weighted_activity.append((created * 3.0) + (replies * 2.0) + (read * 0.5))

        return self._adaptive_saturation_score(weighted_activity, 1.0, 500.0)

    def _calculate_login_consistency_score(self, enrollments: List[Dict]) -> float:
        """Calculate login consistency from login counts."""
        if not enrollments:
            return 0.0

        logins_per_course = [self._to_non_negative(e.get('num_logins', 0)) for e in enrollments]
        return self._adaptive_saturation_score(logins_per_course, 1.0, 500.0)

    def _calculate_time_investment_score(self, enrollments: List[Dict]) -> float:
        """Calculate time investment score from content time."""
        if not enrollments:
            return 0.0

        hours_per_course = [
            self._to_non_negative(e.get('total_time_spent_seconds', 0)) / 3600.0
            for e in enrollments
        ]
        return self._adaptive_saturation_score(hours_per_course, 0.5, 200.0)

    def _calculate_assignment_score(self, enrollments: List[Dict]) -> float:
        """Calculate assignment submission activity."""
        if not enrollments:
            return 0.0

        submissions_per_course = [
            self._to_non_negative(e.get('num_assignment_submissions', 0))
            for e in enrollments
        ]
        return self._adaptive_saturation_score(submissions_per_course, 1.0, 100.0)

    def _calculate_zero_progress_ratio(self, enrollments: List[Dict]) -> float:
        """Calculate fraction of courses with zero content completion."""
        if not enrollments:
            return 1.0

        zero_count = sum(
            1 for e in enrollments
            if self._to_non_negative(e.get('content_completed', 0)) <= 0.0
        )
        return round(zero_count / len(enrollments), 4)

    def _get_progress_category(self, enrollments: List[Dict]) -> str:
        """Classify student into progress bucket based on W1&2 content."""
        total_completed = 0
        total_required_w1w2 = 0

        for e in enrollments:
            required = self._to_non_negative(e.get('content_required_w1w2', 0))
            total_completed += self._w1w2_completed_for_enrollment(e)
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

    def _w1w2_completed_for_enrollment(self, e: Dict) -> float:
        """Get W1/W2 completed count for a single enrollment (leakage-safe)."""
        required_w1w2 = self._to_non_negative(e.get("content_required_w1w2", 0))
        explicit = e.get("content_completed_w1w2")
        if explicit is not None:
            completed = self._to_non_negative(explicit)
            return min(completed, required_w1w2)
        cumulative = self._to_non_negative(e.get("content_completed", 0))
        return min(cumulative, required_w1w2)

    def _get_per_course_breakdown(self, enrollments: List[Dict]) -> List[Dict]:
        """Get per-course engagement breakdown."""
        breakdown = []
        for e in enrollments:
            content_req = e.get('content_required', 0) or 0
            content_done = e.get('content_completed', 0) or 0

            if not content_req or content_req <= 0:
                pct = None
                stale_required_count = False
            else:
                raw_pct = content_done / content_req * 100
                pct = round(min(100.0, raw_pct), 2)
                stale_required_count = raw_pct > 100.0

            breakdown.append({
                "course_id": e.get('course_id'),
                "course_name": e.get('course_name', ''),
                "content_completed": content_done,
                "content_required": content_req,
                "completion_pct": pct,
                "stale_required_count": stale_required_count,
                "quiz_completed": e.get('quiz_completed', 0) or 0,
                "total_quiz_attempts": e.get('total_quiz_attempts', 0) or 0,
                "discussion_posts": e.get('discussion_posts_created', 0) or 0,
                "time_spent_hours": round((e.get('total_time_spent_seconds', 0) or 0) / 3600, 2),
                "logins": e.get('num_logins', 0) or 0,
                "assignments_submitted": e.get('num_assignment_submissions', 0) or 0,
            })
        return breakdown

    def _calculate_self_directed_learning_score(self, enrollments: List[Dict]) -> float:
        """
        Calculate self-directed learning score from optional course engagement.
        Students engaging with self-paced optional courses demonstrate
        self-directed learning motivation.
        """
        optional = [e for e in enrollments if e.get("is_optional", False)]
        if not optional:
            return 0.0

        scores = []
        for e in optional:
            req = e.get("content_required") or 0
            done = e.get("content_completed") or 0
            if req > 0:
                scores.append(min(1.0, done / req))
            elif done > 0:
                scores.append(1.0)

        if not scores:
            return 0.0

        raw = sum(scores) / len(scores)
        return min(100.0, raw * 100 * 2.5)  # Generous multiplier for intent
