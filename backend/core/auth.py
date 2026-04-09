from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

import bcrypt
from jose import jwt

from backend.config import SECRET_KEY, ALGORITHM


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
      - type  : token type ("access" or "refresh")

    Embedding role in the token means authorization checks do not require
    an extra DB round-trip and the role cannot be forged via HTTP headers.

    Args:
        subject: User ID to encode in token
        role: User role (default: "student")
        expires_delta: Token lifetime (default: 15 minutes)
        token_type: Token purpose ("access" or "refresh")
    """
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role.lower(),
        "type": token_type,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT string to decode

    Returns:
        Decoded token payload dict

    Raises:
        jwt.JWTError: If token is invalid or expired
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
