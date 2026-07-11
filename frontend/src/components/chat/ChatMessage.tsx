import { Bot, LoaderCircle, User } from "lucide-react";

import { MarkdownViewer } from "@/components/markdown/MarkdownViewer";
import type { ChatMessage as ChatMessageType } from "@/store/chatStore";
import { cn } from "@/utils/cn";
import { stripInlineCitations } from "@/utils/citations";

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const isUser = message.role === "user";
  const content = isUser ? message.content : stripInlineCitations(message.content);

  return (
    <div className={cn("flex gap-3", isUser && "justify-end")}>
      {!isUser ? (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Bot className="h-4 w-4" />
        </div>
      ) : null}
      <div className={cn("max-w-3xl rounded-lg px-4 py-3", isUser ? "bg-primary text-primary-foreground" : "bg-card border border-border")}>
        {!isUser && message.pending && !message.content ? (
          <div
            className="flex min-h-8 items-center gap-3 text-sm text-muted-foreground"
            role="status"
            aria-live="polite"
          >
            <LoaderCircle className="h-4 w-4 shrink-0 animate-spin text-primary" />
            <span>{message.status ?? "Đang xử lý..."}</span>
            <span className="flex items-center gap-1" aria-hidden="true">
              <span className="h-1 w-1 animate-pulse rounded-full bg-current [animation-delay:0ms]" />
              <span className="h-1 w-1 animate-pulse rounded-full bg-current [animation-delay:150ms]" />
              <span className="h-1 w-1 animate-pulse rounded-full bg-current [animation-delay:300ms]" />
            </span>
          </div>
        ) : isUser || message.pending ? (
          <p className="whitespace-pre-wrap text-sm leading-6">{content}</p>
        ) : (
          <MarkdownViewer content={content} />
        )}
        {message.pending && message.content ? (
          <span className="mt-1 inline-block h-4 w-1.5 animate-pulse bg-primary" aria-label="Generating answer" />
        ) : null}
        {message.warning ? (
          <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
            {message.warning}
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
