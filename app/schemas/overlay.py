from datetime import datetime
from pydantic import BaseModel, Field


class OverlayCreateIn(BaseModel):
    name: str = Field(default="Overlay", min_length=1, max_length=120)
    # Template libre: n'importe quelle chaîne (max 64 pour éviter les abus)
    template: str = Field(default="classic", min_length=1, max_length=64)


class OverlayUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    # Template libre
    template: str | None = Field(default=None, min_length=1, max_length=64)


class OverlayOut(BaseModel):
    id: str
    name: str
    template: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OverlayModerationOut(BaseModel):
    id: str
    owner_id: str
    owner_username: str | None = None
    name: str
    template: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
