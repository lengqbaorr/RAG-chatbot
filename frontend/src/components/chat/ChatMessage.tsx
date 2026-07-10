import { Bot, User } from "lucide-react";

import { CitationCard } from "@/components/citation/CitationCard";
import { MarkdownViewer } from "@/components/markdown/MarkdownViewer";
import { useChatStore } from "@/store/chatStore";
import type { ChatMessage as ChatMessageType } from "@/store/chatStore";
import { cn } from "@/utils/cn";

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const setActiveSource = useChatStore((state) => state.setActiveSource);
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "justify-end")}>
      {!isUser ? (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Bot className="h-4 w-4" />
        </div>
      ) : null}
      <div className={cn("max-w-3xl rounded-lg px-4 py-3", isUser ? "bg-primary text-primary-foreground" : "bg-card border border-border")}>
        {isUser ? <p className="text-sm leading-6">{message.content}</p> : <MarkdownViewer content={message.content} />}
        {message.warning ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
            {message.warning}
          </div>
        ) : null}
        {message.sources?.length ? (
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {message.sources.map((source) => (
              <CitationCard key={`${source.chunk_id}-${source.source_id}`} source={source} onClick={() => setActiveSource(source)} />
            ))}
          </div>
        ) : null}
      </div>
      {isUser ? (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
          <User className="h-4 w-4" />
        </div>
      ) : null}
    </div>
  );
}
