import { Bot, BriefcaseBusiness, FileText, Gauge, MessageSquare, Settings } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/utils/cn";

const navItems = [
  { to: "/", label: "Dashboard", icon: Gauge },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/jobs", label: "Jobs", icon: BriefcaseBusiness },
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-border bg-card md:flex md:flex-col">
      <div className="flex h-16 items-center gap-3 border-b border-border px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Bot className="h-5 w-5" />
        </div>
        <div>
          <div className="font-semibold">RAG Console</div>
          <div className="text-xs text-muted-foreground">Personal knowledge engine</div>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition hover:bg-muted hover:text-foreground",
                isActive && "bg-muted text-foreground",
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
