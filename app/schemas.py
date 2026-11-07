from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: Literal["user", "premium"]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LinkCreate(BaseModel):
    original_url: HttpUrl
    expires_at: datetime | None = None
    max_clicks: int | None = Field(default=None, ge=1)

    @field_validator("expires_at")
    @classmethod
    def _to_utc(cls, v: datetime | None):
        if v is None:
            return v
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        v = v.astimezone(timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("expires_at должен быть в будущем")
        return v


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_url: str
    code: str
    expires_at: datetime | None
    clicks: int
    max_clicks: int | None
    created_at: datetime
    is_active: bool
