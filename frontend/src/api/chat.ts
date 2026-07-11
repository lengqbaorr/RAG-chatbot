import { API_BASE_URL, ApiError, apiRequest } from "@/api/client";
import type {
  ApiErrorPayload,
  ChatRequest,
  ChatResponse,
  ChatSession,
  ChatSessionDetailResponse,
  ChatSessionListResponse,
  ChatStreamEvent,
} from "@/types/api";

export function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  return apiRequest<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listChatSessions(): Promise<ChatSessionListResponse> {
  return apiRequest<ChatSessionListResponse>("/chat/sessions");
}

export function getChatSession(sessionId: string): Promise<ChatSessionDetailResponse> {
  return apiRequest<ChatSessionDetailResponse>(`/chat/sessions/${sessionId}`);
}

export function createChatSession(payload: {
  title?: string;
  selected_source_ids?: string[];
}): Promise<ChatSession> {
  return apiRequest<ChatSession>("/chat/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateChatSession({
  sessionId,
  ...payload
}: {
  sessionId: string;
  title?: string;
  selected_source_ids?: string[];
}): Promise<ChatSession> {
  return apiRequest<ChatSession>(`/chat/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteChatSession(sessionId: string): Promise<void> {
  return apiRequest<void>(`/chat/sessions/${sessionId}`, {
    method: "DELETE",
    skipJson: true,
  });
}

type ChatStreamHandlers = {
  onStart?: () => void;
  onDelta: (text: string) => void;
  onComplete: (response: ChatResponse) => void;
};

export async function streamChatMessage(
  payload: ChatRequest,
  handlers: ChatStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    let body: ApiErrorPayload | undefined;
    try {
      body = (await response.json()) as ApiErrorPayload;
    } catch {
      body = undefined;
    }
    throw new ApiError(
      body?.error?.message ?? `Request failed with HTTP ${response.status}`,
      response.status,
      body?.error?.code,
      body?.error?.details,
    );
  }
  if (!response.body) {
    throw new ApiError("Streaming response has no body", 502, "empty_stream");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed = false;

  const processFrame = (frame: string) => {
    const lines = frame.split("\n");
    const eventName = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
    const dataText = lines
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!eventName || !dataText) return;

    const event = { event: eventName, data: JSON.parse(dataText) } as ChatStreamEvent;
    if (event.event === "start") handlers.onStart?.();
    if (event.event === "delta") handlers.onDelta(event.data.text);
    if (event.event === "complete") {
      completed = true;
      handlers.onComplete(event.data);
    }
    if (event.event === "error") {
      throw new ApiError(event.data.message, 500, event.data.code);
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer = (buffer + decoder.decode(value, { stream: !done })).replace(/\r\n/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary >= 0) {
        processFrame(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        boundary = buffer.indexOf("\n\n");
      }
      if (done) break;
    }
    if (buffer.trim()) processFrame(buffer);
    if (!completed) {
      throw new ApiError("Stream ended before completion", 502, "incomplete_stream");
    }
  } finally {
    reader.releaseLock();
  }
}
