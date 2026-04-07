from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
import json

from backend.database import User
from backend.api import deps
from backend.core import auth
from backend.database.models.audit import AuditLog
from backend.schemas.auth import (
    Token,
    UserOut,
    UserCreate,
    UserUpdate,
    AdminUserUpdate,
)
from backend.utils.api import success_response, error_response
from backend.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    OAuth2 token login — returns a Bearer JWT for use in subsequent requests.
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

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": auth.create_access_token(
            subject=user.id,
            role=user.role or "student",
            expires_delta=access_token_expires,
        ),
        "token_type": "bearer",
    }


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
        db.rollback()

    return user
