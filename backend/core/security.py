import re
from fastapi import HTTPException, status
from typing import List, Callable, Dict, Any

class SecurityManager:
    """Centralized security and validation middleware functions."""

    @staticmethod
    def sanitize_input(data: str) -> str:
        """Removes potentially dangerous characters from string input."""
        if not data:
            return data
        # Basic sanitization: remove script tags and potentially harmful HTML chars
        sanitized = re.sub(r'<[^>]*>', '', str(data))
        return sanitized

    @staticmethod
    def enforce_role(user_role: str, allowed_roles: List[str]):
        """Enforces RBAC on protected endpoints."""
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to access this resource."
            )

    @staticmethod
    def validate_pagination(skip: int, limit: int):
        """Validates standard pagination parameters."""
        if skip < 0:
            raise HTTPException(status_code=400, detail="Skip must be >= 0")
        if limit <= 0 or limit > 1000:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")

security_manager = SecurityManager()
