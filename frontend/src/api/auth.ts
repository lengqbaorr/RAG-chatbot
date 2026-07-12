import { apiRequest } from "@/api/client";
import type { AuthStatusResponse, AuthUser, LoginResponse } from "@/types/api";

export function getAuthStatus(): Promise<AuthStatusResponse> {
  return apiRequest<AuthStatusResponse>("/auth/status");
}

export function login(payload: { username: string; password: string }): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCurrentUser(): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me");
}
