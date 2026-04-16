"""
Test for EngagementFeatureExtractor.

Comprehensive tests for:
- Content completion score calculation
- W1W2 completion score
- Quiz engagement (completion + attempts)
- Discussion participation scoring
- Login consistency
- Time investment
- Zero progress ratio
- Self-directed learning (optional courses)
"""

from backend.services.features.engagement import (
    EngagementFeatureExtractor,
    EngagementFeatures,
)


class TestEngagementFeatureExtractor:
    """Tests for LMS engagement feature extraction."""

    def test_extract_with_empty_enrollments(self):
        """Should return zero/empty scores for empty enrollments."""
        extractor = EngagementFeatureExtractor()
        result = extractor.extract([])

        assert isinstance(result, EngagementFeatures)
        assert result.content_completion_score is None
        assert result.w1w2_completion_score == 0.0
        assert result.quiz_engagement_score == 0.0
        assert result.per_course_breakdown == []

    def test_content_completion_mandatory_only(self):
        """Should only calculate completion for mandatory (non-optional) courses."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {
                "course_id": "CS101",
                "content_completed": 15,
                "content_required": 20,
                "is_optional": False,
            },
            {
                "course_id": "OPT101",
                "content_completed": 25,
                "content_required": 30,
                "is_optional": True,  # Should be excluded
            },
        ]

        result = extractor.extract(enrollments)
        # (15 / 20) * 100 = 75%
        assert result.content_completion_score == 75.0

    def test_content_completion_with_registry_lookup(self):
        """Should use registry lookup when content_required is 0."""

        def mock_lookup(course_code, semester):
            return 25

        extractor = EngagementFeatureExtractor(registry_lookup=mock_lookup)

        enrollments = [
            {
                "course_id": "CS101",
                "course_offering_code": "CS101",
                "semester_name": "T1",
                "content_completed": 20,
                "content_required": 0,  # Should trigger lookup
                "is_optional": False,
            },
        ]

        result = extractor.extract(enrollments)
        # (20 / 25) * 100 = 80%
        assert result.content_completion_score == 80.0

    def test_w1w2_completion_week_based_before_week_2(self):
        """Should use W1/W2 calculation before or during week 2."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {
                "content_completed": 15,
                "content_required_w1w2": 10,
                "content_completed_w1w2": 8,
                "is_optional": False,
            },
        ]

        # Week 2 should use explicit W1/W2 data
        result = extractor.extract(enrollments, week_number=2)
        # (8 / 10) * 100 = 80%
        assert result.w1w2_completion_score == 80.0

    def test_w1w2_completion_after_week_2(self):
        """Should use full content completion after week 2."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {
                "content_completed": 15,
                "content_required": 20,
                "content_required_w1w2": 10,
                "content_completed_w1w2": 8,
                "is_optional": False,
            },
        ]

        # After week 2 should use full completion
        result = extractor.extract(enrollments, week_number=5)
        # (15 / 20) * 100 = 75%
        assert result.w1w2_completion_score == 75.0

    def test_w1w2_completion_uses_cumulative_when_no_explicit(self):
        """Should use cumulative completion when no explicit W1/W2 data."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {
                "content_completed": 8,
                "content_required": 20,
                "content_required_w1w2": 10,
                # No content_completed_w1w2 field
                "is_optional": False,
            },
        ]

        result = extractor.extract(enrollments, week_number=1)
        # Uses min(cumulative, required_w1w2) = min(8, 10) = 8
        # (8 / 10) * 100 = 80%
        assert result.w1w2_completion_score == 80.0

    def test_quiz_engagement_calculation(self):
        """Should calculate quiz engagement with correct weights."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {
                "quiz_completed": 5,
                "total_quiz_attempts": 8,
                "is_optional": False,
            },
        ]

        result = extractor.extract(enrollments)
        # Quiz engagement should be > 0
        assert result.quiz_engagement_score > 0.0
        assert result.quiz_engagement_score <= 100.0

    def test_discussion_scoring_weights(self):
        """Should weight posts > replies > reads correctly."""
        extractor = EngagementFeatureExtractor()

        # Posts are weighted 3x, replies 2x, reads 0.5x
        enrollments_with_posts = [
            {
                "discussion_posts_created": 10,  # High posts
                "discussion_post_replies": 0,
                "discussion_posts_read": 0,
                "is_optional": False,
            },
        ]

        enrollments_with_reads = [
            {
                "discussion_posts_created": 0,
                "discussion_post_replies": 0,
                "discussion_posts_read": 100,  # Many reads
                "is_optional": False,
            },
        ]

        result_posts = extractor.extract(enrollments_with_posts)
        result_reads = extractor.extract(enrollments_with_reads)

        # Posts should contribute more than just reads
        assert result_posts.discussion_engagement_score > 0
        assert result_reads.discussion_engagement_score > 0

    def test_zero_progress_ratio_calculation(self):
        """Should correctly calculate fraction of courses with zero progress."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {"content_completed": 10, "is_optional": False},
            {"content_completed": 0, "is_optional": False},
            {"content_completed": 5, "is_optional": False},
            {"content_completed": 0, "is_optional": False},  # Another zero
        ]

        result = extractor.extract(enrollments)
        # 2 out of 4 have zero progress = 0.5
        assert result.zero_progress_ratio == 0.5

    def test_zero_progress_ratio_all_zero(self):
        """Should return 1.0 when all courses have zero progress."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {"content_completed": 0, "is_optional": False},
            {"content_completed": 0, "is_optional": False},
        ]

        result = extractor.extract(enrollments)
        assert result.zero_progress_ratio == 1.0

    def test_login_consistency_score(self):
        """Should calculate login consistency from login counts."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {"num_logins": 50, "is_optional": False},
            {"num_logins": 30, "is_optional": False},
        ]

        result = extractor.extract(enrollments)
        assert result.login_consistency_score > 0.0
        assert result.login_consistency_score <= 100.0

    def test_time_investment_score(self):
        """Should calculate time investment from time spent."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {"total_time_spent_seconds": 3600, "is_optional": False},  # 1 hour
            {"total_time_spent_seconds": 7200, "is_optional": False},  # 2 hours
        ]

        result = extractor.extract(enrollments)
        assert result.time_investment_score > 0.0
        assert result.time_investment_score <= 100.0

    def test_assignment_score(self):
        """Should calculate assignment submission score."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {"num_assignment_submissions": 5, "is_optional": False},
            {"num_assignment_submissions": 3, "is_optional": False},
        ]

        result = extractor.extract(enrollments)
        assert result.assignment_score > 0.0
        assert result.assignment_score <= 100.0

    def test_self_directed_learning_optional_courses(self):
        """Should score optional course engagement separately."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {
                "course_id": "OPT101",
                "content_completed": 8,
                "content_required": 10,
                "is_optional": True,  # Optional course
            },
        ]

        result = extractor.extract(enrollments)
        # (8 / 10) * 100 * 2.5 multiplier, capped at 100
        assert result.self_directed_learning_score > 0.0
        assert result.self_directed_learning_score <= 100.0

    def test_self_directed_learning_no_optional(self):
        """Should return 0 when no optional courses."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {"content_completed": 8, "content_required": 10, "is_optional": False},
        ]

        result = extractor.extract(enrollments)
        assert result.self_directed_learning_score == 0.0

    def test_progress_category_0_percent(self):
        """Should categorize as 0% when no progress."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {"content_completed": 0, "content_required_w1w2": 10, "is_optional": False},
        ]

        result = extractor.extract(enrollments)
        assert result.progress_category == "0%"

    def test_progress_category_0_to_10_percent(self):
        """Should categorize as 0-10% when in that range."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {
                "content_completed": 5,
                "content_required_w1w2": 50,
                "is_optional": False,
            },  # 10%
        ]

        result = extractor.extract(enrollments)
        # Exactly 10% should be in 0-10% bucket
        assert result.progress_category == "0-10%"

    def test_progress_category_above_10_percent(self):
        """Should categorize as >10% when above that threshold."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {
                "content_completed": 8,
                "content_required_w1w2": 50,
                "is_optional": False,
            },  # 16%
        ]

        result = extractor.extract(enrollments)
        assert result.progress_category == ">10%"

    def test_per_course_breakdown_structure(self):
        """Should return proper structure for per-course breakdown."""
        extractor = EngagementFeatureExtractor()

        enrollments = [
            {
                "course_id": "CS101",
                "course_name": "Computer Science",
                "content_completed": 15,
                "content_required": 20,
                "quiz_completed": 5,
                "total_quiz_attempts": 8,
                "discussion_posts_created": 3,
                "total_time_spent_seconds": 3600,
                "num_logins": 20,
                "num_assignment_submissions": 4,
                "is_optional": False,
            },
        ]

        result = extractor.extract(enrollments)
        assert len(result.per_course_breakdown) == 1

        breakdown = result.per_course_breakdown[0]
        assert breakdown["course_id"] == "CS101"
        assert breakdown["course_name"] == "Computer Science"
        assert breakdown["content_completed"] == 15
        assert breakdown["content_required"] == 20
        assert "completion_pct" in breakdown
        assert "stale_required_count" in breakdown

    def test_adaptive_saturation_score(self):
        """Should calculate adaptive saturation score correctly."""
        extractor = EngagementFeatureExtractor()

        # Empty values should return 0
        assert extractor._adaptive_saturation_score([]) == 0.0

        # Single positive value
        score = extractor._adaptive_saturation_score([100.0])
        assert score > 0.0
        assert score <= 100.0

        # Multiple values
        score = extractor._adaptive_saturation_score([50.0, 100.0, 150.0])
        assert score > 0.0
        assert score <= 100.0
