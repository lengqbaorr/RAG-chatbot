import { apiRequest } from "@/api/client";
import type { ChatRequest, ChatResponse } from "@/types/api";

export function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
