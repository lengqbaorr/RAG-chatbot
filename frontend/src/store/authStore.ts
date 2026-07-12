import { create } from "zustand";

type AuthState = {
  token: string | null;
  user: { user_id: string; username: string; display_name: string } | null;
  setAuth: (auth: {
    token: string;
    user: { user_id: string; username: string; display_name: string };
  }) => void;
  logout: () => void;
};

const TOKEN_KEY = "rag_auth_token";
const USER_KEY = "rag_auth_user";

function readUser() {
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthState["user"];
  } catch {
    window.localStorage.removeItem(USER_KEY);
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  token: window.localStorage.getItem(TOKEN_KEY),
  user: readUser(),
  setAuth: ({ token, user }) => {
    window.localStorage.setItem(TOKEN_KEY, token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
    set({ token, user });
  },
  logout: () => {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
    set({ token: null, user: null });
  },
}));
