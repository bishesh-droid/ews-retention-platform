from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime, timezone
from typing import Optional
import json

import jwt as pyjwt

from backend.database import User
from backend.api import deps
from backend.core import auth
from backend.core.rate_limiting import limiter
from backend.database.models.audit import AuditLog
from backend.database.models.revoked_token import RevokedToken
from backend.schemas.auth import (
    Token,
    UserOut,
    UserCreate,
    UserUpdate,
    AdminUserUpdate,
)
from backend.config import ACCESS_TOKEN_EXPIRE_MINUTES, RATE_LIMIT_LOGIN, REDIS_URL
from redis.asyncio import Redis as AsyncRedis
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
    db: AsyncSession = Depends(deps.get_db_async),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    OAuth2 token login — returns a Bearer JWT and sets httpOnly refresh token cookie.
    """
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):  # type: ignore[arg-type]
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
        token_type="refresh",
    )

    # Set httpOnly cookie with refresh token
    cookie_max_age = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # seconds
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=cookie_max_age,
        path="/api/v1/auth/refresh",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(deps.get_db_async),
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

        # Check if refresh token has been revoked (SEC-4)
        token_jti = payload.get("jti")
        if token_jti:
            revoked_result = await db.execute(
                select(RevokedToken).where(RevokedToken.jti == token_jti)
            )
            if revoked_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from token
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
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

    # Revoke the old refresh token (proper RTR - Refresh Token Rotation)
    if token_jti:
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        revoked = RevokedToken(
            jti=token_jti,
            user_id=user.id,
            expires_at=expires_at,
        )
        db.add(revoked)
        await db.commit()
        # Also write to Redis for fast revocation check (O(1))
        try:
            redis_client = AsyncRedis.from_url(REDIS_URL, decode_responses=True)
            ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
            if ttl > 0:
                await redis_client.setex(f"jti:{token_jti}", ttl, "1")
            await redis_client.close()
        except Exception:
            # Log Redis failure but don't fail the refresh - DB is source of truth
            logger.warning(
                "Failed to write revoked token to Redis (RTR)", exc_info=True
            )

    # Rotate refresh token (security best practice)
    new_refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    new_refresh_token = auth.create_access_token(
        subject=user.id,
        role=user.role or "student",
        expires_delta=new_refresh_token_expires,
        token_type="refresh",
    )

    # Update refresh token cookie
    cookie_max_age = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=new_refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=cookie_max_age,
        path="/api/v1/auth/refresh",
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
    }


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(deps.get_db_async),
    current_user: User = Depends(deps.get_current_user_async),
    token: Optional[str] = Depends(oauth2_scheme),
):
    """
    Logout user by revoking the access token and clearing refresh token cookie.

    The token's JTI is added to the revocation blocklist, making the token
    invalid immediately even before its natural expiration (SEC-4).
    """
    if token:
        try:
            # Decode without verification to extract jti and exp
            unverified_payload = pyjwt.decode(
                token, key="", options={"verify_signature": False, "verify_exp": False}
            )
            token_jti = unverified_payload.get("jti")
            token_exp = unverified_payload.get("exp")

            if token_jti and token_exp:
                # Add token to revocation blocklist (use UTC timezone)
                expires_at = datetime.fromtimestamp(token_exp, tz=timezone.utc)
                revoked_token = RevokedToken(
                    jti=token_jti,
                    user_id=current_user.id,
                    expires_at=expires_at,
                )
                db.add(revoked_token)
                await db.commit()
                # Also write to Redis for fast revocation check (O(1))
                try:
                    redis_client = AsyncRedis.from_url(REDIS_URL, decode_responses=True)
                    ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
                    if ttl > 0:
                        await redis_client.setex(f"jti:{token_jti}", ttl, "1")
                    await redis_client.close()
                except Exception:
                    logger.warning(
                        "Failed to write revoked access token to Redis", exc_info=True
                    )
                logger.info(
                    f"Access token revoked for user {current_user.id}, jti={token_jti}"
                )
        except Exception as e:
            # Log but don't fail the logout if token revocation fails
            logger.warning(f"Failed to revoke access token during logout: {e}")
            await db.rollback()

    # Also revoke the refresh token if present
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token:
        try:
            # Decode refresh token without verification to extract jti and exp
            unverified_payload = pyjwt.decode(
                refresh_token,
                key="",
                options={"verify_signature": False, "verify_exp": False},
            )
            refresh_jti = unverified_payload.get("jti")
            refresh_exp = unverified_payload.get("exp")

            if refresh_jti and refresh_exp:
                # Add refresh token to revocation blocklist (use UTC timezone)
                expires_at = datetime.fromtimestamp(refresh_exp, tz=timezone.utc)
                revoked_refresh = RevokedToken(
                    jti=refresh_jti,
                    user_id=current_user.id,
                    expires_at=expires_at,
                )
                db.add(revoked_refresh)
                await db.commit()
                # Also write to Redis for fast revocation check (O(1))
                try:
                    redis_client = AsyncRedis.from_url(REDIS_URL, decode_responses=True)
                    ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
                    if ttl > 0:
                        await redis_client.setex(f"jti:{refresh_jti}", ttl, "1")
                    await redis_client.close()
                except Exception:
                    logger.warning(
                        "Failed to write revoked refresh token to Redis", exc_info=True
                    )
                logger.info(
                    f"Refresh token revoked for user {current_user.id}, jti={refresh_jti}"
                )
        except Exception as e:
            # Log but don't fail the logout if token revocation fails
            logger.warning(f"Failed to revoke refresh token during logout: {e}")
            await db.rollback()

    # Clear the refresh token cookie
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        path="/api/v1/auth/refresh",
        httponly=True,
        secure=True,
        samesite="strict",
    )
    return {"message": "Successfully logged out"}


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(deps.get_db_async),
):
    """
    Public self-registration.

    The role is ALWAYS set to "student" regardless of request content.
    Accepting a role from an untrusted client would allow self-elevation
    to admin or faculty.
    """
    result = await db.execute(select(User).where(User.username == user_in.username))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists.",
        )
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=auth.get_password_hash(user_in.password),
        role="student",  # Hard-coded: public registration is always student
        is_active=True,  # New accounts are active by default; only admins can deactivate
        is_superuser=False,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
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
        existing = (
            db.query(User)
            .filter(User.username == payload.username, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already taken."
            )
        current_user.username = payload.username

    if payload.email is not None:
        existing = (
            db.query(User)
            .filter(User.email == payload.email, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
            )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

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
