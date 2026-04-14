"""
FastAPI dependency injection helpers.

Security model
--------------
* Authentication  – `get_current_user` validates the Bearer JWT and returns the
                    database User row.  Missing / invalid token → 401.
* Authorization   – `require_role(["Admin", "Faculty"])` is a dependency factory
                    that wraps `get_current_user`.  Wrong role → 403.
                    Superusers (is_superuser=True) bypass role checks.

REMOVED (was a critical vulnerability):
  - `get_current_user_role` — read role from a forgeable X-User-Role header and
    defaulted to "admin" when absent, granting admin access to every anonymous request.
  - `require_role` that called the above instead of verifying the JWT.
"""

from typing import List, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import jwt as pyjwt
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import ALGORITHM, SECRET_KEY, EWS_SERVICE_NAME, EWS_TOKEN_AUDIENCE
from backend.database.connection import get_db, get_db_async
from backend.database.models.user import User
from backend.database.models.student import Student
from backend.database.models.revoked_token import RevokedToken

# Re-exported so routes can write `deps.User` without an extra import.
__all__ = [
    "get_db",
    "get_db_async",
    "get_current_user",
    "get_current_user_async",
    "require_role",
    "require_resource_ownership",
    "User",
    "AsyncSession",
]

# auto_error=True: FastAPI returns a standards-compliant 401 + WWW-Authenticate
# header automatically when no Bearer token is present, before our code runs.
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(reusable_oauth2),
) -> User:
    """
    Decode a Bearer JWT and return the corresponding User row.

    Raises:
      401 Unauthorized — token absent, malformed, expired, or signature invalid.
      403 Forbidden    — token is valid but the account is inactive.

    Using 401 (not 403) for token failures is the correct HTTP semantics:
    401 = "you are not authenticated", 403 = "authenticated but not allowed".
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = pyjwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub", "jti", "iss", "aud", "nbf"]},
            audience=EWS_TOKEN_AUDIENCE,
            issuer=EWS_SERVICE_NAME,
        )
        user_id: Optional[str] = payload.get("sub")
        token_jti: Optional[str] = payload.get("jti")
        if user_id is None:
            raise credentials_exc
        
        # Check if token has been revoked (SEC-4)
        if token_jti is not None:
            revoked = db.query(RevokedToken).filter(RevokedToken.jti == token_jti).first()
            if revoked is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    except InvalidTokenError:
        # Covers expired tokens, bad signature, malformed payload, etc.
        raise credentials_exc

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exc

    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        # Do not reveal whether the user existed; treat as invalid token.
        raise credentials_exc

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    return user


async def get_current_user_async(
    db: AsyncSession = Depends(get_db_async),
    token: str = Depends(reusable_oauth2),
) -> User:
    """
    Async version: Decode a Bearer JWT and return the corresponding User row.

    Usage in async routes:
        @router.get("/students/{student_id}")
        async def get_student(
            student_id: str,
            current_user: User = Depends(get_current_user_async),
            db: AsyncSession = Depends(get_db_async),
        ):
            result = await db.execute(select(Student).where(Student.id == student_id))
            ...

    Raises:
      401 Unauthorized — token absent, malformed, expired, or signature invalid.
      403 Forbidden    — token is valid but the account is inactive.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = pyjwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub", "jti", "iss", "aud", "nbf"]},
            audience=EWS_TOKEN_AUDIENCE,
            issuer=EWS_SERVICE_NAME,
        )
        user_id: Optional[str] = payload.get("sub")
        token_jti: Optional[str] = payload.get("jti")
        if user_id is None:
            raise credentials_exc

        # Check if token has been revoked (SEC-4)
        if token_jti is not None:
            result = await db.execute(
                select(RevokedToken).where(RevokedToken.jti == token_jti)
            )
            revoked = result.scalar_one_or_none()
            if revoked is not None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    except InvalidTokenError:
        raise credentials_exc

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exc

    # Async database query
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exc

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    return user


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------

def require_role(required_roles: List[str]):
    """
    Role-checking dependency factory **tied to the JWT identity**.

    Usage (in a route):

        # Gate the whole endpoint:
        @router.get("/...", dependencies=[Depends(require_role(["admin", "faculty"]))])

        # Get the authenticated user too:
        current_user: User = Depends(require_role(["admin"]))

    Role comparison is case-insensitive.
    Users with `is_superuser=True` bypass the role check entirely.

    Raises:
      401 — no valid JWT (propagated from get_current_user).
      403 — valid JWT but role is not in the allowed list.
    """
    required_lower = {r.lower() for r in required_roles}

    def checker(current_user: User = Depends(get_current_user)) -> User:
        # Superusers are exempt from role restrictions.
        if current_user.is_superuser:
            return current_user

        user_role = (current_user.role or "").lower()
        if user_role not in required_lower:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {required_roles}",
            )
        return current_user

    return checker


class ResourceOwnershipChecker:
    """
    Callable FastAPI dependency that enforces resource ownership for FERPA compliance.

    Access is granted if any of the following are true:
      1. User has role "faculty" or "admin" (staff can access any student)
      2. User's username/email matches the requested student_id (own record)
      3. User is a superuser

    Usage:
        @router.get("/predictions/{student_id}")
        def get_prediction(
            student_id: str,
            current_user: User = Depends(ResourceOwnershipChecker()),
        ):
            ...

        With explicit student_id parameter:
        @router.get("/students/{org_id}")
        def get_student(
            org_id: str,
            current_user: User = Depends(ResourceOwnershipChecker(student_id_param="org_id")),
        ):
            ...
    """

    def __init__(self, student_id_param: str = "student_id"):
        self.student_id_param = student_id_param

    def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        # Extract student_id from path parameters
        student_id = request.path_params.get(self.student_id_param, "")

        # Staff roles can access any student record
        staff_roles = {"faculty", "admin", "retention team"}
        user_role = (current_user.role or "").lower()

        if user_role in staff_roles:
            return current_user

        # Superusers bypass all checks
        if current_user.is_superuser:
            return current_user

        # Check if student exists first (404 before 403)
        student = db.query(Student).filter(Student.id == student_id).first()
        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found",
            )

        # Ownership is determined by matching the authenticated user's email
        # against the student's email record.
        if current_user.email != student.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not have permission to access this resource.",
            )

        return current_user


# Convenience factory function matching the expected pattern
def require_resource_ownership(student_id_param: str = "student_id"):
    """
    Factory function that returns a ResourceOwnershipChecker.

    This provides a cleaner import pattern for routes:
        from backend.api.deps import require_resource_ownership

        @router.get("/{student_id}")
        def get_student(
            student_id: str,
            user: User = Depends(require_resource_ownership()),
        ):
            ...
    """
    return ResourceOwnershipChecker(student_id_param)
