import { useMutation, useQuery } from "@tanstack/react-query";

import { getAuthStatus, getCurrentUser, login } from "@/api/auth";
import { queryClient } from "@/services/queryClient";
import { useAuthStore } from "@/store/authStore";

export function useAuthStatus() {
  return useQuery({
    queryKey: ["auth-status"],
    queryFn: getAuthStatus,
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
