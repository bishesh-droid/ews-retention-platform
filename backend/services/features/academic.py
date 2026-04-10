"""
Academic Feature Extractor
---------------------------
Extracts academic performance features from graded components and exam records.

Domain: Academic Performance
- Graded quiz scores
- Assignment scores
- Exam performance and attendance
- Academic flags (UFM, deferred, etc.)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import math


@dataclass
class AcademicFeatures:
    """Typed dataclass for academic performance features."""
    graded_quiz_score: Optional[float]       # Average graded quiz score [0-100]
    graded_assignment_score: Optional[float]  # Average assignment score [0-100]
    exam_score: Optional[float]             # Average exam marks [0-100]
    exam_attendance_rate: Optional[float]   # Exam attendance percentage [0-100]
    academic_flags: Dict[str, bool]         # Flags: ufm_flagged, deferred, etc.


class AcademicFeatureExtractor:
    """
    Extracts academic performance features from graded components and exams.

    Takes only relevant data slices:
    - graded_components: List of quiz/assignment grade records
    - exam_records: List of exam attendance and marks records
    """

    @staticmethod
    def _to_non_negative(value: object) -> float:
        """Parse value as non-negative float."""
        try:
            v = float(value or 0)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(v):
            return 0.0
        return max(0.0, v)

    def extract(self, graded_components: List[Dict], exam_records: List[Dict]) -> AcademicFeatures:
        """
        Extract all academic features from graded components and exam records.

        Args:
            graded_components: List of graded quiz/assignment records
            exam_records: List of exam records with marks and attendance

        Returns:
            AcademicFeatures dataclass with calculated scores
        """
        return AcademicFeatures(
            graded_quiz_score=self._calculate_graded_quiz_score(graded_components),
            graded_assignment_score=self._calculate_graded_assignment_score(graded_components),
            exam_score=self._calculate_exam_score(exam_records),
            exam_attendance_rate=self._calculate_exam_attendance_rate(exam_records),
            academic_flags=self._calculate_academic_flags(exam_records)
        )

    def _calculate_graded_quiz_score(self, graded_components: List[Dict]) -> Optional[float]:
        """Calculate average graded quiz score as percentage."""
        if not graded_components:
            return None

        quizzes = [g for g in graded_components if g.get('component_type') == 'quiz']
        if not quizzes:
            return None

        scores = []
        for q in quizzes:
            max_score = q.get('max_score', 0) or 0
            if max_score <= 0:
                continue
            score = q.get('score')
            if score is None or q.get('missed', False):
                scores.append(0.0)
            else:
                scores.append(min(100.0, (score / max_score) * 100))

        if not scores:
            return None
        return round(sum(scores) / len(scores), 2)

    def _calculate_graded_assignment_score(self, graded_components: List[Dict]) -> Optional[float]:
        """Calculate average graded assignment score as percentage."""
        if not graded_components:
            return None

        assignments = [g for g in graded_components if g.get('component_type') == 'assignment']
        if not assignments:
            return None

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
            return None
        return round(sum(scores) / len(scores), 2)

    def _calculate_exam_score(self, exam_records: List[Dict]) -> Optional[float]:
        """Calculate exam performance score combining marks with attendance penalty."""
        if not exam_records:
            return None

        scores = []
        for e in exam_records:
            total = self._to_non_negative(e.get('marks_total', 0))
            present = bool(e.get('present', False))

            if not present:
                scores.append(0.0)
            elif total > 0:
                obtained = self._to_non_negative(e.get('marks_obtained'))
                scores.append(min(100.0, (obtained / total) * 100))

        if not scores:
            return None
        return round(sum(scores) / len(scores), 2)

    def _calculate_exam_attendance_rate(self, exam_records: List[Dict]) -> Optional[float]:
        """Calculate percentage of exams the student attended."""
        if not exam_records:
            return None

        attended = sum(1 for e in exam_records if bool(e.get('present', False)))
        return round((attended / len(exam_records)) * 100, 2)

    def _calculate_academic_flags(self, exam_records: List[Dict]) -> Dict[str, bool]:
        """
        Extract high-signal academic flags from exam records.

        Flags:
        - ufm_flagged: Unfair Means detected
        - deferred: Student deferred to next trimester
        - dropout_intent: Strong dropout signal
        - not_activated: Never activated account
        - health_support_needed: Health-related absence
        - unknown_defaulter: No reason given for absence
        """
        ufm = any(r.get("ufm_flagged") for r in exam_records)
        reasons = [r.get("defaulter_reason") for r in exam_records if r.get("defaulter_reason")]

        return {
            "ufm_flagged": ufm,
            "deferred": any(r == "deferred" for r in reasons),
            "dropout_intent": any(r == "dropout_intent" for r in reasons),
            "not_activated": any(r == "not_activated" for r in reasons),
            "health_support_needed": any(r == "health_support" for r in reasons),
            "unknown_defaulter": any(r == "unknown_high_risk" for r in reasons),
        }
