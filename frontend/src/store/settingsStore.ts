import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "light" | "dark" | "system";

type SettingsState = {
  theme: ThemeMode;
  topK: number;
  fetchK: number;
  minScore: number;
  temperature: number;
  streaming: boolean;
  language: "vi" | "en";
  setTheme: (theme: ThemeMode) => void;
  setRetrieval: (settings: Partial<Pick<SettingsState, "topK" | "fetchK" | "minScore">>) => void;
  setGeneration: (settings: Partial<Pick<SettingsState, "temperature" | "streaming">>) => void;
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "system",
      topK: 3,
      fetchK: 10,
      minScore: 0.7,
      temperature: 0.2,
      streaming: false,
      language: "vi",
      setTheme: (theme) => set({ theme }),
      setRetrieval: (settings) => set(settings),
      setGeneration: (settings) => set(settings),
    }),
    { name: "rag-settings" },
  ),
);
