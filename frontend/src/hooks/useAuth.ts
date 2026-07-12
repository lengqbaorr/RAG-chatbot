import { useMutation, useQuery } from "@tanstack/react-query";

import { getAuthStatus, getCurrentUser, login } from "@/api/auth";
import { queryClient } from "@/services/queryClient";
import { useAuthStore } from "@/store/authStore";

export const AUTH_MODE = import.meta.env.VITE_AUTH_MODE ?? "disabled";
export const AUTH_DISABLED = AUTH_MODE === "disabled";

export function useAuthStatus() {
  return useQuery({
    queryKey: ["auth-status"],
    queryFn: getAuthStatus,
    enabled: !AUTH_DISABLED,
    staleTime: 60_000,
  });
}

export function useCurrentUser(enabled: boolean) {
  return useQuery({
    queryKey: ["auth-me"],
    queryFn: getCurrentUser,
    enabled,
    retry: false,
  });
}

export function useLogin() {
  const setAuth = useAuthStore((state) => state.setAuth);
  return useMutation({
    mutationFn: login,
    onSuccess: (response) => {
      setAuth({ token: response.access_token, user: response.user });
      void queryClient.invalidateQueries();
    },
  });
}
