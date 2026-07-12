import type { ApiErrorPayload } from "@/types/api";
import { useAuthStore } from "@/store/authStore";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: Record<string, unknown>;

  constructor(message: string, status: number, code = "api_error", details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type RequestOptions = RequestInit & {
  skipJson?: boolean;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = useAuthStore.getState().token;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let payload: ApiErrorPayload | undefined;
    try {
      payload = (await response.json()) as ApiErrorPayload;
    } catch {
      payload = undefined;
    }
    const error = payload?.error;
    if (response.status === 401) {
      useAuthStore.getState().logout();
    }
    throw new ApiError(
      error?.message ?? `Request failed with HTTP ${response.status}`,
      response.status,
      error?.code,
      error?.details,
    );
  }

  if (options.skipJson || response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
