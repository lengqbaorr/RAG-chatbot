import { create } from "zustand";

import type { SourceCitation } from "@/types/api";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  sources?: SourceCitation[];
  pending?: boolean;
  warning?: string;
};

type ChatState = {
  messages: ChatMessage[];
  activeSource: SourceCitation | null;
  selectedSourceIds: string[];
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  clear: () => void;
  setActiveSource: (source: SourceCitation | null) => void;
  setSelectedSourceIds: (sourceIds: string[]) => void;
  toggleSelectedSource: (sourceId: string) => void;
};

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  activeSource: null,
  selectedSourceIds: [],
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateMessage: (id, patch) =>
    set((state) => ({
      messages: state.messages.map((message) => (message.id === id ? { ...message, ...patch } : message)),
    })),
  clear: () => set({ messages: [], activeSource: null }),
  setActiveSource: (source) => set({ activeSource: source }),
  setSelectedSourceIds: (selectedSourceIds) => set({ selectedSourceIds }),
  toggleSelectedSource: (sourceId) =>
    set((state) => ({
      selectedSourceIds: state.selectedSourceIds.includes(sourceId)
        ? state.selectedSourceIds.filter((id) => id !== sourceId)
        : [...state.selectedSourceIds, sourceId],
    })),
}));
