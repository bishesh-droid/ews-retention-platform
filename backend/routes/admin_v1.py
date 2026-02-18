from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from backend.database import User, AuditLog
from backend.api import deps
from backend.schemas.auth import UserOut

router = APIRouter()

@router.get("/users", response_model=List[UserOut])
def list_users(
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
    db: Session = Depends(deps.get_db)
):
    """
    List all system users (Admin only).
    """
    return db.query(User).all()

@router.get("/audit-logs")
def get_audit_logs(
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
    db: Session = Depends(deps.get_db)
):
    """
    Get system audit trail (Admin only).
    """
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
