"""
Intervention Model
-----------------
Database model for intervention tracking and effectiveness.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class Intervention(Base):
    """
    Intervention model tracking all interventions applied to students,
    including AI-suggested interventions and their effectiveness.
    """
    __tablename__ = "interventions"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    student_id = Column(String, ForeignKey("students.id"))
    
    # Intervention details
    date = Column(Date)
    user = Column(String)  # Who performed the intervention
    action = Column(String)  # Description of the intervention action
    
    # AI integration
    ai_suggested = Column(Boolean, default=False)  # False=manual, True=AI-suggested
    ai_reasoning = Column(String)  # LLM explanation for why this intervention was suggested
    
    # Effectiveness tracking
    effectiveness_score = Column(Float)  # Measured impact on student metrics (0-1 scale)
    
    # Risk context at time of intervention
    risk_score_at_trigger = Column(Float)  # Student's risk score when intervention was triggered
    threshold_category = Column(String)  # 'gentle_reminder', 'mentor_outreach', 'urgent_intervention'
    
    # Intervention details
    channels = Column(String)  # JSON string: ["email", "whatsapp", "mentor_call"]
    assigned_team = Column(String)  # 'automated', 'faculty', 'sales', 'counselor'
    
    # Relationships
    student = relationship("Student", back_populates="interventions")
    responses = relationship("StudentResponse", back_populates="intervention")
