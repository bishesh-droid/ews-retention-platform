"""
Prediction Model
---------------
Database model for ML predictions and risk scores.

DB-5 SCALE STANDARD:
All risk_score values in this table MUST be on a 0-100 scale (not 0-1).
- 0 = no risk (student fully engaged)
- 100 = maximum dropout risk
- Values are stored as Float to support 2 decimal precision (e.g., 75.42)

Write paths MUST normalize any 0-1 probability outputs by multiplying by 100:
    risk_score = round(raw_probability * 100, 2)

Query filters MUST use 0-100 thresholds:
    risk_score >= 70.0  # high risk threshold
    risk_score >= 40.0  # medium risk threshold

Mixed-scale bugs (storing both 0-1 and 0-100) have been fixed.
Always validate risk scores are within [0.0, 100.0] before storing.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.database.connection import Base


class Prediction(Base):
    """
    Prediction model storing ML model outputs including risk scores,
    signal breakdowns, and prediction metadata.

    Database Integrity:
    - risk_score is NOT NULL and constrained to [0.0, 100.0]
    - prediction_timestamp uses timezone-aware UTC datetime
    """
    __tablename__ = "predictions"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key
    student_id = Column(String, ForeignKey("students.id"), index=True, nullable=False)

    # Core predictions (DB-5: ALL scores MUST be 0-100 scale, not 0-1)
    # risk_score is NOT NULL with check constraint for valid range
    risk_score = Column(Float, index=True, nullable=False)  # 0-100 dropout risk scale
    engagement_score = Column(Float, nullable=False)
    retention_likelihood = Column(String, nullable=False)  # 'high', 'medium', 'low'

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
    # TODO: model_version currently stores "rule_based" since no trained ML model exists.
    # Future: will store ML model version when training pipeline is implemented.
    model_version = Column(String)
    prediction_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    prediction_date = Column(DateTime, default=lambda: datetime.now(timezone.utc).date(), nullable=False)
    top_risk_factors = Column(String)  # JSON string of top contributing features

    # Relationship
    student = relationship("Student", back_populates="predictions")

    __table_args__ = (
        # Ensure risk_score is within valid 0-100 range
        CheckConstraint(
            "risk_score >= 0.0 AND risk_score <= 100.0",
            name="check_risk_score_range"
        ),
        # Prevent duplicate predictions per student per day
        UniqueConstraint("student_id", "prediction_date", name="uq_prediction_student_date"),
    )
