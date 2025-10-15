from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    username_or_email: str
    password: str
    totp: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginStep1Out(BaseModel):
    requires_2fa: bool
    ticket: str | None = None


class Login2FAIn(BaseModel):
    ticket: str
    totp: str


class LoginTokensOut(TokenPair):
    requires_2fa: bool = False
    ticket: str | None = None
    role: str = "user"
    user_id: str


class AuthSuccessOut(TokenPair):
    user_id: str
    role: str = "user"


class RefreshIn(BaseModel):
    refresh_token: str | None = None


class ForgotPwdIn(BaseModel):
    email: EmailStr


class ResetPwdIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class TwoFADisableConfirmIn(BaseModel):
    token: str
