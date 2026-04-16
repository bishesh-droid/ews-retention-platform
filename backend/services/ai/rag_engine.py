"""
RAG (Retrieval-Augmented Generation) Engine
--------------------------------------------
Retrieves authorized institutional data for LLM context building.
Ensures LLM only references actual data, preventing hallucinations.
"""

import hashlib
import secrets
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
from backend.database import Student
from backend.database.models.goals_and_risks import RiskSnapshot
from backend.database.models.academic import GradedComponent
from backend.services.ai.hallucination_guard import HallucinationPrevention
import statistics


# Alias so llm_orchestrator can import GuardrailValidator from this module.
# Tests verify these are the exact same class object.
GuardrailValidator = HallucinationPrevention


class StudentDataRetriever:
    """Fetches student-specific data for LLM context."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _pseudonymise_context(context: dict, session_salt: str) -> dict:
        """Replace PII identifiers with session-scoped pseudonyms before LLM dispatch."""
        safe = context.copy()
        if "student_id" in safe:
            safe["student_id"] = (
                "STUDENT_"
                + hashlib.sha256((str(safe["student_id"]) + session_salt).encode())
                .hexdigest()[:8]
                .upper()
            )
        # Remove any raw email/PII fields
        for key in ["email", "username", "first_name", "last_name"]:
            safe.pop(key, None)
        return safe

    def retrieve_student_context(
        self, student_id: str, depth: str = "detailed", pseudonymise: bool = True
    ) -> Dict[str, Any]:  # noqa: C901
        """
        Retrieve comprehensive student data for LLM prompts.

        Args:
            student_id: Student identifier
            depth: 'basic' | 'detailed' | 'comprehensive'

        Returns:
            Structured dictionary with student data and metadata
        """
        student = self.db.query(Student).filter(Student.id == student_id).first()

        if not student:
            return {"error": "Student not found", "student_id": student_id}

        # Basic student info
        context: Dict[str, Any] = {
            "student_id": student.id,
            "data_sources": [],
            "retrieved_at": datetime.now().isoformat(),
        }

        # Get latest prediction
        latest_prediction = student.predictions[0] if student.predictions else None

        if latest_prediction:
            context["current_metrics"] = {
                "risk_score": round(latest_prediction.risk_score, 1),
                "engagement_score": round(latest_prediction.engagement_score, 1),
                "retention_likelihood": latest_prediction.retention_likelihood,
                "attendance": round(latest_prediction.attendance, 1),
                "grades": round(latest_prediction.grades, 2),
            }
            context["data_sources"].append("prediction_model")

        # Risk trend from RiskSnapshot (last 7 weeks)
        latest_snapshots = (
            self.db.query(RiskSnapshot)
            .filter(RiskSnapshot.student_id == student.id)
            .order_by(RiskSnapshot.timestamp.desc())
            .limit(7)
            .all()
        )
        risk_trend = [
            round(s.risk_score, 1)
            for s in reversed(latest_snapshots)
            if s.risk_score is not None
        ]
        context["risk_trend"] = risk_trend
        context["current_risk_score"] = risk_trend[-1] if risk_trend else None
        context["risk_trend_direction"] = (
            "improving"
            if len(risk_trend) >= 2 and float(risk_trend[-1]) < float(risk_trend[-2])  # type: ignore[operator, arg-type]  # noqa: E501
            else (
                "worsening"
                if len(risk_trend) >= 2 and float(risk_trend[-1]) > float(risk_trend[-2])  # type: ignore[operator, arg-type]  # noqa: E501
                else "stable"
            )
        )
        if risk_trend:
            context["data_sources"].append("risk_history")

        # Grade signals from GradedComponent records
        graded = (
            self.db.query(GradedComponent)
            .filter(GradedComponent.student_id == student.id)
            .order_by(GradedComponent.id.desc())
            .limit(10)
            .all()
        )
        scores = [g.score for g in graded if g.score is not None]
        context["recent_quiz_scores"] = [round(s, 1) for s in scores[:5]]
        context["avg_quiz_score"] = (
            round(sum(scores) / len(scores), 1) if scores else None
        )
        context["missed_component_count"] = sum(1 for g in graded if g.missed)
        if scores:
            context["data_sources"].append("grade_records")

        # Interventions
        if student.interventions:
            context["interventions"] = [
                {
                    "date": str(getattr(intervention, "date", None)),
                    "user": getattr(intervention, "user", None),
                    "action": getattr(intervention, "action", None),
                }
                for intervention in list(student.interventions)[-5:]  # type: ignore[call-overload]
            ]
            context["data_sources"].append("intervention_history")

        # Risk level categorization
        if latest_prediction:
            risk = latest_prediction.risk_score
            if risk > 75:
                context["risk_category"] = "critical"
            elif risk > 50:
                context["risk_category"] = "high"
            elif risk > 25:
                context["risk_category"] = "moderate"
            else:
                context["risk_category"] = "low"

        # Pseudonymise before returning for LLM safety
        if pseudonymise:
            session_salt = secrets.token_hex(8)
            return self._pseudonymise_context(context, session_salt)
        return context

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate if trend is improving, declining, or stable."""
        if len(values) < 2:
            return "insufficient_data"

        recent = statistics.mean(values[-3:]) if len(values) >= 3 else values[-1]
        earlier = statistics.mean(values[:3]) if len(values) >= 3 else values[0]

        change_pct = ((recent - earlier) / earlier) * 100 if earlier != 0 else 0

        if change_pct > 5:
            return "improving"
        elif change_pct < -5:
            return "declining"
        else:
            return "stable"

    def _calculate_recent_change(self, values: List[float]) -> Dict[str, float]:
        """Calculate recent change in values."""
        if len(values) < 2:
            return {"change": 0, "change_pct": 0}

        recent = values[-1]
        previous = values[-2]

        change = recent - previous
        change_pct = (change / previous) * 100 if previous != 0 else 0

        return {"change": round(change, 2), "change_pct": round(change_pct, 1)}


