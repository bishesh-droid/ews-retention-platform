from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[int] = None
    role: Optional[str] = None


class UserBase(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    department: Optional[str] = None


class UserCreate(UserBase):
    """Schema for public self-registration.

    `role` is intentionally absent: the registration endpoint always
    assigns the "student" role.  Accepting a role from an untrusted
    client would allow anyone to self-elevate to admin/faculty.
    """
    username: str
    email: EmailStr
    password: str


class UserUpdate(UserBase):
    """Fields an authenticated user may update on their own profile.

    `role` and `is_active` are intentionally absent: changing either
    requires an admin action (a separate admin-only endpoint), not a
    self-service call.  Allowing self-role-update is a privilege
    escalation vulnerability.
    """
    password: Optional[str] = None


class AdminUserUpdate(BaseModel):
    """Fields that only an admin may change on any user account."""
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"student", "faculty", "admin", "retention team"}
        if v.lower() not in allowed:
            raise ValueError(f"role must be one of: {allowed}")
        return v.lower()


class UserOut(UserBase):
    id: int
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
