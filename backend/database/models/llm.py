"""
LLM Models
---------
Database models for LLM interactions, insights, and explanations.
"""

from sqlalchemy import Column, Integer, String, Boolean, Date
from backend.database.connection import Base


class LLMQuery(Base):
    """
    Tracks all LLM interactions for audit, improvement, and cost tracking.
    Enables analysis of LLM usage patterns and response quality.
    """
    __tablename__ = "llm_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    user_role = Column(String)  # 'student', 'faculty', 'admin', 'sales', 'marketing'
    query_type = Column(String)  # 'explain_risk', 'advice', 'cohort_analysis', etc.
    input_data = Column(String)  # JSON string of input data
    response = Column(String)  # LLM-generated response
    confidence = Column(String)  # 'high', 'medium', 'low'
    sources = Column(String)  # JSON array of data sources used
    timestamp = Column(Date)


class LLMInsight(Base):
    """
    Stores institutional insights discovered by LLM through pattern analysis.
    These are proactive insights the system surfaces for administrators.
    """
    __tablename__ = "llm_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    insight_type = Column(String)  # 'systemic_issue', 'pattern', 'blind_spot', 'opportunity'
    title = Column(String)
    content = Column(String)  # Full insight explanation
    source_data = Column(String)  # JSON of data that led to this insight
    confidence = Column(String)  # 'high', 'medium', 'low'
    visibility = Column(String)  # 'public', 'admin_only', 'leadership'
    created_at = Column(Date)
    dismissed = Column(Boolean, default=False)  # Has admin dismissed this?


class AIExplanation(Base):
    """
    Stores AI-generated explanations for students to provide transparency
    and help them understand their risk scores and recommendations.
    """
    __tablename__ = "ai_explanations"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String)
    explanation_type = Column(String)  # 'risk_change', 'advice', 'what_if', 'progress'
    content = Column(String)  # The generated explanation text
    confidence = Column(String)  # 'high', 'medium', 'low'
    created_at = Column(Date)
    viewed = Column(Boolean, default=False)  # Has student viewed this?


class PatternDiscovery(Base):
    """
    Stores discovered institutional patterns and blind spots identified by LLM.
    These represent systemic issues that require administrative attention.
    """
    __tablename__ = "pattern_discoveries"
    
    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(String)  # 'systemic_issue', 'cross_semester', 'demographic_disparity', 'blind_spot'
    title = Column(String)  # Short title for the pattern
    description = Column(String)  # Detailed description
    severity = Column(String)  # 'low', 'medium', 'high', 'critical'
    affected_cohort = Column(String)  # JSON array of affected cohort identifiers
    root_cause = Column(String)  # LLM-suggested root cause analysis
    suggested_action = Column(String)  # Recommended institutional-level intervention
    supporting_data = Column(String)  # JSON of statistical evidence
    confidence = Column(String)  # 'high', 'medium', 'low'
    discovered_at = Column(Date)
    acknowledged = Column(Boolean, default=False)  # Has admin reviewed this?
    acted_upon = Column(Boolean, default=False)  # Has action been taken?
