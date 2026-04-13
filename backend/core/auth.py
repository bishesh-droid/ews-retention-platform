from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import uuid

import bcrypt
import jwt as pyjwt
from jwt.exceptions import InvalidTokenError

from backend.config import SECRET_KEY, ALGORITHM, EWS_SERVICE_NAME, EWS_TOKEN_AUDIENCE


def create_access_token(
    subject: Union[str, Any],
    role: str = "student",
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access",
) -> str:
    """
    Create a signed JWT containing:
      - sub   : user ID (str)
      - role  : lowercased role string embedded at issue time
      - exp   : expiry timestamp
      - iat   : issued at timestamp
      - iss   : issuer (EWS_SERVICE_NAME)
      - aud   : audience (EWS_TOKEN_AUDIENCE)
      - jti   : unique token ID
      - nbf   : not before timestamp
      - type  : token type ("access" or "refresh")

    Embedding role in the token means authorization checks do not require
    an extra DB round-trip and the role cannot be forged via HTTP headers.

    Args:
        subject: User ID to encode in token
        role: User role (default: "student")
        expires_delta: Token lifetime (default: 15 minutes)
        token_type: Token purpose ("access" or "refresh")
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=15))
    to_encode = {
        "exp": expire,
        "iat": now,
        "sub": str(subject),
        "role": role.lower(),
        "type": token_type,
        "iss": EWS_SERVICE_NAME,
        "aud": EWS_TOKEN_AUDIENCE,
        "jti": str(uuid.uuid4()),
        "nbf": now,
    }
    return pyjwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT string to decode

    Returns:
        Decoded token payload dict

    Raises:
        InvalidTokenError: If token is invalid or expired
    """
    return pyjwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"require": ["exp", "iat", "sub", "jti", "iss", "aud", "nbf"]},
        audience=EWS_TOKEN_AUDIENCE,
        issuer=EWS_SERVICE_NAME,
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
