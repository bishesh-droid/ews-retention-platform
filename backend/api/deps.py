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

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.config import ALGORITHM, SECRET_KEY
from backend.database.connection import get_db, get_db_async
from backend.database.models.user import User

# Re-exported so routes can write `deps.User` without an extra import.
__all__ = ["get_db", "get_db_async", "get_current_user", "require_role", "User"]

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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
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
