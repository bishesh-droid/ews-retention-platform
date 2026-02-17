from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[int] = None

class UserBase(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    username: str
    email: EmailStr
    password: str
    role: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserOut(UserBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)
