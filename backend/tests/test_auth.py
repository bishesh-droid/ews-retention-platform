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

    def test_register_duplicate_username_returns_409(self, client: TestClient, test_user: User):
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
        assert "username" in response.json()["error"]["message"].lower() or \
               "already exists" in response.json()["error"]["message"].lower()

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

    def test_login_valid_credentials_returns_tokens(self, client: TestClient, test_user: User):
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

    def test_login_wrong_password_returns_401(self, client: TestClient, test_user: User):
        """POST /auth/login — wrong password returns 401"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser",
                "password": "wrongpassword",
            },
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["error"]["message"].lower() or \
               "password" in response.json()["error"]["message"].lower()


class TestAuthLogout:
    """Test user logout endpoint with token revocation (SEC-4)."""

    def test_logout_revokes_access_token(self, client: TestClient, test_user: User, db_session: Session):
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
        from backend.config import SECRET_KEY, ALGORITHM, EWS_TOKEN_AUDIENCE, EWS_SERVICE_NAME

        payload = pyjwt.decode(
            access_token, SECRET_KEY, algorithms=[ALGORITHM],
            audience=EWS_TOKEN_AUDIENCE, issuer=EWS_SERVICE_NAME,
        )
        token_jti = payload.get("jti")
        
        revoked = db_session.query(RevokedToken).filter(RevokedToken.jti == token_jti).first()
        assert revoked is not None, "Token should be in revocation blocklist after logout"


class TestAuthRefresh:
    """Test token refresh endpoint."""

    def test_refresh_valid_token_returns_new_access_token(self, client: TestClient, test_user: User):
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
