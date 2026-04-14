"""
Test for AcademicFeatureExtractor.

Comprehensive tests for:
- Graded quiz score calculation
- Assignment score calculation
- Exam score calculation
- Exam attendance rate calculation
- Academic flags extraction (UFM, deferred, etc.)
"""

from backend.services.features.academic import AcademicFeatureExtractor, AcademicFeatures


class TestAcademicFeatureExtractor:
    """Tests for academic performance feature extraction."""

    def test_extract_with_empty_data(self):
        """Should return None scores for empty input data."""
        extractor = AcademicFeatureExtractor()
        result = extractor.extract([], [])

        assert isinstance(result, AcademicFeatures)
        assert result.graded_quiz_score is None
        assert result.graded_assignment_score is None
        assert result.exam_score is None
        assert result.exam_attendance_rate is None

    def test_extract_graded_quiz_score(self):
        """Should calculate average quiz score correctly."""
        extractor = AcademicFeatureExtractor()
        graded_components = [
            {"component_type": "quiz", "score": 80, "max_score": 100, "missed": False},
            {"component_type": "quiz", "score": 90, "max_score": 100, "missed": False},
        ]
        result = extractor.extract(graded_components, [])

        assert result.graded_quiz_score == 85.0  # (80 + 90) / 2

    def test_extract_graded_quiz_score_with_missed(self):
        """Should count missed quizzes as 0."""
        extractor = AcademicFeatureExtractor()
        graded_components = [
            {"component_type": "quiz", "score": 80, "max_score": 100, "missed": False},
            {"component_type": "quiz", "score": 90, "max_score": 100, "missed": True},  # Missed = 0
        ]
        result = extractor.extract(graded_components, [])

        assert result.graded_quiz_score == 40.0  # (80 + 0) / 2

    def test_extract_graded_quiz_score_with_none_score(self):
        """Should count None score as 0."""
        extractor = AcademicFeatureExtractor()
        graded_components = [
            {"component_type": "quiz", "score": 100, "max_score": 100, "missed": False},
            {"component_type": "quiz", "score": None, "max_score": 100, "missed": False},  # None = 0
        ]
        result = extractor.extract(graded_components, [])

        assert result.graded_quiz_score == 50.0  # (100 + 0) / 2

    def test_extract_assignment_score(self):
        """Should calculate average assignment score correctly."""
        extractor = AcademicFeatureExtractor()
        graded_components = [
            {"component_type": "assignment", "score": 75, "max_score": 100, "missed": False},
            {"component_type": "assignment", "score": 85, "max_score": 100, "missed": False},
        ]
        result = extractor.extract(graded_components, [])

        assert result.graded_assignment_score == 80.0  # (75 + 85) / 2

    def test_extract_exam_score_with_attendance(self):
        """Should factor in exam attendance for score calculation."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": True, "marks_obtained": 80, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": None},
            {"present": False, "marks_obtained": 0, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": "health_support"},
        ]
        result = extractor.extract([], exam_records)

        # (80 + 0) / 2 = 40.0
        assert result.exam_score == 40.0

    def test_extract_exam_attendance_rate(self):
        """Should calculate exam attendance rate correctly."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": True, "marks_obtained": 80, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": None},
            {"present": True, "marks_obtained": 90, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": None},
            {"present": False, "marks_obtained": 0, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": "health_support"},
        ]
        result = extractor.extract([], exam_records)

        # 2 out of 3 attended = 66.67%
        assert result.exam_attendance_rate == 66.67

    def test_academic_flags_ufm_detection(self):
        """Should detect UFM (unfair means) flags in exam records."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": True, "marks_obtained": 0, "marks_total": 100, "ufm_flagged": True, "defaulter_reason": None},
        ]
        result = extractor.extract([], exam_records)

        assert result.academic_flags["ufm_flagged"] is True

    def test_academic_flags_no_ufm(self):
        """Should not flag UFM when not present."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": True, "marks_obtained": 80, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": None},
        ]
        result = extractor.extract([], exam_records)

        assert result.academic_flags["ufm_flagged"] is False

    def test_academic_flags_deferred(self):
        """Should detect deferred status from exam records."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": False, "marks_obtained": 0, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": "deferred"},
        ]
        result = extractor.extract([], exam_records)

        assert result.academic_flags["deferred"] is True

    def test_academic_flags_dropout_intent(self):
        """Should detect dropout intent from exam records."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": False, "marks_obtained": 0, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": "dropout_intent"},
        ]
        result = extractor.extract([], exam_records)

        assert result.academic_flags["dropout_intent"] is True

    def test_academic_flags_health_support(self):
        """Should detect health support needed from exam records."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": False, "marks_obtained": 0, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": "health_support"},
        ]
        result = extractor.extract([], exam_records)

        assert result.academic_flags["health_support_needed"] is True

    def test_all_academic_flags(self):
        """Should correctly set all academic flags from multiple records."""
        extractor = AcademicFeatureExtractor()
        exam_records = [
            {"present": True, "marks_obtained": 80, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": None},
            {"present": False, "marks_obtained": 0, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": "deferred"},
            {"present": False, "marks_obtained": 0, "marks_total": 100, "ufm_flagged": False, "defaulter_reason": "unknown_high_risk"},
        ]
        result = extractor.extract([], exam_records)

        assert result.academic_flags["ufm_flagged"] is False
        assert result.academic_flags["deferred"] is True
        assert result.academic_flags["unknown_defaulter"] is True
