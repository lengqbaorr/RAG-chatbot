import { useEffect } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { AuthGate } from "@/components/layout/AuthGate";
import { DocumentPreviewDialog } from "@/components/document/DocumentPreviewDialog";
import { RuntimeSettingsHydrator } from "@/components/layout/RuntimeSettingsHydrator";
import { useSettingsStore } from "@/store/settingsStore";

export function AppLayout() {
  const theme = useSettingsStore((state) => state.theme);

  useEffect(() => {
    const root = document.documentElement;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const dark = theme === "dark" || (theme === "system" && prefersDark);
    root.classList.toggle("dark", dark);
  }, [theme]);

  return (
    <AuthGate>
      <div className="flex min-h-screen bg-background text-foreground">
        <RuntimeSettingsHydrator />
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar />
          <main className="flex-1 overflow-auto">
            <Outlet />
          </main>
        </div>
        <DocumentPreviewDialog />
      </div>
    </AuthGate>
  );
}
