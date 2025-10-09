from pydantic import BaseModel, Field


class SpotifyCredentialsIn(BaseModel):
    client_id: str | None = Field(default=None, description="Spotify Client ID")
    client_secret: str | None = Field(default=None, description="Spotify Client Secret")
    refresh_token: str | None = Field(default=None, description="Spotify Refresh Token")


class SpotifyCredentialsStatusOut(BaseModel):
    has_client_id: bool
    has_client_secret: bool
    has_refresh_token: bool
