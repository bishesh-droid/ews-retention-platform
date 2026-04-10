"""
Audit Log API Endpoints
-----------------------
Provides FERPA-compliant audit trail access for administrators.

All endpoints require admin role for access.
"""

from typing import Optional
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError

from backend.api.deps import get_db, require_role
from backend.database.models.user import User
from backend.database.models.audit import AuditLog
from backend.core.logger import sys_logger

router = APIRouter()

# Admin-only role requirement
_ADMIN_ROLES = ["admin"]


@router.get("/audit-log")
def get_audit_logs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of records to return"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action (READ/WRITE/DELETE)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    start_date: Optional[date] = Query(None, description="Filter from this date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter to this date (inclusive)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(_ADMIN_ROLES)),
):
    """
    Get paginated audit logs for FERPA compliance review.

    This endpoint returns a list of all data access events, including:
    - Who accessed the data (user_id, user_role)
    - What action was performed (READ/WRITE/DELETE)
    - What resource was accessed (resource_type, resource_id)
    - When it occurred (timestamp)
    - From where (ip_address)
    - Request trace ID (request_id)

    Access: Admin only (for FERPA compliance monitoring)
    """
    try:
        query = db.query(AuditLog)

        # Apply filters
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if action:
            query = query.filter(AuditLog.action == action.upper())
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        if start_date:
            query = query.filter(AuditLog.timestamp >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(AuditLog.timestamp <= datetime.combine(end_date, datetime.max.time()))

        # Get total count for pagination
        total = query.count()

        # Apply ordering and pagination
        logs = (
            query.order_by(desc(AuditLog.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )

        # Format response
        return {
            "logs": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "user_role": log.user_role,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "ip_address": log.ip_address,
                    "request_id": log.request_id,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "details": log.details,
                }
                for log in logs
            ],
            "total": total,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "page_size": limit,
            "filters_applied": {
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        }
    except SQLAlchemyError as e:
        sys_logger.error(f"Database error fetching audit logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit logs")


@router.get("/audit-log/summary")
def get_audit_summary(
    start_date: Optional[date] = Query(None, description="Summary from this date"),
    end_date: Optional[date] = Query(None, description="Summary to this date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(_ADMIN_ROLES)),
):
    """
    Get a summary of audit activity for compliance reporting.

    Returns aggregated statistics:
    - Total access events
    - Breakdown by action type (READ/WRITE/DELETE)
    - Breakdown by resource type
    - Top users by access count

    Access: Admin only
    """
    try:
        query = db.query(AuditLog)

        if start_date:
            query = query.filter(AuditLog.timestamp >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(AuditLog.timestamp <= datetime.combine(end_date, datetime.max.time()))

        # Total count
        total_access = query.count()

        # Breakdown by action
        action_counts = (
            db.query(AuditLog.action, func.count(AuditLog.id))
            .group_by(AuditLog.action)
            .all()
        )

        # Breakdown by resource type
        resource_counts = (
            db.query(AuditLog.resource_type, func.count(AuditLog.id))
            .group_by(AuditLog.resource_type)
            .all()
        )

        # Top users by access count
        top_users = (
            db.query(
                AuditLog.user_id,
                AuditLog.user_role,
                func.count(AuditLog.id).label("access_count")
            )
            .group_by(AuditLog.user_id, AuditLog.user_role)
            .order_by(desc("access_count"))
            .limit(10)
            .all()
        )

        return {
            "total_access_events": total_access,
            "date_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "by_action": {action: count for action, count in action_counts},
            "by_resource_type": {rtype: count for rtype, count in resource_counts},
            "top_users": [
                {
                    "user_id": user_id,
                    "user_role": role,
                    "access_count": count,
                }
                for user_id, role, count in top_users
            ],
        }
    except SQLAlchemyError as e:
        sys_logger.error(f"Database error fetching audit summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audit summary")


@router.get("/audit-log/student/{student_id}")
def get_student_audit_trail(
    student_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(_ADMIN_ROLES)),
):
    """
    Get audit trail for a specific student.

    Returns all access events related to this student, useful for
    FERPA compliance investigations.

    Access: Admin only
    """
    try:
        # Find all audit logs where this student was the resource
        logs = (
            db.query(AuditLog)
            .filter(
                (AuditLog.resource_id == student_id) |
                (AuditLog.affected_student_id == student_id)
            )
            .order_by(desc(AuditLog.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )

        total = (
            db.query(AuditLog)
            .filter(
                (AuditLog.resource_id == student_id) |
                (AuditLog.affected_student_id == student_id)
            )
            .count()
        )

        return {
            "student_id": student_id,
            "logs": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "user_role": log.user_role,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "ip_address": log.ip_address,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                }
                for log in logs
            ],
            "total": total,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "page_size": limit,
        }
    except SQLAlchemyError as e:
        sys_logger.error(f"Database error fetching student audit trail: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve student audit trail")
