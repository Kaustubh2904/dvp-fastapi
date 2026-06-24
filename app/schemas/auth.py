from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole
    company_id: Optional[int] = None
    is_active: Optional[bool] = True
    is_verified: Optional[bool] = False


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    role: Optional[UserRole] = None
    company_id: Optional[int] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OTPGenerateRequest(BaseModel):
    email: EmailStr


class OTPLoginRequest(BaseModel):
    email: EmailStr
    code: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class CompanyRegistrationRequest(BaseModel):
    company_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6)
    plan_name: str  # SMALL, MEDIUM, LARGE, CUSTOM