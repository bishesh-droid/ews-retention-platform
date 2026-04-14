"""
Test for ConsistencyFeatureExtractor.

Comprehensive tests for:
- Engagement trend calculation (active/declining/inactive)
- Ghost student detection
- Zero progress course counting
- Timestamp parsing edge cases
"""

from datetime import datetime, timedelta
from backend.services.features.consistency import ConsistencyFeatureExtractor, ConsistencyFeatures


class TestConsistencyFeatureExtractor:
    """Tests for behavioral consistency feature extraction."""

    def test_extract_with_empty_enrollments(self):
        """Should return inactive trend for empty enrollments."""
        extractor = ConsistencyFeatureExtractor()
        result = extractor.extract([], total_login_count=0)

        assert isinstance(result, ConsistencyFeatures)
        assert result.engagement_trend == "inactive"
        assert result.is_ghost is False  # No courses = not a ghost
        assert result.total_enrolled_courses == 0

    def test_engagement_trend_active(self):
        """Should classify as 'active' with recent logins."""
        extractor = ConsistencyFeatureExtractor()
        recent_date = (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"

        enrollments = [
            {
                "content_completed": 10,
                "last_system_login": recent_date,
                "last_visited_date": recent_date,
            },
        ]
        result = extractor.extract(enrollments, total_login_count=20)

        assert result.engagement_trend == "active"

    def test_engagement_trend_declining(self):
        """Should classify as 'declining' with old but present activity."""
        extractor = ConsistencyFeatureExtractor()
        # Activity within 30 days but not within 14 days
        old_date = (datetime.utcnow() - timedelta(days=20)).isoformat() + "Z"

        enrollments = [
            {
                "content_completed": 10,
                "last_system_login": old_date,
            },
        ]
        result = extractor.extract(enrollments, total_login_count=10)

        assert result.engagement_trend == "declining"

    def test_engagement_trend_inactive(self):
        """Should classify as 'inactive' with no recent activity."""
        extractor = ConsistencyFeatureExtractor()
        # Activity more than 30 days ago
        very_old_date = (datetime.utcnow() - timedelta(days=45)).isoformat() + "Z"

        enrollments = [
            {
                "content_completed": 10,
                "last_system_login": very_old_date,
            },
        ]
        result = extractor.extract(enrollments, total_login_count=5)

        assert result.engagement_trend == "inactive"

    def test_ghost_never_logged_in(self):
        """Should detect ghost type 'never_logged_in' with zero logins."""
        extractor = ConsistencyFeatureExtractor()

        enrollments = [
            {"content_completed": 0, "total_time_spent": 0},
            {"content_completed": 0, "total_time_spent": 0},
        ]
        result = extractor.extract(enrollments, total_login_count=0)

        assert result.is_ghost is True
        assert result.ghost_type == "never_logged_in"
        assert result.total_enrolled_courses == 2

    def test_ghost_logged_in_never_started(self):
        """Should detect ghost type 'logged_in_never_started'."""
        extractor = ConsistencyFeatureExtractor()

        # Has logins but no content progress and minimal time spent
        enrollments = [
            {"content_completed": 0, "total_time_spent": 100},  # < 300 seconds
            {"content_completed": 0, "total_time_spent": 50},
        ]
        result = extractor.extract(enrollments, total_login_count=5)

        assert result.is_ghost is True
        assert result.ghost_type == "logged_in_never_started"

    def test_not_ghost_with_engagement(self):
        """Should not flag as ghost when student has meaningful engagement."""
        extractor = ConsistencyFeatureExtractor()

        # Has content completion
        enrollments = [
            {"content_completed": 5, "total_time_spent": 500},
            {"content_completed": 0, "total_time_spent": 200},
        ]
        result = extractor.extract(enrollments, total_login_count=5)

        assert result.is_ghost is False
        assert result.ghost_type is None

    def test_not_ghost_with_sufficient_time(self):
        """Should not flag as ghost when student spent significant time."""
        extractor = ConsistencyFeatureExtractor()

        # No content completion but significant time spent (> 300 seconds)
        enrollments = [
            {"content_completed": 0, "total_time_spent": 600},
        ]
        result = extractor.extract(enrollments, total_login_count=2)

        assert result.is_ghost is False
        assert result.ghost_type is None

    def test_zero_progress_counting(self):
        """Should correctly count courses with zero content completion."""
        extractor = ConsistencyFeatureExtractor()

        enrollments = [
            {"content_completed": 0, "total_time_spent": 0},
            {"content_completed": 5, "total_time_spent": 100},
            {"content_completed": 0, "total_time_spent": 0},
        ]
        result = extractor.extract(enrollments, total_login_count=10)

        assert result.zero_progress_course_count == 2
        assert result.total_enrolled_courses == 3

    def test_timestamp_parsing_edge_cases(self):
        """Should handle various timestamp formats."""
        extractor = ConsistencyFeatureExtractor()

        # Valid ISO format with Z suffix
        valid_ts = datetime.utcnow().isoformat() + "Z"
        assert extractor._parse_timestamp(valid_ts) is not None

        # Valid ISO format with timezone
        valid_ts_tz = datetime.utcnow().isoformat() + "+00:00"
        assert extractor._parse_timestamp(valid_ts_tz) is not None

        # Invalid format returns None
        assert extractor._parse_timestamp("invalid") is None
        assert extractor._parse_timestamp(None) is None
        assert extractor._parse_timestamp("") is None

    def test_total_time_seconds_calculation(self):
        """Should correctly sum total time across all enrollments."""
        extractor = ConsistencyFeatureExtractor()

        enrollments = [
            {"content_completed": 5, "total_time_spent": 3600},
            {"content_completed": 3, "total_time_spent": 1800},
        ]
        result = extractor.extract(enrollments, total_login_count=10)

        assert result.total_time_seconds == 5400  # 3600 + 1800
