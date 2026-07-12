from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_settings_service
from app.api.schemas.settings import SettingsResponse, SettingsUpdateRequest
from app.services.settings import SettingsService, UserSettingsUpdate

router = APIRouter(prefix="/settings")


@router.get("", response_model=SettingsResponse)
def get_runtime_settings(
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    return SettingsResponse(**settings_service.get_runtime_settings().__dict__)


@router.patch("", response_model=SettingsResponse)
def update_runtime_settings(
    payload: SettingsUpdateRequest,
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    updated = settings_service.update_settings(
        UserSettingsUpdate(**payload.model_dump(exclude_unset=True))
    )
    return SettingsResponse(**updated.__dict__)


@router.post("/reset", response_model=SettingsResponse)
def reset_runtime_settings(
    settings_service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    return SettingsResponse(**settings_service.reset_settings().__dict__)
