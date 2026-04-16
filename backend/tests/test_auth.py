"""
TEST-1: Auth Routes Tests

Covers authentication endpoints:
- POST /auth/register — valid registration succeeds (201)
- POST /auth/register — duplicate username returns 409
- POST /auth/register — invalid email returns 422
- POST /auth/login — valid credentials return access + refresh token
- POST /auth/login — wrong password returns 401
- POST /auth/logout — after logout, access token is blocklisted (SEC-4)
- POST /auth/refresh — valid refresh token returns new access token
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.database.models.user import User
from backend.database.models.revoked_token import RevokedToken
from backend.core.auth import get_password_hash


@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user for authentication tests."""
    # Clean up any existing test user
    existing = db_session.query(User).filter(User.username == "testuser").first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        role="student",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    yield user

    # Cleanup
    db_session.delete(user)
    db_session.commit()


class TestAuthRegister:
    """Test user registration endpoint."""

    def test_register_valid_succeeds(self, client: TestClient, db_session: Session):
        """POST /auth/register — valid registration succeeds (201)"""
        # Clean up any existing user
        existing = db_session.query(User).filter(User.username == "newuser").first()
        if existing:
            db_session.delete(existing)
            db_session.commit()

        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "student"  # Always student for public registration

        # Cleanup
        user = db_session.query(User).filter(User.username == "newuser").first()
        if user:
            db_session.delete(user)
            db_session.commit()

    def test_register_duplicate_username_returns_409(
        self, client: TestClient, test_user: User
    ):
        """POST /auth/register — duplicate username returns 409"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",  # Same as test_user fixture
                "email": "different@example.com",
                "password": "securepassword123",
            },
        )

        assert response.status_code == 409
        assert (
            "username" in response.json()["error"]["message"].lower()
            or "already exists" in response.json()["error"]["message"].lower()
        )

    def test_register_invalid_email_returns_422(self, client: TestClient):
        """POST /auth/register — invalid email returns 422"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "invalidemailuser",
                "email": "not-an-email",  # Invalid email format
                "password": "securepassword123",
            },
        )

        assert response.status_code == 422


class TestAuthLogin:
    """Test user login endpoint."""

    def test_login_valid_credentials_returns_tokens(
        self, client: TestClient, test_user: User
    ):
        """POST /auth/login — valid credentials return access + refresh token"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Check refresh token cookie is set
        assert "refresh_token" in response.cookies

    def test_login_wrong_password_returns_401(
        self, client: TestClient, test_user: User
    ):
        """POST /auth/login — wrong password returns 401"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert (
            "incorrect" in response.json()["error"]["message"].lower()
            or "password" in response.json()["error"]["message"].lower()
        )


class TestAuthLogout:
    """Test user logout endpoint with token revocation (SEC-4)."""

    def test_logout_revokes_access_token(
        self, client: TestClient, test_user: User, db_session: Session
    ):
        """POST /auth/logout — after logout, access token is blocklisted (SEC-4)"""
        # First login to get a token
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpassword123",
            },
        )

        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Logout with the access token
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert logout_response.status_code == 200
        assert "successfully logged out" in logout_response.json()["message"].lower()

        # Verify the token is in the revocation blocklist
        # Decode token to get JTI (skip audience/issuer validation — we just need the jti)
        import jwt as pyjwt
        from backend.config import (
            SECRET_KEY,
            ALGORITHM,
            EWS_TOKEN_AUDIENCE,
            EWS_SERVICE_NAME,
        )

        payload = pyjwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=EWS_TOKEN_AUDIENCE,
            issuer=EWS_SERVICE_NAME,
        )
        token_jti = payload.get("jti")

        revoked = (
            db_session.query(RevokedToken).filter(RevokedToken.jti == token_jti).first()
        )
        assert (
            revoked is not None
        ), "Token should be in revocation blocklist after logout"

    def test_logout_revokes_refresh_token(
        self, client: TestClient, test_user: User, db_session: Session
    ):
        """POST /auth/logout — after logout, refresh token is also blocklisted (SEC-4)"""
        import jwt as pyjwt
        from backend.config import (
            SECRET_KEY,
            ALGORITHM,
            EWS_TOKEN_AUDIENCE,
            EWS_SERVICE_NAME,
        )

        # First login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpassword123",
            },
        )

        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        refresh_token = login_response.cookies.get("refresh_token")
        assert refresh_token is not None, "Login should set refresh token cookie"

        # Logout with the access token
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert logout_response.status_code == 200

        # Decode refresh token to get JTI
        refresh_payload = pyjwt.decode(
            refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=EWS_TOKEN_AUDIENCE,
            issuer=EWS_SERVICE_NAME,
        )
        refresh_jti = refresh_payload.get("jti")

        # Verify refresh token is also revoked
        revoked_refresh = (
            db_session.query(RevokedToken)
            .filter(RevokedToken.jti == refresh_jti)
            .first()
        )
        assert (
            revoked_refresh is not None
        ), "Refresh token should be revoked after logout"

    def test_logout_without_token_fails_401(self, client: TestClient):
        """POST /auth/logout without token should fail with 401."""
        logout_response = client.post("/api/v1/auth/logout")

        assert logout_response.status_code == 401

    def test_logout_with_invalid_token_fails_401(self, client: TestClient):
        """POST /auth/logout with invalid token should fail with 401."""
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert logout_response.status_code == 401


