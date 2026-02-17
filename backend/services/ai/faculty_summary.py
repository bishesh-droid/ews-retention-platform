"""
Faculty Summary Generator Module

Generates faculty-appropriate summaries for student profiles.
Designed to help faculty have productive conversations with students
without exposing sensitive risk predictions.

Key principles:
- Focus on observable behaviors, not predictions
- Suggest conversation starters, not diagnoses
- Provide actionable recommendations
- Maintain professional, supportive tone
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.services.ai.advisor_context import build_advisor_context
from backend.services.ai.llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)


class FacultySummaryGenerator:
    """Generates faculty-safe student summaries."""

    def __init__(self, db=None):
        self.db = db
        self.llm = None  # Initialized lazily

    def _get_llm(self, db=None):
        """Get or create LLM orchestrator with database session."""
        if db:
            return LLMOrchestrator(db)
        elif self.db:
            if not self.llm:
                self.llm = LLMOrchestrator(self.db)
            return self.llm
        return None

    async def generate_summary(
        self,
        student_data: Dict[str, Any],
        prediction_data: Optional[Dict[str, Any]] = None,
        intervention_history: Optional[List[Dict]] = None,
        include_talking_points: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a faculty-appropriate student summary.

        This summary:
        - Does NOT include specific risk percentages
        - Does NOT predict dropout likelihood
        - DOES include observable engagement patterns
        - DOES include academic performance trends
        - DOES suggest conversation starters

        Args:
            student_data: Student record
            prediction_data: Current prediction data (used for context, not exposed)
            intervention_history: Past interventions
            include_talking_points: Whether to include conversation starters

        Returns:
            Faculty-safe summary with actionable insights
        """
        # Build context with sensitive data for internal use
        context = build_advisor_context(
            student_data=student_data,
            prediction_data=prediction_data,
            intervention_history=intervention_history,
            include_sensitive=True  # For generating better insights
        )

        try:
            summary = await self._generate_with_llm(context, include_talking_points)
            return {
                "success": True,
                "student_id": student_data.get('id'),
                "generated_at": datetime.now().isoformat(),
                "summary": summary,
                "data_sources": [
                    "Academic Records",
                    "Attendance Logs",
                    "Previous Intervention History"
                ]
            }
        except Exception as e:
            logger.error(f"Failed to generate faculty summary: {e}")
            return self._get_fallback_summary(context, include_talking_points)

    async def _generate_with_llm(
        self,
        context: Dict[str, Any],
        include_talking_points: bool
    ) -> Dict[str, Any]:
        """Generate summary using LLM."""
        prompt = self._build_prompt(context, include_talking_points)

        try:
            response = await self.llm.generate(
                prompt=prompt,
                context=context,
                max_tokens=1000,
                temperature=0.6
            )

            return self._parse_response(response, context, include_talking_points)

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def _build_prompt(
        self,
        context: Dict[str, Any],
        include_talking_points: bool
    ) -> str:
        """Build the prompt for faculty summary generation."""
        academic = context.get('academic_history', {})
        risk = context.get('risk_assessment', {})
        interventions = context.get('intervention_history', {})

        prompt = f"""
You are helping a faculty member prepare for a student meeting.
Generate a professional, supportive summary.

IMPORTANT RULES:
- Do NOT mention specific risk percentages or dropout predictions
- Do NOT use alarming language
- Focus on OBSERVABLE patterns and behaviors
- Be constructive and solution-oriented
- Maintain student dignity

STUDENT DATA:
- Current GPA: {academic.get('current_gpa', 'N/A')}
- GPA Trend: {academic.get('gpa_trend_description', 'N/A')}
- Attendance Rate: {academic.get('current_attendance_rate', 'N/A')}%
- Attendance Trend: {academic.get('attendance_trend_description', 'N/A')}
- Identified Strengths: {', '.join(academic.get('strengths', ['Not specified']))}
- Areas for Growth: {', '.join(academic.get('areas_for_improvement', ['Not specified']))}
- Previous Support: {interventions.get('total_interventions', 0)} interactions
- Response Pattern: {interventions.get('response_pattern', 'unknown')}

Generate a summary with these sections:

1. STUDENT_SNAPSHOT: 2-3 sentence overview of the student's current academic standing

2. ENGAGEMENT_PATTERNS: Observable patterns in attendance, participation, assignment completion

3. ACADEMIC_TRENDS: How performance has changed over time

4. RECOMMENDED_SUPPORT: 2-3 specific support resources or strategies

{"5. TALKING_POINTS: 3-4 conversation starters for a productive meeting" if include_talking_points else ""}

Keep the tone professional, supportive, and focused on helping the student succeed.
"""
        return prompt

    def _parse_response(
        self,
        response: str,
        context: Dict,
        include_talking_points: bool
    ) -> Dict[str, Any]:
        """Parse LLM response into structured summary."""
        academic = context.get('academic_history', {})

        # Build structured summary
        summary = {
            "student_snapshot": self._extract_section(response, "STUDENT_SNAPSHOT") or
                self._generate_snapshot(academic),
            "engagement_patterns": self._extract_section(response, "ENGAGEMENT_PATTERNS") or
                self._generate_engagement_patterns(academic),
            "academic_trends": self._extract_section(response, "ACADEMIC_TRENDS") or
                academic.get('gpa_trend_description', 'Stable'),
            "recommended_support": self._extract_list(response, "RECOMMENDED_SUPPORT") or
                self._get_default_support(context),
            "key_observations": self._extract_observations(context)
        }

        if include_talking_points:
            summary["talking_points"] = self._extract_list(response, "TALKING_POINTS") or \
                self._get_default_talking_points(context)

        return summary

    def _extract_section(self, response: str, section: str) -> Optional[str]:
        """Extract a section from the response."""
        try:
            if section in response:
                start = response.index(section) + len(section)
                # Find the next section or end
                end = len(response)
                for marker in ["STUDENT_SNAPSHOT", "ENGAGEMENT_PATTERNS", "ACADEMIC_TRENDS",
                              "RECOMMENDED_SUPPORT", "TALKING_POINTS"]:
                    if marker in response[start:] and marker != section:
                        end = min(end, start + response[start:].index(marker))

                text = response[start:end].strip()
                # Clean up markers
                text = text.lstrip(':').strip()
                return text if text else None
        except Exception:
            pass
        return None

    def _extract_list(self, response: str, section: str) -> List[str]:
        """Extract a list from a section."""
        text = self._extract_section(response, section)
        if not text:
            return []

        # Split by common list markers
        items = []
        for line in text.split('\n'):
            line = line.strip()
            if line.startswith(('-', '*', '•', '1', '2', '3', '4')):
                clean = line.lstrip('-*•0123456789. ').strip()
                if clean:
                    items.append(clean)

        return items[:5]  # Max 5 items

    def _generate_snapshot(self, academic: Dict) -> str:
        """Generate a student snapshot from academic data."""
        gpa = academic.get('current_gpa')
        attendance = academic.get('current_attendance_rate')

        if gpa and gpa > 3.5 and attendance and attendance > 90:
            return "This student is performing well academically with strong attendance."
        elif gpa and gpa < 2.5:
            return "This student may benefit from additional academic support."
        elif attendance and attendance < 80:
            return "This student has shown inconsistent attendance patterns."
        else:
            return "This student is progressing through their coursework."

    def _generate_engagement_patterns(self, academic: Dict) -> str:
        """Generate engagement pattern description."""
        attendance = academic.get('current_attendance_rate', 85)
        trend = academic.get('attendance_trend', 0)

        if attendance > 90:
            pattern = "Regular attendance with consistent engagement"
        elif attendance > 80:
            pattern = "Generally present with some absences"
        else:
            pattern = "Attendance could be more consistent"

        if trend < -0.1:
            pattern += ". Recent trend shows decreasing engagement."
        elif trend > 0.1:
            pattern += ". Recent trend shows improving engagement."

        return pattern

    def _extract_observations(self, context: Dict) -> List[str]:
        """Extract key observations from context."""
        observations = []
        academic = context.get('academic_history', {})
        risk = context.get('risk_assessment', {})

        # Strengths
        strengths = academic.get('strengths', [])
        if strengths:
            observations.append(f"Strengths: {', '.join(strengths)}")

        # Areas for focus (using softer language)
        areas = risk.get('areas_of_focus', [])
        area_map = {
            'academic_performance': 'May benefit from academic support',
            'course_engagement': 'Could increase course participation',
            'attendance': 'Attendance improvement opportunity',
            'performance_trend': 'Recent performance changes noted'
        }
        for area in areas[:2]:
            if area in area_map:
                observations.append(area_map[area])

        return observations

    def _get_default_support(self, context: Dict) -> List[str]:
        """Get default support recommendations."""
        areas = context.get('risk_assessment', {}).get('areas_of_focus', [])

        support = ["Academic advising office hours"]

        if 'academic_performance' in areas:
            support.extend([
                "Tutoring center for core subjects",
                "Study skills workshop"
            ])
        if 'attendance' in areas:
            support.extend([
                "Flexible scheduling options",
                "Check for any external barriers"
            ])
        if 'course_engagement' in areas:
            support.extend([
                "Study group connections",
                "Office hours encouragement"
            ])

        return support[:4]

    def _get_default_talking_points(self, context: Dict) -> List[str]:
        """Get default conversation starters."""
        academic = context.get('academic_history', {})
        strengths = academic.get('strengths', [])

        points = [
            "How are you finding the coursework this semester?",
            "Is there anything making it difficult to attend class regularly?",
            "What resources have you found helpful so far?"
        ]

        if strengths:
            points.insert(0, f"I noticed you're doing well with {strengths[0].lower()}. What's working for you?")

        return points[:4]

    def _get_fallback_summary(
        self,
        context: Dict,
        include_talking_points: bool
    ) -> Dict[str, Any]:
        """Return fallback summary when LLM fails."""
        academic = context.get('academic_history', {})

        summary = {
            "success": False,
            "student_id": context.get('student_id'),
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "student_snapshot": self._generate_snapshot(academic),
                "engagement_patterns": self._generate_engagement_patterns(academic),
                "academic_trends": academic.get('gpa_trend_description', 'Data not available'),
                "recommended_support": self._get_default_support(context),
                "key_observations": self._extract_observations(context)
            },
            "error": "AI generation unavailable, using template summary"
        }

        if include_talking_points:
            summary["summary"]["talking_points"] = self._get_default_talking_points(context)

        return summary


# Factory function instead of singleton to avoid import-time initialization
def get_faculty_summary_generator(db=None):
    """Get a FacultySummaryGenerator instance."""
    return FacultySummaryGenerator(db=db)


async def generate_faculty_summary(
    student_data: Dict,
    prediction_data: Optional[Dict] = None,
    intervention_history: Optional[List] = None,
    include_talking_points: bool = True,
    db=None
) -> Dict:
    """Convenience function for generating faculty summaries."""
    generator = get_faculty_summary_generator(db=db)
    return await generator.generate_summary(
        student_data=student_data,
        prediction_data=prediction_data,
        intervention_history=intervention_history,
        include_talking_points=include_talking_points
    )
