"""
Prediction Log Model
--------------------
Audit trail for every prediction made by the ML pipeline.

ML-4: Tracks all inference calls for audit and debugging.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.database.connection import Base


class PredictionLog(Base):
    """
    Audit log entry for each prediction inference call.
    
    Stores input features, output scores, and metadata for traceability.
    This table grows quickly — consider archival strategy for old records.
    """
    __tablename__ = "prediction_logs"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Identifiers
    student_id = Column(String, ForeignKey("students.id"), index=True, nullable=False)
    
    # Model version used for this prediction (ML-2)
    model_version = Column(String, index=True, nullable=False)
    
    # Input features (JSON snapshot at prediction time)
    input_features = Column(JSON, nullable=True)
    
    # Output results
    output_score = Column(Float, nullable=False)  # 0-100 scale
    output_category = Column(String(20), nullable=True)  # 'low', 'medium', 'high'
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Optional: source info (API endpoint, scheduled job, etc.)
    source = Column(String(50), nullable=True)  # e.g., 'api', 'scheduler', 'manual'
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_prediction_logs_student_created', 'student_id', 'created_at'),
        Index('ix_prediction_logs_model_version', 'model_version'),
    )
    
    # Relationship (optional, for join queries)
    student = relationship("Student", back_populates="prediction_logs")