class CohortDataRetriever:
    """Fetches cohort-level statistics and comparisons."""

    def __init__(self, db: Session):
        self.db = db

    def retrieve_cohort_context(self, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Retrieve cohort-level statistics.

        Args:
            filters: Optional filters (e.g., risk_threshold, date_range)

        Returns:
            Cohort statistics and patterns
        """
        students = self.db.query(Student).all()

        if not students:
            return {"error": "No students found"}

        # Get all students with predictions
        students_with_predictions = [s for s in students if s.predictions]

        if not students_with_predictions:
            return {"error": "No prediction data available"}

        # Calculate cohort metrics
        risk_scores = [s.predictions[0].risk_score for s in students_with_predictions]
        engagement_scores = [
            s.predictions[0].engagement_score for s in students_with_predictions
        ]

        context = {
            "total_students": len(students),
            "students_with_data": len(students_with_predictions),
            "average_risk_score": round(statistics.mean(risk_scores), 1),
            "median_risk_score": round(statistics.median(risk_scores), 1),
            "average_engagement": round(statistics.mean(engagement_scores), 1),
            "data_sources": ["cohort_aggregates", "prediction_model"],
            "retrieved_at": datetime.now().isoformat(),
        }

        # Risk distribution
        context["risk_distribution"] = {
            "critical": len([r for r in risk_scores if r > 75]),
            "high": len([r for r in risk_scores if 50 < r <= 75]),
            "moderate": len([r for r in risk_scores if 25 < r <= 50]),
            "low": len([r for r in risk_scores if r <= 25]),
        }

        # At-risk percentage
        at_risk_count = len([r for r in risk_scores if r > 60])
        context["at_risk_percentage"] = round(
            (at_risk_count / len(risk_scores)) * 100, 1
        )

        return context


class InstitutionalDataRetriever:
    """Fetches system-wide patterns and metrics."""

    def __init__(self, db: Session):
        self.db = db

    def retrieve_institutional_metrics(self) -> Dict[str, Any]:
        """
        Retrieve institutional-level insights.

        Returns:
            System-wide patterns and anomalies
        """
        students = self.db.query(Student).all()
        students_with_predictions = [s for s in students if s.predictions]

        if not students_with_predictions:
            return {"error": "Insufficient data for institutional analysis"}

        # Overall retention health
        risk_scores = [s.predictions[0].risk_score for s in students_with_predictions]
        avg_risk = statistics.mean(risk_scores)

        context = {
            "total_population": len(students),
            "retention_health_score": round(100 - avg_risk, 1),
            "high_risk_population_pct": round(
                (len([r for r in risk_scores if r > 60]) / len(risk_scores)) * 100, 1
            ),
            "data_sources": ["institutional_aggregates"],
            "retrieved_at": datetime.now().isoformat(),
        }

        # Intervention coverage
        total_interventions = sum(len(list(s.interventions)) if s.interventions else 0 for s in students)  # type: ignore[call-overload, misc]  # noqa: E501
        students_with_interventions = len([s for s in students if s.interventions])  # type: ignore[misc]

        context["intervention_metrics"] = {
            "total_interventions": total_interventions,
            "students_with_interventions": students_with_interventions,
            "coverage_pct": (
                round((students_with_interventions / len(students)) * 100, 1)
                if students
                else 0
            ),
        }

        return context


class ContextAssembler:
    """Assembles structured context for LLM prompts."""

    @staticmethod
    def assemble_for_student_explanation(student_context: Dict) -> str:
        """Create natural language context for student-facing explanations."""
        if "error" in student_context:
            return "No data available for this student."

        context_parts = []

        # Current status
        if "current_metrics" in student_context:
            metrics = student_context["current_metrics"]
            context_parts.append(f"Current risk score: {metrics['risk_score']}%")
            context_parts.append(f"Attendance rate: {metrics['attendance']}%")
            context_parts.append(f"Grade average: {metrics['grades']}")
            context_parts.append(f"Engagement score: {metrics['engagement_score']}%")

        # Attendance trend
        if "attendance_trend" in student_context:
            trend = student_context["attendance_trend"]
            context_parts.append(
                f"Attendance trend over last 7 periods: {trend['trend']}"
            )
            if trend["recent_change"]["change"] != 0:
                change = trend["recent_change"]
                direction = "increased" if change["change"] > 0 else "decreased"
                context_parts.append(
                    f"Recent attendance {direction} by {abs(change['change_pct'])}%"
                )

        # GPA trend
        if "gpa_trend" in student_context:
            trend = student_context["gpa_trend"]
            context_parts.append(f"GPA trend: {trend['trend']}")
            context_parts.append(f"Current GPA average: {trend['average']}")

        # Data sources for attribution
        sources = student_context.get("data_sources", [])
        context_parts.append(f"\nData sources: {', '.join(sources)}")

        return "\n".join(context_parts)

    @staticmethod
    def assemble_for_faculty_summary(student_context: Dict) -> str:
        """Create context for faculty-facing summaries."""
        if "error" in student_context:
            return "Insufficient data for summary."

        context_parts = [
            f"Student ID: {student_context['student_id']}",
            f"Risk Category: {student_context.get('risk_category', 'unknown').upper()}",
        ]

        if "current_metrics" in student_context:
            metrics = student_context["current_metrics"]
            context_parts.append(
                f"Risk: {metrics['risk_score']}%, Engagement: {metrics['engagement_score']}%"
            )

        if "interventions" in student_context:
            intervention_count = len(student_context["interventions"])
            context_parts.append(f"Previous interventions: {intervention_count}")
            if intervention_count > 0:
                latest = student_context["interventions"][-1]
                context_parts.append(
                    f"Latest action: {latest['action']} ({latest['date']})"
                )

        return "\n".join(context_parts)
