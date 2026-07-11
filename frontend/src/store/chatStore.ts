import { create } from "zustand";

import type { SourceCitation } from "@/types/api";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  sources?: SourceCitation[];
  pending?: boolean;
  status?: string;
  warning?: string;
};

type ChatState = {
  messages: ChatMessage[];
  activeSource: SourceCitation | null;
  selectedSourceIds: string[];
  activeSessionId: string | null;
  isStreaming: boolean;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  clear: () => void;
  setMessages: (messages: ChatMessage[]) => void;
  setActiveSessionId: (sessionId: string | null) => void;
  setStreaming: (streaming: boolean) => void;
  setActiveSource: (source: SourceCitation | null) => void;
  setSelectedSourceIds: (sourceIds: string[]) => void;
  toggleSelectedSource: (sourceId: string) => void;
};

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  activeSource: null,
  selectedSourceIds: [],
  activeSessionId: null,
  isStreaming: false,
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateMessage: (id, patch) =>
    set((state) => ({
      messages: state.messages.map((message) => (message.id === id ? { ...message, ...patch } : message)),
    })),
  clear: () => set({ messages: [], activeSource: null }),
  setMessages: (messages) => set({ messages, activeSource: null }),
  setActiveSessionId: (activeSessionId) => set({ activeSessionId, activeSource: null }),
  setStreaming: (isStreaming) => set({ isStreaming }),
  setActiveSource: (source) => set({ activeSource: source }),
  setSelectedSourceIds: (selectedSourceIds) => set({ selectedSourceIds }),
  toggleSelectedSource: (sourceId) =>
    set((state) => ({
      selectedSourceIds: state.selectedSourceIds.includes(sourceId)
        ? state.selectedSourceIds.filter((id) => id !== sourceId)
        : [...state.selectedSourceIds, sourceId],
    })),
}));
