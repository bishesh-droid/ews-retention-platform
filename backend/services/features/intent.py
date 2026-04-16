"""
Intent Feature Extractor
-----------------------
Extracts intent and motivation features from combined feature data.

Domain: Intent (Student Motivation & Engagement Pattern)
- Engagement pattern classification (disengaged, struggling, on_track)
- Combines academic, engagement, and consistency signals
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class IntentFeatures:
    """Typed dataclass for student intent/motivation features."""

    engagement_pattern: str  # "disengaged", "struggling", "at_risk_normal", "on_track"


class IntentFeatureExtractor:
    """
    Extracts intent features by classifying overall engagement pattern.

    Combines signals from academic, engagement, and consistency domains
    to classify the student's motivational state.
    """

    def extract(
        self,
        content_completion_score: Optional[float],
        login_consistency_score: float,
        time_investment_score: float,
        graded_quiz_score: Optional[float],
        risk_score: float,
        total_login_count: int,
        total_time_seconds: float,
    ) -> IntentFeatures:
        """
        Extract intent features by classifying engagement pattern.

        Args:
            content_completion_score: Content completion percentage [0-100]
            login_consistency_score: Login frequency score [0-100]
            time_investment_score: Time spent score [0-100]
            graded_quiz_score: Quiz performance score [0-100] or None
            risk_score: Overall risk score [0-100]
            total_login_count: Raw login count
            total_time_seconds: Raw time spent in seconds

        Returns:
            IntentFeatures dataclass with engagement pattern
        """
        pattern = self._classify_engagement_pattern(
            login_count=total_login_count,
            content_completion_rate=(content_completion_score or 0) / 100.0,
            total_time_seconds=total_time_seconds,
            graded_quiz_score=graded_quiz_score,
            risk_score=risk_score,
        )

        return IntentFeatures(engagement_pattern=pattern)

    def _classify_engagement_pattern(
        self,
        login_count: int,
        content_completion_rate: float,
        total_time_seconds: float,
        graded_quiz_score: Optional[float],
        risk_score: float,
    ) -> str:
        """
        Classify student into engagement pattern.

        Distinguishes between:
        - disengaged: Not using platform (low login, low completion)
        - struggling: Trying but not succeeding (high login, low completion, poor quiz)
        - at_risk_normal: At risk but normal pattern
        - on_track: Healthy engagement

        Returns:
            One of: "disengaged", "struggling", "at_risk_normal", "on_track"
        """
        # Rule 1: Disengaged - very low login and completion
        if login_count < 5 and content_completion_rate < 0.05:
            return "disengaged"

        # Rule 2: Struggling - high login, low completion, significant time, poor quiz
        if (
            login_count > 80
            and content_completion_rate < 0.20
            and total_time_seconds > 7200
            and (graded_quiz_score is None or graded_quiz_score < 55)
        ):
            return "struggling"

        # Rule 3: At risk but normal pattern
        if risk_score >= 40:
            return "at_risk_normal"

        # Rule 4: On track
        return "on_track"
