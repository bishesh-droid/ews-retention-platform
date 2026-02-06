"""
Study Plan Generator Module

Generates personalized study plans based on EWS data.
Uses AI to create actionable, achievable plans tailored to each student.

The AI does NOT calculate risk - it consumes EWS data to generate:
- Weekly focus areas
- Daily time allocation recommendations
- Specific actions to address identified concerns
- Milestones to track progress
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from backend.app.services.ai.advisor_context import build_advisor_context
from backend.app.services.ai.llm_orchestrator import LLMOrchestrator

logger = logging.getLogger(__name__)


class StudyPlanGenerator:
    """Generates personalized study plans using LLM."""

    def __init__(self, db=None):
        self.db = db
        self.llm = None  # Initialized lazily when db is provided
        self.plan_duration_weeks = 4

    def _get_llm(self, db=None):
        """Get or create LLM orchestrator with database session."""
        if db:
            return LLMOrchestrator(db)
        elif self.db:
            if not self.llm:
                self.llm = LLMOrchestrator(self.db)
            return self.llm
        return None

    async def generate_study_plan(
        self,
        student_data: Dict[str, Any],
        prediction_data: Optional[Dict[str, Any]] = None,
        intervention_history: Optional[List[Dict]] = None,
        preferences: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate a personalized 4-week study plan.

        Args:
            student_data: Student record
            prediction_data: Current risk/prediction data
            intervention_history: Past interventions
            preferences: Student preferences (study times, learning style, etc.)

        Returns:
            Structured study plan with weekly goals, daily schedule, and milestones
        """
        # Build context for LLM
        context = build_advisor_context(
            student_data=student_data,
            prediction_data=prediction_data,
            intervention_history=intervention_history,
            include_sensitive=False  # Don't expose raw risk scores
        )

        # Generate the plan
        try:
            plan = await self._generate_with_llm(context, preferences)
            return {
                "success": True,
                "student_id": student_data.get('id'),
                "generated_at": datetime.now().isoformat(),
                "plan_duration_weeks": self.plan_duration_weeks,
                "plan": plan,
                "context_summary": {
                    "status": context['risk_assessment'].get('status'),
                    "areas_of_focus": context['risk_assessment'].get('areas_of_focus', []),
                    "strengths": context['academic_history'].get('strengths', [])
                }
            }
        except Exception as e:
            logger.error(f"Failed to generate study plan: {e}")
            return self._get_fallback_plan(context)

    async def _generate_with_llm(
        self,
        context: Dict[str, Any],
        preferences: Optional[Dict]
    ) -> Dict[str, Any]:
        """Generate study plan using LLM."""
        prompt = self._build_prompt(context, preferences)

        try:
            response = await self.llm.generate(
                prompt=prompt,
                context=context,
                max_tokens=1500,
                temperature=0.7
            )

            # Parse LLM response
            plan = self._parse_llm_response(response)
            return plan

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def _build_prompt(
        self,
        context: Dict[str, Any],
        preferences: Optional[Dict]
    ) -> str:
        """Build the prompt for study plan generation."""
        academic = context.get('academic_history', {})
        risk = context.get('risk_assessment', {})
        hints = context.get('advisor_hints', [])

        prompt = f"""
You are an AI Academic Advisor. Generate a personalized 4-week study plan for a student.

STUDENT CONTEXT:
- Current Status: {risk.get('status', 'unknown')}
- Current GPA: {academic.get('current_gpa', 'N/A')}
- GPA Trend: {academic.get('gpa_trend_description', 'N/A')}
- Attendance Rate: {academic.get('current_attendance_rate', 'N/A')}%
- Areas Needing Focus: {', '.join(risk.get('areas_of_focus', ['general improvement']))}
- Strengths: {', '.join(academic.get('strengths', ['dedication to studies']))}
- Areas for Improvement: {', '.join(academic.get('areas_for_improvement', []))}

ADVISOR HINTS:
{chr(10).join(f'- {hint}' for hint in hints)}

STUDENT PREFERENCES:
{json.dumps(preferences or {'study_time': 'flexible', 'learning_style': 'mixed'}, indent=2)}

Generate a study plan with the following structure:

1. WEEKLY_PLAN: For each of the 4 weeks, provide:
   - week_number (1-4)
   - theme (e.g., "Building Foundation", "Strengthening Skills")
   - focus_areas (list of 2-3 specific areas)
   - goals (list of 2-3 achievable goals)
   - success_metrics (how to measure progress)

2. DAILY_SCHEDULE: Recommended daily time allocation:
   - morning_focus
   - afternoon_focus
   - evening_focus
   - study_hours_recommended (number)

3. ACTIONS: List of 5-7 specific, actionable steps the student should take

4. MILESTONES: 4 checkpoints (one per week) with:
   - week
   - milestone_description
   - how_to_verify

5. ENCOURAGEMENT: A brief encouraging message (2-3 sentences)

Respond ONLY with valid JSON in this exact structure. Be specific, practical, and encouraging.
"""
        return prompt

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured plan."""
        try:
            # Try to extract JSON from response
            # Handle cases where LLM wraps JSON in markdown code blocks
            clean_response = response.strip()
            if clean_response.startswith('```'):
                clean_response = clean_response.split('```')[1]
                if clean_response.startswith('json'):
                    clean_response = clean_response[4:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]

            plan = json.loads(clean_response.strip())
            return self._validate_plan_structure(plan)

        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse LLM response as JSON: {e}")
            # Return a structured response based on the text
            return self._extract_plan_from_text(response)

    def _validate_plan_structure(self, plan: Dict) -> Dict:
        """Ensure plan has required structure."""
        required_keys = ['WEEKLY_PLAN', 'DAILY_SCHEDULE', 'ACTIONS', 'MILESTONES']

        for key in required_keys:
            if key not in plan:
                plan[key] = self._get_default_section(key)

        return plan

    def _get_default_section(self, section: str) -> Any:
        """Get default content for missing sections."""
        defaults = {
            'WEEKLY_PLAN': [
                {
                    "week_number": i,
                    "theme": f"Week {i} Focus",
                    "focus_areas": ["Study habits", "Time management"],
                    "goals": ["Complete all assignments", "Attend all classes"],
                    "success_metrics": "Track completion rate"
                }
                for i in range(1, 5)
            ],
            'DAILY_SCHEDULE': {
                "morning_focus": "Review previous material",
                "afternoon_focus": "New learning and practice",
                "evening_focus": "Homework and preparation",
                "study_hours_recommended": 3
            },
            'ACTIONS': [
                "Create a weekly study schedule",
                "Set up a dedicated study space",
                "Review notes within 24 hours of class",
                "Use active recall techniques",
                "Take regular breaks (Pomodoro technique)"
            ],
            'MILESTONES': [
                {
                    "week": i,
                    "milestone_description": f"Week {i} checkpoint",
                    "how_to_verify": "Self-assessment"
                }
                for i in range(1, 5)
            ],
            'ENCOURAGEMENT': "You have the ability to succeed. Take it one step at a time."
        }
        return defaults.get(section, [])

    def _extract_plan_from_text(self, response: str) -> Dict:
        """Extract plan structure from unstructured text response."""
        # Fallback parser for when LLM doesn't return JSON
        return {
            'WEEKLY_PLAN': self._get_default_section('WEEKLY_PLAN'),
            'DAILY_SCHEDULE': self._get_default_section('DAILY_SCHEDULE'),
            'ACTIONS': self._get_default_section('ACTIONS'),
            'MILESTONES': self._get_default_section('MILESTONES'),
            'ENCOURAGEMENT': response[:200] if len(response) > 200 else response,
            'raw_response': response[:500]
        }

    def _get_fallback_plan(self, context: Dict) -> Dict[str, Any]:
        """Return a reasonable fallback plan when LLM fails."""
        areas = context.get('risk_assessment', {}).get('areas_of_focus', [])

        return {
            "success": False,
            "student_id": context.get('student_id'),
            "generated_at": datetime.now().isoformat(),
            "plan_duration_weeks": self.plan_duration_weeks,
            "plan": {
                'WEEKLY_PLAN': self._get_default_section('WEEKLY_PLAN'),
                'DAILY_SCHEDULE': self._get_default_section('DAILY_SCHEDULE'),
                'ACTIONS': self._generate_actions_from_areas(areas),
                'MILESTONES': self._get_default_section('MILESTONES'),
                'ENCOURAGEMENT': "Every step forward is progress. You've got this!"
            },
            "error": "AI generation unavailable, using template plan"
        }

    def _generate_actions_from_areas(self, areas: List[str]) -> List[str]:
        """Generate specific actions based on areas of focus."""
        action_map = {
            'academic_performance': [
                "Schedule tutoring sessions for challenging subjects",
                "Create summary sheets for each chapter",
                "Practice past exam questions"
            ],
            'course_engagement': [
                "Participate in at least one discussion per class",
                "Visit office hours once per week",
                "Join a study group"
            ],
            'attendance': [
                "Set multiple alarms for class times",
                "Prepare materials the night before",
                "Identify and address barriers to attendance"
            ],
            'performance_trend': [
                "Review feedback from recent assignments",
                "Identify patterns in mistakes",
                "Create a revision schedule"
            ]
        }

        actions = ["Create a weekly schedule and stick to it"]
        for area in areas:
            if area in action_map:
                actions.extend(action_map[area][:2])

        return actions[:7]  # Max 7 actions


# Factory function instead of singleton to avoid import-time initialization
def get_study_plan_generator(db=None):
    """Get a StudyPlanGenerator instance."""
    return StudyPlanGenerator(db=db)


async def generate_study_plan(
    student_data: Dict,
    prediction_data: Optional[Dict] = None,
    intervention_history: Optional[List] = None,
    preferences: Optional[Dict] = None,
    db=None
) -> Dict:
    """Convenience function for generating study plans."""
    generator = get_study_plan_generator(db=db)
    return await generator.generate_study_plan(
        student_data=student_data,
        prediction_data=prediction_data,
        intervention_history=intervention_history,
        preferences=preferences
    )
