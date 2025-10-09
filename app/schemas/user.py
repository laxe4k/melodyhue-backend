from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr
    role: str = "user"
    created_at: datetime
    last_login_at: datetime | None
    avatar_url: str | None = None
    # Couleur par défaut des overlays
    default_overlay_color: str | None = None

    class Config:
        from_attributes = True


class PublicUserOut(BaseModel):
    id: str
    username: str
    created_at: datetime
    avatar_url: str | None = None
    default_overlay_color: str | None = None

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
