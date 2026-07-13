import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { RuntimeSettingsResponse } from "@/types/api";

export type ThemeMode = "light" | "dark" | "system";
export type RetrievalStrategy = "dense" | "parent_child";

type SettingsState = {
  theme: ThemeMode;
  retrievalStrategy: RetrievalStrategy;
  topK: number;
  fetchK: number;
  minScore: number;
  temperature: number;
  maxTokens: number;
  model: string;
  rerankerEnabled: boolean;
  rerankerModel: string;
  streaming: boolean;
  language: "vi" | "en";
  setTheme: (theme: ThemeMode) => void;
  setRetrieval: (
    settings: Partial<Pick<SettingsState, "retrievalStrategy" | "topK" | "fetchK" | "minScore">>,
  ) => void;
  setGeneration: (
    settings: Partial<
      Pick<
        SettingsState,
        "temperature" | "maxTokens" | "model" | "rerankerEnabled" | "rerankerModel" | "streaming"
      >
    >,
  ) => void;
  resetRagSettings: () => void;
  applyRuntimeSettings: (settings: RuntimeSettingsResponse) => void;
};

const defaultRagSettings = {
  retrievalStrategy: "parent_child" as RetrievalStrategy,
  topK: 3,
  fetchK: 8,
  minScore: 0.7,
  temperature: 0.2,
  maxTokens: 2048,
  model: "gemini-2.5-flash",
  rerankerEnabled: false,
  rerankerModel: "BAAI/bge-reranker-v2-m3",
  streaming: true,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "system",
      ...defaultRagSettings,
      language: "vi",
      setTheme: (theme) => set({ theme }),
      setRetrieval: (settings) => set(settings),
      setGeneration: (settings) => set(settings),
      resetRagSettings: () => set(defaultRagSettings),
      applyRuntimeSettings: (settings) =>
        set({
          retrievalStrategy: settings.retrieval_strategy,
          topK: settings.top_k,
          fetchK: settings.fetch_k,
          minScore: settings.min_score,
          temperature: settings.llm_temperature,
          maxTokens: settings.llm_max_tokens,
          model: settings.llm_model,
          rerankerEnabled: settings.reranker_enabled,
          rerankerModel: settings.reranker_model,
        }),
    }),
    { name: "rag-settings" },
  ),
);