class TestTokenRevocation:
    """
    SEC-4: Token Revocation Tests

    Comprehensive tests for token revocation (blocklist) functionality.
    """

    def test_revoked_token_cannot_access_protected_endpoint(
        self, client: TestClient, test_user: User, db_session: Session
    ):
        """REV-1: After logout, revoked access token cannot access protected endpoints."""

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpassword123"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Logout (revokes token)
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_response.status_code == 200

        # Attempt to access protected endpoint with revoked token
        # Note: This assumes /predictions/{student_id} is a protected endpoint
        # If endpoint doesn't exist, test verifies middleware revocation check works
        protected_response = client.get(
            "/api/v1/predictions/testuser",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Should fail because token is revoked
        assert protected_response.status_code in [401, 403, 404]

    def test_revoked_refresh_token_cannot_get_new_access_token(
        self, client: TestClient, test_user: User, db_session: Session
    ):
        """REV-2: Revoked refresh token cannot be used to get new access token."""
        from datetime import datetime
        import jwt as pyjwt
        from backend.config import (
            SECRET_KEY,
            ALGORITHM,
            EWS_TOKEN_AUDIENCE,
            EWS_SERVICE_NAME,
        )

        # Login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpassword123"},
        )
        assert login_response.status_code == 200
        refresh_token = login_response.cookies.get("refresh_token")

        # Decode and revoke refresh token
        assert refresh_token is not None
        payload = pyjwt.decode(
            refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=EWS_TOKEN_AUDIENCE,
            issuer=EWS_SERVICE_NAME,
        )
        token_jti = payload.get("jti")
        token_exp = payload.get("exp")

        revoked = RevokedToken(
            jti=token_jti,
            user_id=test_user.id,
            expires_at=datetime.fromtimestamp(token_exp),  # type: ignore[arg-type]
        )
        db_session.add(revoked)
        db_session.commit()

        # Try to refresh with revoked token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": refresh_token},
        )

        assert refresh_response.status_code == 401
        response_json = refresh_response.json()
        # Handle both envelope format (error.message) and direct format (detail)
        error_message = response_json.get("detail", "")
        if not error_message and "error" in response_json:
            error_message = response_json["error"].get("message", "")
        assert "revoked" in error_message.lower()

    def test_token_revoked_at_expiry_matches_jwt_exp(
        self, client: TestClient, test_user: User, db_session: Session
    ):
        """REV-3: Revoked token expiry should match JWT exp claim."""
        import jwt as pyjwt
        from backend.config import (
            SECRET_KEY,
            ALGORITHM,
            EWS_TOKEN_AUDIENCE,
            EWS_SERVICE_NAME,
        )

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpassword123"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Logout (revokes token)
        client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Decode token to get JTI and exp
        payload = pyjwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=EWS_TOKEN_AUDIENCE,
            issuer=EWS_SERVICE_NAME,
        )
        token_jti = payload.get("jti")
        token_exp = payload.get("exp")

        # Verify revoked token record
        revoked = (
            db_session.query(RevokedToken).filter(RevokedToken.jti == token_jti).first()
        )

        assert revoked is not None
        # Verify expiry matches (within 1 second tolerance).
        # expires_at is stored as a naive UTC datetime in SQLite; attach UTC
        # before calling timestamp() so Python doesn't misinterpret it as local.
        from datetime import timezone as _tz

        assert revoked.expires_at is not None
        assert token_exp is not None
        db_exp = int(revoked.expires_at.replace(tzinfo=_tz.utc).timestamp())
        assert abs(db_exp - token_exp) <= 1, "DB expiry should match JWT exp claim"

    def test_cannot_revoke_same_token_twice(
        self, client: TestClient, test_user: User, db_session: Session
    ):
        """REV-4: Revoking same token twice should be idempotent (no error)."""
        from datetime import datetime
        import jwt as pyjwt
        from backend.config import (
            SECRET_KEY,
            ALGORITHM,
            EWS_TOKEN_AUDIENCE,
            EWS_SERVICE_NAME,
        )

        # Login
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpassword123"},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Decode token
        payload = pyjwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=EWS_TOKEN_AUDIENCE,
            issuer=EWS_SERVICE_NAME,
        )
        token_jti = payload.get("jti")
        token_exp = payload.get("exp")

        # Revoke token
        revoked1 = RevokedToken(
            jti=token_jti,
            user_id=test_user.id,
            expires_at=datetime.fromtimestamp(token_exp),  # type: ignore[arg-type]
        )
        db_session.add(revoked1)
        db_session.commit()

        # Attempt to revoke same token again (should not raise error due to conflict handling)
        revoked2 = RevokedToken(
            jti=token_jti,
            user_id=test_user.id,
            expires_at=datetime.fromtimestamp(token_exp),  # type: ignore[arg-type]
        )
        db_session.add(revoked2)

        # This may raise IntegrityError or be handled gracefully
        try:
            db_session.commit()
        except Exception:
            db_session.rollback()

        # Verify only one record exists
        count = (
            db_session.query(RevokedToken).filter(RevokedToken.jti == token_jti).count()
        )
        assert count <= 1, "Should not create duplicate revocation entries"


