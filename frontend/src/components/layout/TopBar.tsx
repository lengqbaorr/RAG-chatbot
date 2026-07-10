import { Menu, Moon, Sun } from "lucide-react";

import { Button } from "@/components/common/Button";
import { useHealth } from "@/hooks/useHealth";
import { useSettingsStore } from "@/store/settingsStore";
import { useUiStore } from "@/store/uiStore";

export function TopBar() {
  const { data } = useHealth();
  const { theme, setTheme } = useSettingsStore();
  const { toggleSidebar } = useUiStore();
  const nextTheme = theme === "dark" ? "light" : "dark";

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
      <Button
        variant="secondary"
        onClick={() => setTheme(nextTheme)}
        leftIcon={theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      >
        {theme === "dark" ? "Light" : "Dark"}
      </Button>
    </header>
  );
}
