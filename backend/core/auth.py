from datetime import datetime, timedelta
from typing import Any, Optional, Union

from jose import jwt
from passlib.context import CryptContext

from backend.config import SECRET_KEY, ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    subject: Union[str, Any],
    role: str = "student",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT containing:
      - sub  : user ID (str)
      - role : lowercased role string embedded at issue time
      - exp  : expiry timestamp

    Embedding role in the token means authorization checks do not require
    an extra DB round-trip and the role cannot be forged via HTTP headers.
    """
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role.lower(),
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
