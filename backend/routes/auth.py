from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from backend.database import User
from backend.api import deps
from backend.core import auth
from backend.schemas.auth import Token, UserOut, UserCreate, UserUpdate
from backend.utils.api import success_response, error_response
from backend.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()

@router.post("/login", response_model=Token)
def login(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": auth.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.post("/register", response_model=UserOut)
def register(
    user_in: UserCreate,
    db: Session = Depends(deps.get_db)
):
    """
    Create a new user.
    """
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=auth.get_password_hash(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/me")
def get_current_profile(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Get the authenticated user's profile, role, and preferences.
    """
    prefs = current_user.preferences or {}
    data = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "preferences": prefs,
    }
    return success_response(data, message="Current user profile")


@router.put("/me")
def update_current_profile(
    payload: UserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Update authenticated user's profile fields and preferences.
    """
    # Basic profile updates
    if payload.username is not None:
        current_user.username = payload.username
    if payload.email is not None:
        current_user.email = payload.email
    if payload.role is not None:
        current_user.role = payload.role
    if payload.is_active is not None:
        current_user.is_active = payload.is_active

    # Preferences can be passed in payload.model_extra or a dedicated key; here we accept `preferences` from model_extra
    extra = getattr(payload, "model_extra", {}) or {}
    prefs = extra.get("preferences")
    if isinstance(prefs, dict):
        current_user.preferences = {**(current_user.preferences or {}), **prefs}

    # Optional password change
    if payload.password:
        current_user.hashed_password = auth.get_password_hash(payload.password)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    data = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "preferences": current_user.preferences or {},
    }
    return success_response(data, message="Profile updated")
