import {
  Bot,
  BriefcaseBusiness,
  Check,
  FileText,
  Gauge,
  MessageSquare,
  Pencil,
  Plus,
  Settings,
  Trash2,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useChatSessions, useDeleteChatSession, useUpdateChatSession } from "@/hooks/useChat";
import { useChatStore } from "@/store/chatStore";
import { cn } from "@/utils/cn";

const navItems = [
  { to: "/", label: "Dashboard", icon: Gauge },
  { to: "/documents", label: "Documents", icon: FileText },
  { to: "/jobs", label: "Jobs", icon: BriefcaseBusiness },
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const navigate = useNavigate();
  const sessions = useChatSessions();
  const updateSession = useUpdateChatSession();
  const deleteSession = useDeleteChatSession();
  const { activeSessionId, isStreaming, setActiveSessionId, clear } = useChatStore();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  const newChat = () => {
    if (isStreaming) return;
    setActiveSessionId(null);
    clear();
    navigate("/chat");
  };

  const openSession = (sessionId: string) => {
    if (isStreaming || editingId) return;
    clear();
    setActiveSessionId(sessionId);
    navigate("/chat");
  };

  const saveTitle = async (sessionId: string) => {
    const title = editingTitle.trim();
    if (title) await updateSession.mutateAsync({ sessionId, title });
    setEditingId(null);
  };

  const removeSession = async (sessionId: string) => {
    if (!window.confirm("Xóa cuộc trò chuyện này?")) return;
    await deleteSession.mutateAsync(sessionId);
    if (activeSessionId === sessionId) newChat();
  };

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
      <nav className="space-y-1 p-3">
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
      <div className="mx-3 border-t border-border" />
      <section className="flex min-h-0 flex-1 flex-col px-3 pb-3 pt-4">
        <div className="mb-2 flex items-center justify-between px-2">
          <span className="text-xs font-semibold uppercase text-muted-foreground">History</span>
          <button
            type="button"
            onClick={newChat}
            disabled={isStreaming}
            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-40"
            aria-label="New chat"
            title="New chat"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1 space-y-1 overflow-y-auto">
          {sessions.data?.sessions.map((session) => {
            const active = activeSessionId === session.session_id;
            const editing = editingId === session.session_id;
            return (
              <div
                key={session.session_id}
                className={cn(
                  "group flex min-h-9 items-center rounded-md text-sm",
                  active ? "bg-muted text-foreground" : "text-muted-foreground hover:bg-muted/70",
                )}
              >
                {editing ? (
                  <form
                    className="flex min-w-0 flex-1 items-center gap-1 px-1"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void saveTitle(session.session_id);
                    }}
                  >
                    <input
                      autoFocus
                      value={editingTitle}
                      onChange={(event) => setEditingTitle(event.target.value)}
                      className="h-7 min-w-0 flex-1 rounded border border-border bg-background px-2 text-xs outline-none focus:border-primary"
                      maxLength={120}
                    />
                    <button type="submit" className="p-1" aria-label="Save title">
                      <Check className="h-3.5 w-3.5" />
                    </button>
                    <button type="button" className="p-1" onClick={() => setEditingId(null)} aria-label="Cancel rename">
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </form>
                ) : (
                  <>
                    <button
                      type="button"
                      onClick={() => openSession(session.session_id)}
                      disabled={isStreaming}
                      className="min-w-0 flex-1 truncate px-2 py-2 text-left"
                      title={session.title}
                    >
                      {session.title}
                    </button>
                    <div className="hidden shrink-0 items-center pr-1 group-hover:flex">
                      <button
                        type="button"
                        className="p-1 hover:text-foreground"
                        onClick={() => {
                          setEditingId(session.session_id);
                          setEditingTitle(session.title);
                        }}
                        aria-label="Rename chat"
                        title="Rename"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        className="p-1 hover:text-destructive"
                        onClick={() => void removeSession(session.session_id)}
                        aria-label="Delete chat"
                        title="Delete"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            );
          })}
          {sessions.isLoading ? (
            <p className="px-2 py-2 text-xs text-muted-foreground">Loading history...</p>
          ) : null}
          {!sessions.isLoading && !sessions.data?.sessions.length ? (
            <p className="px-2 py-2 text-xs text-muted-foreground">No conversations yet</p>
          ) : null}
        </div>
      </section>
    </aside>
  );
}
