"""
Audit Logging Helper
--------------------
Provides functions for logging data access for FERPA compliance.

Usage:
    from backend.core.audit_logger import log_data_access

    log_data_access(
        db=db_session,
        user=current_user,
        action="READ",
        resource_type="student",
        resource_id=student_id,
        request=request
    )
"""

import os
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import Request

from backend.database.models.audit import AuditLog
from backend.database.models.user import User


def log_data_access(
    db: Session,
    user: Optional[User],
    action: str,  # READ, WRITE, DELETE
    resource_type: str,  # student, enrollment, grade, etc.
    resource_id: str,
    request: Optional[Request] = None,
    request_id: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuditLog:
    """
    Log a data access event for FERPA compliance.

    This function creates an audit log entry recording who accessed what data
    and when. It should be called from all endpoints that read, write, or
    delete sensitive student data.

    Args:
        db: Database session
        user: The user performing the action (from get_current_user)
        action: One of "READ", "WRITE", "DELETE"
        resource_type: Type of resource accessed (e.g., "student", "enrollment")
        resource_id: Unique identifier of the resource (e.g., student_id)
        request: FastAPI request object (to extract IP address and request_id)
        request_id: Optional explicit request_id (falls back to request.state.request_id)
        details: Optional additional details (stored as JSON)

    Returns:
        The created AuditLog record

    Example:
        @router.get("/students/{student_id}")
        def get_student(
            student_id: str,
            db: Session = Depends(get_db),
            request: Request = None,  # FastAPI provides this
            current_user: User = Depends(get_current_user),
        ):
            student = get_student_by_id(db, student_id)
            log_data_access(db, current_user, "READ", "student", student_id, request)
            return student
    """
    # Extract IP address from request if available
    # Only trust X-Forwarded-For when request arrives from a known proxy
    ip_address = None
    if request is not None:
        trusted_proxies = set(
            ip.strip()
            for ip in os.getenv("TRUSTED_PROXY_IPS", "").split(",")
            if ip.strip()
        )
        if request.client and request.client.host in trusted_proxies:
            forwarded = request.headers.get("X-Forwarded-For", "")
            ip_address = (
                forwarded.split(",")[0].strip() if forwarded else request.client.host
            )
        else:
            ip_address = request.client.host if request.client else "unknown"

    # Extract request_id from request state or use provided value
    req_id = request_id
    if req_id is None and request is not None:
        req_id = getattr(request.state, "request_id", None)

    # Get user role
    user_role = None
    if user is not None:
        user_role = getattr(user, "role", None)

    # Create audit log entry
    audit_log = AuditLog(
        user_id=getattr(user, "id", None) if user else None,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),  # Ensure string
        ip_address=ip_address,
        request_id=req_id,
        # Legacy field mapping
        action_type=f"{action}_{resource_type}" if action and resource_type else None,
        affected_student_id=resource_id if resource_type == "student" else None,
        details=details,
    )

    db.add(audit_log)
    # Caller controls commit — do NOT commit here to maintain transaction atomicity
    return audit_log


def log_bulk_data_access(
    db: Session,
    user: Optional[User],
    action: str,
    resource_type: str,
    resource_ids: list,
    request: Optional[Request] = None,
    request_id: Optional[str] = None,
) -> list[AuditLog]:
    """
    Log bulk data access (e.g., listing all students).

    For bulk operations, creates a single audit log entry with resource_id="BULK"
    and includes the count and query context in details.

    Args:
        db: Database session
        user: The user performing the action
        action: One of "READ", "WRITE", "DELETE"
        resource_type: Type of resource accessed
        resource_ids: List of resource IDs that were accessed
        request: FastAPI request object
        request_id: Optional request ID

    Returns:
        List of created AuditLog records
    """
    logs = []

    # Log a summary entry for the bulk operation
    # Only trust X-Forwarded-For when request arrives from a known proxy
    ip_address = None
    if request is not None:
        trusted_proxies = set(
            ip.strip()
            for ip in os.getenv("TRUSTED_PROXY_IPS", "").split(",")
            if ip.strip()
        )
        if request.client and request.client.host in trusted_proxies:
            forwarded = request.headers.get("X-Forwarded-For", "")
            ip_address = (
                forwarded.split(",")[0].strip() if forwarded else request.client.host
            )
        else:
            ip_address = request.client.host if request.client else "unknown"

    req_id = request_id
    if req_id is None and request is not None:
        req_id = getattr(request.state, "request_id", None)

    user_role = getattr(user, "role", None) if user else None

    # Create bulk summary log
    bulk_log = AuditLog(
        user_id=getattr(user, "id", None) if user else None,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id="BULK",
        ip_address=ip_address,
        request_id=req_id,
        action_type=f"{action}_{resource_type}_BULK",
        details={
            "count": len(resource_ids),
            "resource_ids": resource_ids[:100],  # Limit to first 100 IDs
            "truncated": len(resource_ids) > 100,
        },
    )

    db.add(bulk_log)
    logs.append(bulk_log)
    # Caller controls commit — do NOT commit here to maintain transaction atomicity
    return logs
