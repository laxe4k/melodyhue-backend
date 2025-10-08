from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr
    created_at: datetime
    last_login_at: datetime | None
    avatar_url: str | None = None

    class Config:
        from_attributes = True


class UpdateUsernameIn(BaseModel):
    username: str = Field(min_length=3, max_length=80)


class UpdateEmailIn(BaseModel):
    email: EmailStr


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class TwoFASetupOut(BaseModel):
    secret: str
    otpauth_url: str


class TwoFAVerifyIn(BaseModel):
    code: str
