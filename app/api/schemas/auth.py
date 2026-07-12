from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuthStatusResponse(BaseModel):
    enabled: bool


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class AuthUserResponse(BaseModel):
    user_id: str
    username: str
    display_name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    user: AuthUserResponse
