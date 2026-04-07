"""
Prediction Model
---------------
Database model for ML predictions and risk scores.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.database.connection import Base


class Prediction(Base):
    """
    Prediction model storing ML model outputs including risk scores,
    signal breakdowns, and prediction metadata.
    """
    __tablename__ = "predictions"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign Key
    student_id = Column(String, ForeignKey("students.id"), index=True)

    # Core predictions
    risk_score = Column(Float, index=True)  # 0-1 probability of dropout
    engagement_score = Column(Float)
    retention_likelihood = Column(String)  # 'high', 'medium', 'low'
    
    # Legacy metrics (from old model)
    attendance = Column(Float)
    assignments = Column(Float)
    grades = Column(Float)
    
    # ========== Signal Breakdown Scores (0-1 scale) ==========
    academic_signal_score = Column(Float)
    engagement_signal_score = Column(Float)
    consistency_signal_score = Column(Float)
    intent_signal_score = Column(Float)
    responsiveness_signal_score = Column(Float)
    
    # ========== Prediction Metadata ==========
    model_version = Column(String)  # e.g., 'xgboost_v1.0', 'random_forest_v1.0'
    prediction_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    top_risk_factors = Column(String)  # JSON string of top contributing features
    
    # Relationship
    student = relationship("Student", back_populates="predictions")
