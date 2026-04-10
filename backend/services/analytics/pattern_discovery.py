"""
Pattern Discovery Service
--------------------------
Identifies institutional insights, systemic issues, and blind spots
that humans wouldn't query manually.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from backend.database import Student
import statistics


class PatternDiscoveryEngine:
    """Discovers system-wide patterns and anomalies."""

    def __init__(self, db: Session):
        self.db = db

    def discover_systemic_issues(self) -> List[Dict[str, Any]]:
        """
        Identify systemic institutional issues affecting retention.

        Returns:
            List of discovered patterns with evidence
        """
        students = self.db.query(Student).all()
        students_with_predictions = [s for s in students if s.predictions]

        if len(students_with_predictions) < 10:
            return [{
                "type": "insufficient_data",
                "title": "Need more student data",
                "description": "At least 10 students required for pattern detection",
                "confidence": "low"
            }]

        patterns = []

        # Pattern 1: Attendance policy impact
        attendance_pattern = self._analyze_attendance_impact(students_with_predictions)
        if attendance_pattern:
            patterns.append(attendance_pattern)

        # Pattern 2: GPA trend correlation
        gpa_pattern = self._analyze_gpa_patterns(students_with_predictions)
        if gpa_pattern:
            patterns.append(gpa_pattern)

        # Pattern 3: Intervention gaps
        intervention_pattern = self._analyze_intervention_gaps(students, students_with_predictions)
        if intervention_pattern:
            patterns.append(intervention_pattern)

        # Pattern 4: High-risk clustering
        clustering_pattern = self._analyze_risk_clustering(students_with_predictions)
        if clustering_pattern:
            patterns.append(clustering_pattern)

        return patterns

    def _analyze_attendance_impact(self, students: List[Student]) -> Optional[Dict]:
        """Analyze if attendance has disproportionate impact on risk."""
        attendance_risk_correlation = []

        for student in students:
            absrate7 = getattr(student, 'absrate7', None)
            if absrate7 is not None and student.predictions:
                # Convert absence rate to attendance
                attendance = (1 - absrate7) * 100  # type: ignore[attr-defined]
                risk = student.predictions[0].risk_score
                attendance_risk_correlation.append((attendance, risk))

        if len(attendance_risk_correlation) < 5:
            return None

        # Calculate correlation
        low_attendance_students = [r for a, r in attendance_risk_correlation if a < 75]
        high_attendance_students = [r for a, r in attendance_risk_correlation if a >= 90]

        if low_attendance_students and high_attendance_students:
            avg_low = statistics.mean(low_attendance_students)
            avg_high = statistics.mean(high_attendance_students)
            risk_diff = avg_low - avg_high

            if risk_diff > 20:  # Significant difference
                return {
                    "type": "attendance_policy_impact",
                    "title": "Attendance Strongly Correlates with Risk",
                    "description": (
                        f"Students with <75% attendance have {risk_diff:.0f} points higher risk on average. "
                        f"This suggests attendance policy may be a critical retention lever."
                    ),
                    "evidence": {
                        "low_attendance_avg_risk": round(avg_low, 1),
                        "high_attendance_avg_risk": round(avg_high, 1),
                        "risk_difference": round(risk_diff, 1),
                        "sample_size": len(attendance_risk_correlation)
                    },
                    "confidence": "high" if len(attendance_risk_correlation) > 20 else "medium",
                    "suggested_action": (
                        "Consider flexible attendance policies or early intervention "
                        "for students below 75% attendance."
                    ),
                }

        return None

    def _analyze_gpa_patterns(self, students: List[Student]) -> Optional[Dict]:
        """Analyze GPA improvement/decline patterns."""
        gpa_trends = []

        for student in students:
            # Compare Q1 to Q4 of most recent quarter
            q1mpa7 = getattr(student, 'q1mpa7', None)
            q4mpa7 = getattr(student, 'q4mpa7', None)
            if q1mpa7 is not None and q4mpa7 is not None:
                improvement = q4mpa7 - q1mpa7  # type: ignore[attr-defined]
                risk = student.predictions[0].risk_score if student.predictions else None
                if risk is not None:
                    gpa_trends.append((improvement, risk))

        if len(gpa_trends) < 5:
            return None

        # Find students who improved significantly
        improved_students = [(imp, risk) for imp, risk in gpa_trends if imp > 0.5]
        declined_students = [(imp, risk) for imp, risk in gpa_trends if imp < -0.5]

        if improved_students and declined_students:
            avg_risk_improved = statistics.mean([r for _, r in improved_students])
            avg_risk_declined = statistics.mean([r for _, r in declined_students])

            if avg_risk_declined - avg_risk_improved > 15:
                return {
                    "type": "gpa_trend_impact",
                    "title": "GPA Trends Predict Risk Better Than Absolute GPA",
                    "description": (
                        f"Students with declining GPA (Q1→Q4) have "
                        f"{avg_risk_declined - avg_risk_improved:.0f} points higher risk than improving students, "
                        f"regardless of starting GPA."
                    ),
                    "evidence": {
                        "improved_students_avg_risk": round(avg_risk_improved, 1),
                        "declined_students_avg_risk": round(avg_risk_declined, 1),
                        "improved_count": len(improved_students),
                        "declined_count": len(declined_students)
                    },
                    "confidence": "medium",
                    "suggested_action": (
                        "Monitor GPA trends (not just absolute values) and "
                        "intervene on declining students early."
                    ),
                }

        return None

    def _analyze_intervention_gaps(self, all_students: List[Student], at_risk_students: List[Student]) -> Optional[Dict]:
        """Identify students who need interventions but haven't received any."""
        high_risk_students = [s for s in at_risk_students if s.predictions and s.predictions[0].risk_score > 70]

        if not high_risk_students:
            return None

        students_without_interventions = [s for s in high_risk_students if not s.interventions]
        gap_percentage = (len(students_without_interventions) / len(high_risk_students)) * 100

        if gap_percentage > 30:
            return {
                "type": "intervention_gap",
                "title": "High-Risk Students Not Receiving Interventions",
                "description": (
                    f"{gap_percentage:.0f}% of high-risk students (70%+ risk) have received zero interventions. "
                    f"This represents a coverage gap."
                ),
                "evidence": {
                    "high_risk_count": len(high_risk_students),
                    "without_intervention_count": len(students_without_interventions),
                    "gap_percentage": round(gap_percentage, 1)
                },
                "confidence": "high",
                "suggested_action": (
                    f"Prioritize outreach to {len(students_without_interventions)} high-risk students "
                    f"with no intervention history."
                ),
            }

        return None

    def _analyze_risk_clustering(self, students: List[Student]) -> Optional[Dict]:
        """Check if risk is concentrated in specific segments."""
        risk_scores = [s.predictions[0].risk_score for s in students if s.predictions]

        if len(risk_scores) < 10:
            return None

        critical_risk = len([r for r in risk_scores if r > 80])
        total_students = len(risk_scores)
        critical_pct = (critical_risk / total_students) * 100

        if critical_pct > 15:  # More than 15% in critical zone
            return {
                "type": "risk_clustering",
                "title": "High Concentration of Critical-Risk Students",
                "description": (
                    f"{critical_pct:.0f}% of students are in critical risk zone (>80%). "
                    f"This suggests systemic challenges beyond individual issues."
                ),
                "evidence": {
                    "critical_risk_count": critical_risk,
                    "total_students": total_students,
                    "percentage": round(critical_pct, 1),
                    "average_risk": round(statistics.mean(risk_scores), 1)
                },
                "confidence": "high",
                "suggested_action": (
                    "Investigate institution-wide factors (curriculum difficulty, "
                    "support resources, scheduling) affecting large cohorts."
                ),
            }

        return None

    def detect_blind_spots(self) -> List[Dict[str, Any]]:
        """
        Identify non-obvious patterns humans wouldn't query.

        Returns:
            List of unexpected insights
        """
        students = self.db.query(Student).all()
        students_with_predictions = [s for s in students if s.predictions]

        blind_spots = []

        # Blind Spot 1: Early vs Late quarter performance
        early_late_pattern = self._compare_early_vs_late_performance(students_with_predictions)
        if early_late_pattern:
            blind_spots.append(early_late_pattern)

        # Blind Spot 2: Suspension impact
        suspension_pattern = self._analyze_suspension_impact(students_with_predictions)
        if suspension_pattern:
            blind_spots.append(suspension_pattern)

        return blind_spots

    def _compare_early_vs_late_performance(self, students: List[Student]) -> Optional[Dict]:
        """Compare Q1 vs Q4 performance across cohort."""
        early_strong = []
        late_strong = []

        for student in students:
            q1mpa7 = getattr(student, 'q1mpa7', None)
            q4mpa7 = getattr(student, 'q4mpa7', None)
            if q1mpa7 is not None and q4mpa7 is not None:
                if q1mpa7 > q4mpa7:  # type: ignore[attr-defined]
                    early_strong.append(student)
                elif q4mpa7 > q1mpa7:  # type: ignore[attr-defined]
                    late_strong.append(student)

        if len(early_strong) > len(late_strong) * 1.5:  # 50% more early-strong students
            return {
                "type": "performance_timing",
                "title": "Students Struggle More in Later Quarters",
                "description": (
                    f"{len(early_strong)} students perform better Q1 than Q4, vs {len(late_strong)} improving. "
                    f"This suggests curriculum difficulty increases or fatigue sets in."
                ),
                "evidence": {
                    "early_strong_count": len(early_strong),
                    "late_strong_count": len(late_strong)
                },
                "confidence": "medium",
                "insight": "Consider mid-semester support programs or adjust Q4 workload expectations."
            }

        return None

    def _analyze_suspension_impact(self, students: List[Student]) -> Optional[Dict]:
        """Check if suspensions correlate with risk."""
        students_with_suspensions = [s for s in students if getattr(s, 'nsusp7', None) and getattr(s, 'nsusp7', 0) > 0]
        students_without_suspensions = [s for s in students if not getattr(s, 'nsusp7', None) or getattr(s, 'nsusp7', 0) == 0]

        if len(students_with_suspensions) < 3 or len(students_without_suspensions) < 3:
            return None

        avg_risk_with_susp = statistics.mean([s.predictions[0].risk_score for s in students_with_suspensions if s.predictions])
        avg_risk_without_susp = statistics.mean(
            [s.predictions[0].risk_score for s in students_without_suspensions if s.predictions])

        risk_diff = avg_risk_with_susp - avg_risk_without_susp

        if risk_diff > 25:
            return {
                "type": "suspension_correlation",
                "title": "Suspensions Highly Correlate with Dropout Risk",
                "description": (
                    f"Students with any suspension history have {risk_diff:.0f} points higher average risk. "
                    f"Suspension may be both symptom and cause of disengagement."
                ),
                "evidence": {
                    "with_suspension_avg_risk": round(avg_risk_with_susp, 1),
                    "without_suspension_avg_risk": round(avg_risk_without_susp, 1),
                    "students_with_suspensions": len(students_with_suspensions)
                },
                "confidence": "high",
                "insight": "Re-evaluate suspension practices or provide intensive support post-suspension."
            }

        return None


