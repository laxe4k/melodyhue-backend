from datetime import datetime
from pydantic import BaseModel, Field


class RoleUpdateIn(BaseModel):
    role: str = Field(pattern="^(user|moderator|admin)$")


class AdminStatsOut(BaseModel):
    users_count: int
    overlays_count: int
    moderators_count: int
    admins_count: int
    active_2fa_count: int
    last_user_registered_at: datetime | None = None


class UserListItem(BaseModel):
    id: str
    username: str
    email: str
    role: str
    created_at: datetime
    last_login_at: datetime | None = None

    class Config:
        from_attributes = True


class UserListOut(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    page_size: int


class WarnUserIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class BanUserIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    # None = permanent ban
    until: datetime | None = None
