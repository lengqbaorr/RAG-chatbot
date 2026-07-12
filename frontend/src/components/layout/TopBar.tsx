import { LogOut, Menu, Moon, Sun } from "lucide-react";

import { Button } from "@/components/common/Button";
import { useHealth } from "@/hooks/useHealth";
import { useAuthStatus } from "@/hooks/useAuth";
import { queryClient } from "@/services/queryClient";
import { useAuthStore } from "@/store/authStore";
import { useSettingsStore } from "@/store/settingsStore";
import { useUiStore } from "@/store/uiStore";

export function TopBar() {
  const { data } = useHealth();
  const authStatus = useAuthStatus();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { theme, setTheme } = useSettingsStore();
  const { toggleSidebar } = useUiStore();
  const nextTheme = theme === "dark" ? "light" : "dark";
  const signOut = () => {
    logout();
    queryClient.clear();
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-background px-4 md:px-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" className="md:hidden" onClick={toggleSidebar} aria-label="Open sidebar">
          <Menu className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-base font-semibold">RAG Client</h1>
          <p className="text-xs text-muted-foreground">
            {data?.ready ? "Backend ready" : "Checking backend"} · {data?.llm_provider ?? "LLM unknown"}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {authStatus.data?.enabled ? (
          <div className="hidden text-right text-xs sm:block">
            <div className="font-medium">{user?.display_name ?? "Local User"}</div>
            <div className="text-muted-foreground">{user?.username ?? "local"}</div>
          </div>
        ) : null}
        <Button
          variant="secondary"
          onClick={() => setTheme(nextTheme)}
          leftIcon={theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        >
          {theme === "dark" ? "Light" : "Dark"}
        </Button>
        {authStatus.data?.enabled ? (
          <Button variant="ghost" onClick={signOut} aria-label="Sign out" title="Sign out">
            <LogOut className="h-4 w-4" />
          </Button>
        ) : null}
      </div>
    </header>
  );
}
