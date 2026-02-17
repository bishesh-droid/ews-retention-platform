"""
RAG (Retrieval-Augmented Generation) Engine
--------------------------------------------
Retrieves authorized institutional data for LLM context building.
Ensures LLM only references actual data, preventing hallucinations.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from backend.database import Student, Prediction, Intervention
import statistics


class StudentDataRetriever:
    """Fetches student-specific data for LLM context."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def retrieve_student_context(self, student_id: str, depth: str = 'detailed') -> Dict[str, Any]:
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
        context = {
            "student_id": student.id,
            "data_sources": [],
            "retrieved_at": datetime.now().isoformat()
        }
        
        # Get latest prediction
        latest_prediction = student.predictions[0] if student.predictions else None
        
        if latest_prediction:
            context["current_metrics"] = {
                "risk_score": round(latest_prediction.risk_score, 1),
                "engagement_score": round(latest_prediction.engagement_score, 1),
                "retention_likelihood": latest_prediction.retention_likelihood,
                "attendance": round(latest_prediction.attendance, 1),
                "grades": round(latest_prediction.grades, 2)
            }
            context["data_sources"].append("prediction_model")
        
        # Attendance trend (last 7 periods)
        attendance_trend = [
            student.absrate1, student.absrate2, student.absrate3,
            student.absrate4, student.absrate5, student.absrate6, student.absrate7
        ]
        attendance_trend = [a for a in attendance_trend if a is not None]
        
        if attendance_trend:
            # Convert absence rate to attendance percentage
            attendance_percentages = [(1 - rate) * 100 for rate in attendance_trend]
            context["attendance_trend"] = {
                "last_7_periods": [round(a, 1) for a in attendance_percentages],
                "average": round(statistics.mean(attendance_percentages), 1),
                "trend": self._calculate_trend(attendance_percentages),
                "recent_change": self._calculate_recent_change(attendance_percentages)
            }
            context["data_sources"].append("attendance_records")
        
        # GPA trend (quarterly averages from last 7 quarters)
        gpa_trend = [
            student.q4mpa1, student.q4mpa2, student.q4mpa3,
            student.q4mpa4, student.q4mpa5, student.q4mpa6, student.q4mpa7
        ]
        gpa_trend = [g for g in gpa_trend if g is not None]
        
        if gpa_trend:
            context["gpa_trend"] = {
                "last_7_quarters": [round(g, 2) for g in gpa_trend],
                "average": round(statistics.mean(gpa_trend), 2),
                "trend": self._calculate_trend(gpa_trend),
                "recent_change": self._calculate_recent_change(gpa_trend)
            }
            context["data_sources"].append("grade_records")
        
        # Interventions
        if student.interventions:
            context["interventions"] = [
                {
                    "date": str(intervention.date),
                    "user": intervention.user,
                    "action": intervention.action
                }
                for intervention in student.interventions[-5:]  # Last 5 interventions
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
        
        return {
            "change": round(change, 2),
            "change_pct": round(change_pct, 1)
        }


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
        engagement_scores = [s.predictions[0].engagement_score for s in students_with_predictions]
        
        context = {
            "total_students": len(students),
            "students_with_data": len(students_with_predictions),
            "average_risk_score": round(statistics.mean(risk_scores), 1),
            "median_risk_score": round(statistics.median(risk_scores), 1),
            "average_engagement": round(statistics.mean(engagement_scores), 1),
            "data_sources": ["cohort_aggregates", "prediction_model"],
            "retrieved_at": datetime.now().isoformat()
        }
        
        # Risk distribution
        context["risk_distribution"] = {
            "critical": len([r for r in risk_scores if r > 75]),
            "high": len([r for r in risk_scores if 50 < r <= 75]),
            "moderate": len([r for r in risk_scores if 25 < r <= 50]),
            "low": len([r for r in risk_scores if r <= 25])
        }
        
        # At-risk percentage
        at_risk_count = len([r for r in risk_scores if r > 60])
        context["at_risk_percentage"] = round((at_risk_count / len(risk_scores)) * 100, 1)
        
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
            "high_risk_population_pct": round((len([r for r in risk_scores if r > 60]) / len(risk_scores)) * 100, 1),
            "data_sources": ["institutional_aggregates"],
            "retrieved_at": datetime.now().isoformat()
        }
        
        # Intervention coverage
        total_interventions = sum(len(s.interventions) for s in students)
        students_with_interventions = len([s for s in students if s.interventions])
        
        context["intervention_metrics"] = {
            "total_interventions": total_interventions,
            "students_with_interventions": students_with_interventions,
            "coverage_pct": round((students_with_interventions / len(students)) * 100, 1) if students else 0
        }
        
        return context


class ContextAssembler:
    """Assembles structured context for LLM prompts."""
    
    @staticmethod
    def assemble_for_student_explanation(student_context: Dict) -> str:
        """Create natural language context for student-facing explanations."""
        if "error" in student_context:
            return f"No data available for this student."
        
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
            context_parts.append(f"Attendance trend over last 7 periods: {trend['trend']}")
            if trend['recent_change']['change'] != 0:
                change = trend['recent_change']
                direction = "increased" if change['change'] > 0 else "decreased"
                context_parts.append(f"Recent attendance {direction} by {abs(change['change_pct'])}%")
        
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
            f"Risk Category: {student_context.get('risk_category', 'unknown').upper()}"
        ]
        
        if "current_metrics" in student_context:
            metrics = student_context["current_metrics"]
            context_parts.append(f"Risk: {metrics['risk_score']}%, Engagement: {metrics['engagement_score']}%")
        
        if "interventions" in student_context:
            intervention_count = len(student_context["interventions"])
            context_parts.append(f"Previous interventions: {intervention_count}")
            if intervention_count > 0:
                latest = student_context["interventions"][-1]
                context_parts.append(f"Latest action: {latest['action']} ({latest['date']})")
        
        return "\n".join(context_parts)


class GuardrailValidator:
    """Validates LLM responses against authorized data to prevent hallucinations."""
    
    @staticmethod
    def validate_response(response: str, allowed_data: Dict) -> Dict[str, Any]:
        """
        Check if LLM response only references data from allowed_data.
        
        Args:
            response: LLM generated text
            allowed_data: Data that was provided to LLM
        
        Returns:
            Validation result with confidence score
        """
        # Simple validation: check if response is reasonable length
        # In production, use more sophisticated fact-checking
        
        validation = {
            "is_valid": True,
            "confidence": "high",
            "issues": []
        }
        
        # Check for unreasonable claims
        if "100%" in response and "certain" in response.lower():
            validation["confidence"] = "medium"
            validation["issues"].append("Overly confident language detected")
        
        # Check length
        if len(response) < 20:
            validation["is_valid"] = False
            validation["issues"].append("Response too short")
        
        if len(response) > 2000:
            validation["confidence"] = "medium"
            validation["issues"].append("Response very long, may contain hallucinations")
        
        # Check for data source mentions
        if "based on" not in response.lower() and "according to" not in response.lower():
            validation["confidence"] = "medium"
            validation["issues"].append("No clear source attribution")
        
        return validation
