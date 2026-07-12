import { LockKeyhole } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/common/Button";
import { useLogin } from "@/hooks/useAuth";

export function LoginPage() {
  const login = useLogin();
  const [username, setUsername] = useState("local");
  const [password, setPassword] = useState("");

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground">
      <form
        className="w-full max-w-sm rounded-lg border border-border bg-card p-6 shadow-sm"
        onSubmit={(event) => {
          event.preventDefault();
          void login.mutateAsync({ username, password });
        }}
      >
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <LockKeyhole className="h-5 w-5" />
          </div>
          <div>
            <h1 className="font-semibold">RAG Console</h1>
            <p className="text-xs text-muted-foreground">Local authentication</p>
          </div>
        </div>

        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium">Username</span>
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none focus:border-primary"
          />
        </label>

        <label className="mb-4 block">
          <span className="mb-1 block text-sm font-medium">Password</span>
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            autoComplete="current-password"
            className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm outline-none focus:border-primary"
          />
        </label>

        {login.isError ? (
          <p className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {login.error.message}
          </p>
        ) : null}

        <Button type="submit" className="w-full" disabled={login.isPending}>
          {login.isPending ? "Signing in..." : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
