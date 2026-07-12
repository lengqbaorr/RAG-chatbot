from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Any

from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.services.auth.models import AuthToken, AuthUser


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return self.settings.auth_enabled

    def login(self, *, username: str, password: str) -> AuthToken:
        if not self.enabled:
            return self._issue_token(self.local_user())
        if not hmac.compare_digest(username, self.settings.auth_local_username):
            raise AuthenticationError("Invalid username or password")
        if not hmac.compare_digest(password, self.settings.auth_local_password):
            raise AuthenticationError("Invalid username or password")
        return self._issue_token(self.local_user())

    def verify_token(self, token: str | None) -> AuthUser:
        if not self.enabled:
            return self.local_user()
        if not token:
            raise AuthenticationError("Missing bearer token")
        try:
            payload_part, signature = token.split(".", maxsplit=1)
        except ValueError as exc:
            raise AuthenticationError("Invalid bearer token") from exc
        expected = self._sign(payload_part)
        if not hmac.compare_digest(signature, expected):
            raise AuthenticationError("Invalid bearer token")
        try:
            payload = json.loads(self._b64decode(payload_part))
        except (ValueError, json.JSONDecodeError) as exc:
            raise AuthenticationError("Invalid bearer token") from exc
        if int(payload.get("exp", 0)) < int(time.time()):
            raise AuthenticationError("Bearer token expired")
        return AuthUser(
            user_id=str(payload.get("sub") or "local"),
            username=str(payload.get("username") or self.settings.auth_local_username),
            display_name=str(payload.get("name") or "Local User"),
        )

    def local_user(self) -> AuthUser:
        return AuthUser(
            user_id="local",
            username=self.settings.auth_local_username,
            display_name="Local User",
        )

    def _issue_token(self, user: AuthUser) -> AuthToken:
        expires_at = datetime.utcnow() + timedelta(minutes=self.settings.auth_token_ttl_minutes)
        payload = {
            "sub": user.user_id,
            "username": user.username,
            "name": user.display_name,
            "exp": int(expires_at.timestamp()),
        }
        payload_part = self._b64encode(payload)
        return AuthToken(
            access_token=f"{payload_part}.{self._sign(payload_part)}",
            token_type="bearer",
            expires_at=expires_at,
            user=user,
        )

    def _sign(self, payload_part: str) -> str:
        digest = hmac.new(
            self.settings.auth_secret_key.encode("utf-8"),
            payload_part.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    @staticmethod
    def _b64encode(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _b64decode(value: str) -> str:
        padded = value + "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
