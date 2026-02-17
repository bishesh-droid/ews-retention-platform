from sqlalchemy.orm import Session
from datetime import datetime
from typing import Any, Dict, Optional

from backend.database import AuditLog

class AuditService:
    @staticmethod
    def log_action(
        db: Session,
        user_id: int,
        user_role: str,
        action_type: str,
        affected_student_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Logs a structured action to the AuditLog table.
        """
        audit = AuditLog(
            user_id=user_id,
            user_role=user_role,
            action_type=action_type,
            affected_student_id=affected_student_id,
            details=details or {},
            timestamp=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit

    @staticmethod
    def log_risk_change(db: Session, user_id: int, user_role: str, student_id: str, old_score: float, new_score: float):
        return AuditService.log_action(
            db, user_id, user_role, "risk_score_change", student_id,
            {"old_score": old_score, "new_score": new_score}
        )

    @staticmethod
    def log_ai_generation(db: Session, user_id: int, user_role: str, student_id: str, prompt_type: str):
        return AuditService.log_action(
            db, user_id, user_role, "ai_advisory_generation", student_id,
            {"prompt_type": prompt_type}
        )
