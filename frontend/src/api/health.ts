import { apiRequest } from "@/api/client";
import type { HealthResponse } from "@/types/api";

export function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health");
}
