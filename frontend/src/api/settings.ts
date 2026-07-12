import { apiRequest } from "@/api/client";
import type { RuntimeSettingsResponse, RuntimeSettingsUpdate } from "@/types/api";

export function getRuntimeSettings(): Promise<RuntimeSettingsResponse> {
  return apiRequest<RuntimeSettingsResponse>("/settings");
}

export function updateRuntimeSettings(
  payload: RuntimeSettingsUpdate,
): Promise<RuntimeSettingsResponse> {
  return apiRequest<RuntimeSettingsResponse>("/settings", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function resetRuntimeSettings(): Promise<RuntimeSettingsResponse> {
  return apiRequest<RuntimeSettingsResponse>("/settings/reset", {
    method: "POST",
  });
}
