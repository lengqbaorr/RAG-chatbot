import { create } from "zustand";

type AuthState = {
  user: { name: string; email?: string } | null;
  loginAsLocalUser: () => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: { name: "Local User" },
  loginAsLocalUser: () => set({ user: { name: "Local User" } }),
  logout: () => set({ user: null }),
}));
