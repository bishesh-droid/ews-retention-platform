"""
LLM Service - Core Orchestration Layer
---------------------------------------
Manages all LLM interactions with role-based prompts,
confidence scoring, and hallucination prevention.
"""

import os
from typing import Dict, List, Optional, Any

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

from sqlalchemy.orm import Session
from backend.services.ai.rag_engine import (
    StudentDataRetriever,
    CohortDataRetriever,
    InstitutionalDataRetriever,
    ContextAssembler,
    GuardrailValidator
)

# Configure Gemini
GEMINI_MODEL = "gemini-pro"
if GENAI_AVAILABLE and os.getenv("GEMINI_API_KEY"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


class LLMOrchestrator:
    """Main interface for all LLM operations with data grounding."""

    def __init__(self, db: Session):
        self.db = db
        self.student_retriever = StudentDataRetriever(db)
        self.cohort_retriever = CohortDataRetriever(db)
        self.institutional_retriever = InstitutionalDataRetriever(db)
        self.model = genai.GenerativeModel(GEMINI_MODEL) if GENAI_AVAILABLE and os.getenv("GEMINI_API_KEY") else None

    def _check_llm_available(self) -> Optional[Dict[str, Any]]:
        """Check if LLM is available, return error dict if not."""
        if not GENAI_AVAILABLE:
            return {
                "content": "AI service unavailable - google-generativeai package not installed",
                "confidence": "low",
                "sources": [],
                "error": "Module not installed"
            }
        if not os.getenv("GEMINI_API_KEY"):
            return {
                "content": "AI service unavailable - GEMINI_API_KEY not configured",
                "confidence": "low",
                "sources": [],
                "error": "API key not set"
            }
        return None
    
    def explain_risk_change(self, student_id: str, time_period: str = "recent") -> Dict[str, Any]:
        """
        Explain why a student's risk score changed.

        Args:
            student_id: Student identifier
            time_period: "recent" | "this_week" | "this_month"

        Returns:
            Explanation with sources and confidence
        """
        llm_error = self._check_llm_available()
        if llm_error:
            return llm_error

        # Retrieve student data via RAG
        student_context = self.student_retriever.retrieve_student_context(student_id, depth='detailed')
        
        if "error" in student_context:
            return {
                "content": "Unable to generate explanation: student data not found.",
                "confidence": "low",
                "sources": [],
                "error": student_context["error"]
            }
        
        # Build prompt with actual data
        prompt = self._build_risk_explanation_prompt(student_context, time_period)
        
        # Generate response
        try:
            response = self.model.generate_content(prompt)
            explanation = response.text
            
            # Validate response
            validation = GuardrailValidator.validate_response(explanation, student_context)
            
            # Calculate confidence
            confidence = self._calculate_confidence(validation, student_context)
            
            return {
                "content": explanation,
                "confidence": confidence,
                "sources": student_context.get("data_sources", []),
                "timestamp": student_context["retrieved_at"],
                "student_id": student_id,
                "validation": validation
            }
        except Exception as e:
            return {
                "content": f"Error generating explanation: {str(e)}",
                "confidence": "low",
                "sources": [],
                "error": str(e)
            }
    
    def generate_student_advice(self, student_id: str, question: str) -> Dict[str, Any]:
        """
        Generate personalized advice for a student.

        Args:
            student_id: Student identifier
            question: Student's question or concern

        Returns:
            Personalized advice with sources
        """
        llm_error = self._check_llm_available()
        if llm_error:
            return llm_error

        student_context = self.student_retriever.retrieve_student_context(student_id, depth='detailed')
        
        if "error" in student_context:
            return {
                "content": "I don't have enough information about your academic progress to provide specific advice.",
                "confidence": "low",
                "sources": []
            }
        
        prompt = self._build_student_advice_prompt(student_context, question)
        
        try:
            response = self.model.generate_content(prompt)
            advice = response.text
            
            validation = GuardrailValidator.validate_response(advice, student_context)
            confidence = self._calculate_confidence(validation, student_context)
            
            return {
                "content": advice,
                "confidence": confidence,
                "sources": student_context.get("data_sources", []),
                "timestamp": student_context["retrieved_at"]
            }
        except Exception as e:
            return {
                "content": "I'm having trouble generating advice right now. Please try again later.",
                "confidence": "low",
                "sources": [],
                "error": str(e)
            }
    
    def summarize_student_profile(self, student_id: str, for_role: str = "faculty") -> Dict[str, Any]:
        """
        Generate a student profile summary for faculty/counselors.

        Args:
            student_id: Student identifier
            for_role: "faculty" | "counselor" | "admin"

        Returns:
            Concise student summary
        """
        llm_error = self._check_llm_available()
        if llm_error:
            return llm_error

        student_context = self.student_retriever.retrieve_student_context(student_id, depth='comprehensive')
        
        if "error" in student_context:
            return {
                "content": "Student profile unavailable.",
                "confidence": "low",
                "sources": []
            }
        
        prompt = self._build_faculty_summary_prompt(student_context, for_role)
        
        try:
            response = self.model.generate_content(prompt)
            summary = response.text
            
            validation = GuardrailValidator.validate_response(summary, student_context)
            confidence = self._calculate_confidence(validation, student_context)
            
            return {
                "content": summary,
                "confidence": confidence,
                "sources": student_context.get("data_sources", []),
                "student_id": student_id,
                "risk_category": student_context.get("risk_category", "unknown")
            }
        except Exception as e:
            return {
                "content": "Unable to generate summary.",
                "confidence": "low",
                "sources": [],
                "error": str(e)
            }
    
    def suggest_interventions(self, student_id: str) -> Dict[str, Any]:
        """
        Suggest evidence-based interventions for a student.

        Args:
            student_id: Student identifier

        Returns:
            Intervention suggestions with reasoning
        """
        llm_error = self._check_llm_available()
        if llm_error:
            return llm_error

        student_context = self.student_retriever.retrieve_student_context(student_id, depth='detailed')
        
        if "error" in student_context:
            return {
                "content": [],
                "confidence": "low",
                "sources": []
            }
        
        prompt = self._build_intervention_prompt(student_context)
        
        try:
            response = self.model.generate_content(prompt)
            suggestions = response.text
            
            return {
                "content": suggestions,
                "confidence": "medium",  # Interventions always medium confidence
                "sources": student_context.get("data_sources", []),
                "student_id": student_id
            }
        except Exception as e:
            return {
                "content": "Unable to generate intervention suggestions.",
                "confidence": "low",
                "sources": [],
                "error": str(e)
            }
    
    def analyze_cohort_patterns(self, cohort_filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze patterns across a cohort for sales/retention teams.

        Args:
            cohort_filters: Optional filters

        Returns:
            Cohort insights and patterns
        """
        llm_error = self._check_llm_available()
        if llm_error:
            return llm_error

        cohort_context = self.cohort_retriever.retrieve_cohort_context(cohort_filters)
        
        if "error" in cohort_context:
            return {
                "content": "Insufficient cohort data for analysis.",
                "confidence": "low",
                "sources": []
            }
        
        prompt = self._build_cohort_analysis_prompt(cohort_context)
        
        try:
            response = self.model.generate_content(prompt)
            analysis = response.text
            
            return {
                "content": analysis,
                "confidence": "medium",
                "sources": cohort_context.get("data_sources", []),
                "cohort_size": cohort_context.get("total_students", 0)
            }
        except Exception as e:
            return {
                "content": "Unable to analyze cohort patterns.",
                "confidence": "low",
                "sources": [],
                "error": str(e)
            }
    
    def simulate_what_if(self, student_id: str, scenario: Dict) -> Dict[str, Any]:
        """
        Simulate a what-if scenario for a student.

        Args:
            student_id: Student identifier
            scenario: Dict with changes (e.g., {"attendance": 95, "grades": 3.5})

        Returns:
            Scenario analysis in natural language
        """
        llm_error = self._check_llm_available()
        if llm_error:
            return llm_error

        student_context = self.student_retriever.retrieve_student_context(student_id, depth='detailed')
        
        if "error" in student_context:
            return {
                "content": "Can't simulate scenarios without student data.",
                "confidence": "low",
                "sources": []
            }
        
        prompt = self._build_what_if_prompt(student_context, scenario)
        
        try:
            response = self.model.generate_content(prompt)
            simulation = response.text
            
            return {
                "content": simulation,
                "confidence": "medium",  # What-if always medium (speculative)
                "sources": student_context.get("data_sources", []),
                "scenario": scenario
            }
        except Exception as e:
            return {
                "content": "Unable to run simulation.",
                "confidence": "low",
                "sources": [],
                "error": str(e)
            }
    
    def generate_report_narrative(self, report_type: str, data: Dict) -> Dict[str, Any]:
        """
        Generate executive narrative for reports.

        Args:
            report_type: Type of report ("executive", "cohort", "institutional")
            data: Report data

        Returns:
            Auto-generated narrative
        """
        llm_error = self._check_llm_available()
        if llm_error:
            return llm_error

        prompt = self._build_report_narrative_prompt(report_type, data)
        
        try:
            response = self.model.generate_content(prompt)
            narrative = response.text
            
            return {
                "content": narrative,
                "confidence": "high",
                "report_type": report_type
            }
        except Exception as e:
            return {
                "content": "Unable to generate report narrative.",
                "confidence": "low",
                "error": str(e)
            }
    
    # ========== Prompt Builders ==========
    
    def _build_risk_explanation_prompt(self, context: Dict, time_period: str) -> str:
        """Build prompt for risk change explanation."""
        context_text = ContextAssembler.assemble_for_student_explanation(context)
        
        return f"""You are an empathetic academic advisor explaining risk score changes to a student.

IMPORTANT INSTRUCTIONS:
- Be calm, supportive, and non-alarming
- Use simple, encouraging language
- Cite specific data from the context below
- Focus on actionable insights
- Never fabricate data not in the context
- Keep explanation concise (3-4 sentences)

STUDENT DATA:
{context_text}

Task: Explain why this student's risk score is {context.get('current_metrics', {}).get('risk_score', 'unknown')}% and what specific factors contributed to recent changes.

Begin your explanation with "Based on your recent academic activity..." and cite specific metrics."""
    
    def _build_student_advice_prompt(self, context: Dict, question: str) -> str:
        """Build prompt for student advice."""
        context_text = ContextAssembler.assemble_for_student_explanation(context)
        
        return f"""You are a supportive academic coach providing personalized advice to a student.

STUDENT DATA:
{context_text}

STUDENT QUESTION: "{question}"

INSTRUCTIONS:
- Provide specific, actionable advice
- Reference their actual data (attendance, grades, trends)
- Be encouraging and realistic
- Suggest 2-3 concrete micro-goals
- Never make unsupported claims
- Keep advice concise and practical

Provide your advice:"""
    
    def _build_faculty_summary_prompt(self, context: Dict, for_role: str) -> str:
        """Build prompt for faculty summary."""
        context_text = ContextAssembler.assemble_for_faculty_summary(context)
        
        return f"""You are an AI assistant helping {for_role} quickly understand a student's situation.

STUDENT CONTEXT:
{context_text}

INSTRUCTIONS:
- Generate a 3-4 sentence summary
- Highlight key concerns and patterns
- Recommend 1-2 priority actions
- Use professional, time-saving language
- Cite specific metrics

Provide the summary:"""
    
    def _build_intervention_prompt(self, context: Dict) -> str:
        """Build prompt for intervention suggestions."""
        context_text = ContextAssembler.assemble_for_faculty_summary(context)
        
        return f"""You are an intervention specialist suggesting evidence-based actions for at-risk students.

STUDENT CONTEXT:
{context_text}

INSTRUCTIONS:
- Suggest 2-3 specific interventions
- Explain why each intervention is appropriate
- Consider past interventions if any
- Be practical and actionable
- Cite student's specific risk factors

Provide intervention suggestions:"""
    
    def _build_cohort_analysis_prompt(self, context: Dict) -> str:
        """Build prompt for cohort analysis."""
        return f"""You are a retention analyst translating academic risk into business insights for sales/retention teams.

COHORT DATA:
Total Students: {context.get('total_students', 0)}
Average Risk Score: {context.get('average_risk_score', 0)}%
At-Risk Percentage: {context.get('at_risk_percentage', 0)}%
Risk Distribution: {context.get('risk_distribution', {})}

INSTRUCTIONS:
- Translate academic risk to churn probability
- Identify key dropout drivers
- Use executive-friendly language
- Provide actionable retention recommendations
- Keep analysis concise (4-5 sentences)

Provide cohort analysis:"""
    
    def _build_what_if_prompt(self, context: Dict, scenario: Dict) -> str:
        """Build prompt for what-if simulation."""
        context_text = ContextAssembler.assemble_for_student_explanation(context)
        
        return f"""You are an academic advisor explaining the likely impact of behavior changes.

CURRENT STUDENT DATA:
{context_text}

PROPOSED CHANGES:
{scenario}

INSTRUCTIONS:
- Explain how these changes would likely affect risk score
- Use encouraging, motivational language
- Be realistic but optimistic
- Keep explanation brief (3-4 sentences)
- Reference current metrics for comparison

Explain the projected impact:"""
    
    def _build_report_narrative_prompt(self, report_type: str, data: Dict) -> str:
        """Build prompt for report narrative."""
        return f"""You are a report writer creating executive summaries for leadership.

REPORT TYPE: {report_type}
REPORT DATA: {data}

INSTRUCTIONS:
- Write a calm, professional executive summary
- Highlight key findings and anomalies
- Suggest next actions
- Use clear, jargon-free language
- Keep summary concise (5-6 sentences)

Generate the report narrative:"""
    
    # ========== Confidence Calculation ==========
    
    def _calculate_confidence(self, validation: Dict, context: Dict) -> str:
        """Calculate confidence level based on data quality and validation."""
        # Start with validation confidence
        confidence = validation.get("confidence", "medium")
        
        # Downgrade if limited data sources
        data_sources = len(context.get("data_sources", []))
        if data_sources < 2 and confidence == "high":
            confidence = "medium"
        
        # Downgrade if validation issues
        if len(validation.get("issues", [])) > 2:
            confidence = "low"
        
        return confidence
