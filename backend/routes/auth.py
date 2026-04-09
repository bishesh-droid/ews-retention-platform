from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
import json

from backend.database import User
from backend.api import deps
from backend.core import auth
from backend.core.rate_limiting import limiter
from backend.database.models.audit import AuditLog
from backend.schemas.auth import (
    Token,
    UserOut,
    UserCreate,
    UserUpdate,
    AdminUserUpdate,
)
from backend.utils.api import success_response, error_response
from backend.config import ACCESS_TOKEN_EXPIRE_MINUTES, ENVIRONMENT, RATE_LIMIT_LOGIN
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Cookie settings for refresh token
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
REFRESH_TOKEN_EXPIRE_DAYS = 7


@router.post("/login", response_model=Token)
@limiter.limit(RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    OAuth2 token login — returns a Bearer JWT and sets httpOnly refresh token cookie.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive.",
        )

    # Create access token (short-lived)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        subject=user.id,
        role=user.role or "student",
        expires_delta=access_token_expires,
    )

    # Create refresh token (long-lived, stored in httpOnly cookie)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = auth.create_access_token(
        subject=user.id,
        role=user.role or "student",
        expires_delta=refresh_token_expires,
        token_type="refresh"
    )

    # Set httpOnly cookie with refresh token
    cookie_max_age = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # seconds
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=ENVIRONMENT == "production",  # HTTPS only in production
        samesite="lax",
        max_age=cookie_max_age,
        path="/",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(deps.get_db),
):
    """
    Refresh access token using httpOnly cookie refresh token.
    Returns new access token and rotates refresh token cookie.
    """
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify refresh token
    try:
        payload = auth.decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from token
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = auth.create_access_token(
        subject=user.id,
        role=user.role or "student",
        expires_delta=access_token_expires,
    )

    # Rotate refresh token (security best practice)
    new_refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = auth.create_access_token(
        subject=user.id,
        role=user.role or "student",
        expires_delta=new_refresh_token_expires,
        token_type="refresh"
    )

    # Update refresh token cookie
    cookie_max_age = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=new_refresh_token,
        httponly=True,
        secure=ENVIRONMENT == "production",
        samesite="lax",
        max_age=cookie_max_age,
        path="/",
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(response: Response):
    """
    Logout user by clearing refresh token cookie.
    Client should also clear in-memory access token.
    """
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=ENVIRONMENT == "production",
        samesite="lax",
    )
    return {"message": "Successfully logged out"}


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user_in: UserCreate,
    db: Session = Depends(deps.get_db),
):
    """
    Public self-registration.

    The role is ALWAYS set to "student" regardless of request content.
    Accepting a role from an untrusted client would allow self-elevation
    to admin or faculty.
    """
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists.",
        )
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=auth.get_password_hash(user_in.password),
        role="student",          # Hard-coded: public registration is always student
        is_active=True,          # New accounts are active by default; only admins can deactivate
        is_superuser=False,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/me", response_model=UserOut)
def get_current_profile(
    current_user: User = Depends(deps.get_current_user),
):
    """
    Return the authenticated user's own profile.
    """
    return current_user


@router.put("/me", response_model=UserOut)
def update_current_profile(
    payload: UserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Update authenticated user's own profile.

    Only username, email, and password may be changed here.
    Role and active-status changes require an admin action.
    """
    if payload.username is not None:
        existing = db.query(User).filter(
            User.username == payload.username, User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken.")
        current_user.username = payload.username

    if payload.email is not None:
        existing = db.query(User).filter(
            User.email == payload.email, User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
        current_user.email = payload.email

    if payload.password:
        current_user.hashed_password = auth.get_password_hash(payload.password)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


# ---------------------------------------------------------------------------
# Admin-only: role and account management
# ---------------------------------------------------------------------------

@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    dependencies=[Depends(deps.require_role(["admin"]))],
)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(["admin"])),
):
    """
    Admin-only: update role, active status, or superuser flag for any account.
    This is the ONLY legitimate path for role changes.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    old_role = user.role
    old_is_superuser = user.is_superuser

    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_superuser is not None:
        user.is_superuser = payload.is_superuser

    db.add(user)
    db.commit()
    db.refresh(user)

    # Best-effort audit log. Must never roll back the user update.
    try:
        audit_entry = AuditLog(
            user_id=current_user.id,
            user_role=current_user.role,
            action_type="USER_ROLE_MODIFIED",
            affected_student_id=str(user.id),
            details=json.dumps(
                {
                    "target_id": user.id,
                    "old": {"role": old_role, "is_superuser": old_is_superuser},
                    "new": {"role": user.role, "is_superuser": user.is_superuser},
                }
            ),
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit_entry)
        db.commit()
    except Exception:
        logger.exception("Audit log write failed — security event unrecorded")
        db.rollback()
        # Do not re-raise — audit failure should not break the auth flow,
        # but it must be logged to an external system in production

    return user
