from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    username: str
    display_name: str


@dataclass(frozen=True)
class AuthToken:
    access_token: str
    token_type: str
    expires_at: datetime
    user: AuthUser
