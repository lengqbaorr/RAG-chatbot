import type { ReactNode } from "react";
import { useEffect } from "react";

import { Spinner } from "@/components/common/Spinner";
import { AUTH_DISABLED, useAuthStatus, useCurrentUser } from "@/hooks/useAuth";
import { LoginPage } from "@/pages/LoginPage";
import { useAuthStore } from "@/store/authStore";

export function AuthGate({ children }: { children: ReactNode }) {
  const token = useAuthStore((state) => state.token);
  const setAuth = useAuthStore((state) => state.setAuth);
  const status = useAuthStatus();
  const authEnabled = Boolean(status.data?.enabled);
  const currentUser = useCurrentUser(authEnabled && Boolean(token));

  useEffect(() => {
    if (authEnabled && token && currentUser.data) {
      setAuth({ token, user: currentUser.data });
    }
  }, [authEnabled, currentUser.data, setAuth, token]);

  if (AUTH_DISABLED) {
    return children;
  }

  if (status.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-3 bg-background text-sm text-muted-foreground">
        <Spinner /> Checking authentication
      </div>
    );
  }

  if (authEnabled && !token) {
    return <LoginPage />;
  }

  if (authEnabled && token && currentUser.isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-3 bg-background text-sm text-muted-foreground">
        <Spinner /> Loading profile
      </div>
    );
  }

  return children;
}