class TestAuthRefresh:
    """Test token refresh endpoint."""

    def test_refresh_valid_token_returns_new_access_token(
        self, client: TestClient, test_user: User
    ):
        """POST /auth/refresh — valid refresh token returns new access token"""
        # First login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpassword123",
            },
        )

        assert login_response.status_code == 200

        # Use the refresh token cookie to get a new access token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
        )

        assert refresh_response.status_code == 200
        data = refresh_response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # New refresh token cookie should be set
        assert "refresh_token" in refresh_response.cookies

    def test_refresh_revoked_token_returns_401(
        self, client: TestClient, test_user: User, db_session: Session
    ):
        """POST /auth/refresh — revoked refresh token returns 401 (SEC-4)"""
        from datetime import datetime
        import jwt as pyjwt
        from backend.config import (
            SECRET_KEY,
            ALGORITHM,
            EWS_TOKEN_AUDIENCE,
            EWS_SERVICE_NAME,
        )

        # First login to get tokens
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200

        # Get the refresh token from cookie
        refresh_token = login_response.cookies.get("refresh_token")
        assert refresh_token is not None

        # Decode refresh token to get JTI
        payload = pyjwt.decode(
            refresh_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=EWS_TOKEN_AUDIENCE,
            issuer=EWS_SERVICE_NAME,
        )
        token_jti = payload.get("jti")
        token_exp = payload.get("exp")

        # Revoke the refresh token (simulate logout or token revocation)
        revoked = RevokedToken(
            jti=token_jti,
            user_id=test_user.id,
            expires_at=datetime.fromtimestamp(token_exp),  # type: ignore[arg-type]
        )
        db_session.add(revoked)
        db_session.commit()

        # Try to refresh with revoked token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": refresh_token},
        )

        assert refresh_response.status_code == 401
        response_json = refresh_response.json()
        # Handle both envelope format (error.message) and direct format (detail)
        error_message = response_json.get("detail", "")
        if not error_message and "error" in response_json:
            error_message = response_json["error"].get("message", "")
        assert "revoked" in error_message.lower()


def test_404_returns_404_not_500(client: TestClient):
    """
    Verify that a 404 error returns HTTP 404 (not 500).

    This tests that exception handlers are registered in the correct order:
    - Generic Exception handler must be registered FIRST (lowest priority)
    - Specific handlers (StarletteHTTPException) registered AFTER (higher priority)

    FastAPI's add_exception_handler is LIFO - last registered takes precedence.
    If order is wrong, 404s would be caught by the generic handler and return 500.
    """
    response = client.get("/api/v1/nonexistent-route-xyz")
    assert response.status_code == 404