class CohortAnalyzer:
    """Analyzes cohort-level patterns for sales/retention teams."""

    def __init__(self, db: Session):
        self.db = db

    def analyze_churn_risk(self, cohort_filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Translate academic risk to business impact.

        Returns:
            Revenue risk and churn probability estimates
        """
        students = self.db.query(Student).all()
        students_with_predictions = [s for s in students if s.predictions]

        if not students_with_predictions:
            return {"error": "No student data available"}

        risk_scores = [s.predictions[0].risk_score for s in students_with_predictions]

        # Estimate churn probability (simple heuristic: risk_score / 100)
        high_churn_risk = len([r for r in risk_scores if r > 70])
        medium_churn_risk = len([r for r in risk_scores if 40 < r <= 70])
        low_churn_risk = len([r for r in risk_scores if r <= 40])

        # Estimate revenue at risk (assume $5000 per student avg)
        avg_tuition = 5000
        high_risk_revenue = high_churn_risk * avg_tuition * 0.6  # 60% churn probability
        medium_risk_revenue = medium_churn_risk * avg_tuition * 0.3  # 30% churn probability

        total_revenue_at_risk = high_risk_revenue + medium_risk_revenue

        return {
            "cohort_size": len(students_with_predictions),
            "average_risk_score": round(statistics.mean(risk_scores), 1),
            "churn_estimates": {
                "high_risk_students": high_churn_risk,
                "medium_risk_students": medium_churn_risk,
                "low_risk_students": low_churn_risk,
                "estimated_high_churn_pct": round((high_churn_risk / len(students_with_predictions)) * 60, 1),
                "estimated_medium_churn_pct": round((medium_churn_risk / len(students_with_predictions)) * 30, 1)
            },
            "revenue_impact": {
                "total_revenue_at_risk": round(total_revenue_at_risk, 2),
                "high_risk_revenue": round(high_risk_revenue, 2),
                "medium_risk_revenue": round(medium_risk_revenue, 2),
                "currency": "USD"
            },
            "confidence": "medium"
        }
