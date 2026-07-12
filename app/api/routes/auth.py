from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_auth_service, require_auth
from app.api.schemas.auth import (
    AuthStatusResponse,
    AuthUserResponse,
    LoginRequest,
    LoginResponse,
)
from app.services.auth import AuthService, AuthUser

router = APIRouter(prefix="/auth")


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(auth_service: AuthService = Depends(get_auth_service)) -> AuthStatusResponse:
    return AuthStatusResponse(enabled=auth_service.enabled)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    token = auth_service.login(username=payload.username, password=payload.password)
    return LoginResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_at=token.expires_at,
        user=_user_response(token.user),
    )


@router.get("/me", response_model=AuthUserResponse)
def me(user: AuthUser = Depends(require_auth)) -> AuthUserResponse:
    return _user_response(user)


def _user_response(user: AuthUser) -> AuthUserResponse:
    return AuthUserResponse(
        user_id=user.user_id,
        username=user.username,
        display_name=user.display_name,
    )
