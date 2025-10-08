from datetime import datetime
from pydantic import BaseModel, Field


class OverlayCreateIn(BaseModel):
    name: str = Field(default="Overlay", min_length=1, max_length=120)
    color_hex: str = Field(default="#25d865", pattern=r"^#[0-9a-fA-F]{6}$")


class OverlayUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    color_hex: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class OverlayOut(BaseModel):
    id: str
    name: str
    color_hex: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
