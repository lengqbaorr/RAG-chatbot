import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { useDocuments } from "@/hooks/useDocuments";
import { useChatSession, useCreateChatSession } from "@/hooks/useChat";
import { streamChatMessage } from "@/api/chat";
import { queryClient } from "@/services/queryClient";
import { useChatStore } from "@/store/chatStore";
import { useSettingsStore } from "@/store/settingsStore";
import type { ChatResponse } from "@/types/api";
import { useEffect, useMemo, useRef } from "react";

const TYPEWRITER_DELAY_MS = 12;

type Typewriter = {
  push: (text: string) => void;
  finish: () => Promise<void>;
  cancel: () => string;
};

function createTypewriter(onText: (text: string) => void): Typewriter {
  let queued = "";
  let rendered = "";
  let timer: number | null = null;
  let finished = false;
  let settled = false;
  let resolveDrain: () => void = () => undefined;
  const drained = new Promise<void>((resolve) => {
    resolveDrain = resolve;
  });

  const settle = () => {
    if (!settled) {
      settled = true;
      resolveDrain();
    }
  };

  const schedule = () => {
    if (timer !== null || settled) return;
    timer = window.setTimeout(tick, TYPEWRITER_DELAY_MS);
  };

  const tick = () => {
    timer = null;
    if (queued) {
      const codePoint = queued.codePointAt(0);
      if (codePoint !== undefined) {
        const character = String.fromCodePoint(codePoint);
        queued = queued.slice(character.length);
        rendered += character;
        onText(rendered);
      }
    }
    if (queued) schedule();
    else if (finished) settle();
  };

  return {
    push: (text) => {
      if (!text || finished) return;
      queued += text;
      schedule();
    },
    finish: () => {
      finished = true;
      if (queued) schedule();
      else settle();
      return drained;
    },
    cancel: () => {
      if (timer !== null) window.clearTimeout(timer);
      timer = null;
      queued = "";
      finished = true;
      settle();
      return rendered;
    },
  };
}

function makeId() {
  return crypto.randomUUID();
}

export function ChatWindow() {
  const {
    messages,
    addMessage,
    updateMessage,
    clear,
    setMessages,
    selectedSourceIds,
    setSelectedSourceIds,
    activeSessionId,
    setActiveSessionId,
    isStreaming,
    setStreaming,
  } = useChatStore();
  const settings = useSettingsStore();
  const abortController = useRef<AbortController | null>(null);
  const typewriterRef = useRef<Typewriter | null>(null);
  const conversationViewport = useRef<HTMLDivElement | null>(null);
  const scrollFrame = useRef<number | null>(null);
  const documents = useDocuments();
  const sessionHistory = useChatSession(activeSessionId);
  const createSession = useCreateChatSession();
  const completedDocuments = useMemo(
    () => documents.data?.documents.filter((document) => document.status === "COMPLETED") ?? [],
    [documents.data?.documents],
  );

  useEffect(() => {
    const completedIds = new Set(completedDocuments.map((document) => document.source_id));
    const validSelected = selectedSourceIds.filter((sourceId) => completedIds.has(sourceId));
    if (validSelected.length !== selectedSourceIds.length) {
      setSelectedSourceIds(validSelected);
    }
  }, [completedDocuments, selectedSourceIds, setSelectedSourceIds]);

  useEffect(() => {
    if (!sessionHistory.data || isStreaming) return;
    setMessages(
      sessionHistory.data.messages.map((message) => ({
        id: message.message_id,
        role: message.role,
        content: message.content,
        createdAt: message.timestamp,
        sources: message.sources,
        warning:
          message.status === "cancelled"
            ? "Câu trả lời đã bị dừng."
            : message.status === "failed"
              ? "Câu trả lời gặp lỗi khi xử lý."
              : undefined,
      })),
    );
    setSelectedSourceIds(sessionHistory.data.session.selected_source_ids);
  }, [isStreaming, sessionHistory.data, setMessages, setSelectedSourceIds]);

  useEffect(
    () => () => {
      abortController.current?.abort();
      typewriterRef.current?.cancel();
      if (scrollFrame.current !== null) window.cancelAnimationFrame(scrollFrame.current);
    },
    [],
  );

  useEffect(() => {
    if (scrollFrame.current !== null) window.cancelAnimationFrame(scrollFrame.current);
    scrollFrame.current = window.requestAnimationFrame(() => {
      const viewport = conversationViewport.current;
      if (!viewport) return;
      viewport.scrollTo({
        top: viewport.scrollHeight,
        behavior: isStreaming ? "auto" : "smooth",
      });
    });
    return () => {
      if (scrollFrame.current !== null) window.cancelAnimationFrame(scrollFrame.current);
    };
  }, [messages, isStreaming]);

  const submit = async (question: string) => {
    const userId = makeId();
    const assistantId = makeId();
    const now = new Date().toISOString();
    addMessage({ id: userId, role: "user", content: question, createdAt: now });
    addMessage({
      id: assistantId,
      role: "assistant",
      content: "",
      createdAt: now,
      pending: true,
      status: "Đang tìm và tổng hợp thông tin từ tài liệu...",
    });
    const controller = new AbortController();
    abortController.current = controller;
    setStreaming(true);
    const typewriter = createTypewriter((content) =>
      updateMessage(assistantId, { content, status: undefined }),
    );
    typewriterRef.current = typewriter;
    let completedResponse: ChatResponse | null = null;
    let sessionId = activeSessionId;
    try {
      if (!sessionId) {
        const session = await createSession.mutateAsync({
          title: question,
          selected_source_ids: selectedSourceIds,
        });
        sessionId = session.session_id;
        setActiveSessionId(sessionId);
      }
      await streamChatMessage({
        question,
        strategy: "parent_child",
        top_k: settings.topK,
        fetch_k: settings.fetchK,
        min_score: settings.minScore,
        filters: {
          source_id: selectedSourceIds.length === 1 ? selectedSourceIds[0] : { $in: selectedSourceIds },
        },
        session_id: sessionId,
        selected_source_ids: selectedSourceIds,
      }, {
        onStart: () => {
          updateMessage(assistantId, { status: "Đang tạo câu trả lời..." });
        },
        onDelta: typewriter.push,
        onComplete: (response) => {
          completedResponse = response;
        },
      }, controller.signal);
      await typewriter.finish();
      if (controller.signal.aborted) throw new DOMException("Chat stream cancelled", "AbortError");
      if (!completedResponse) throw new Error("Stream completed without a final response");
      const response: ChatResponse = completedResponse;
      const stoppedByTokenLimit = response.report.llm_finish_reason === "MAX_TOKENS";
      updateMessage(assistantId, {
        content: response.answer,
        sources: response.sources,
        pending: false,
        status: undefined,
        warning: stoppedByTokenLimit
          ? "Câu trả lời có thể bị cắt do đạt giới hạn output token. Hãy tăng LLM_MAX_TOKENS hoặc hỏi hẹp hơn."
          : undefined,
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["chat-sessions"] }),
        queryClient.invalidateQueries({ queryKey: ["chat-session", sessionId] }),
      ]);
    } catch (error) {
      const rendered = typewriter.cancel();
      if (controller.signal.aborted) {
        updateMessage(assistantId, {
          content: rendered || "Đã hủy tạo câu trả lời.",
          pending: false,
          status: undefined,
          warning: rendered ? "Đã dừng tạo câu trả lời." : undefined,
        });
      } else {
        const message = error instanceof Error ? error.message : "Unknown streaming error";
        updateMessage(assistantId, {
          content: rendered || `Không thể tạo câu trả lời: ${message}`,
          pending: false,
          status: undefined,
          warning: rendered ? `Stream bị gián đoạn: ${message}` : undefined,
        });
      }
      if (sessionId) {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["chat-sessions"] }),
          queryClient.invalidateQueries({ queryKey: ["chat-session", sessionId] }),
        ]);
      }
    } finally {
      if (abortController.current === controller) {
        abortController.current = null;
        setStreaming(false);
      }
      if (typewriterRef.current === typewriter) typewriterRef.current = null;
    }
  };

  const cancel = () => {
    abortController.current?.abort();
    typewriterRef.current?.cancel();
  };

  const clearChat = () => {
    abortController.current?.abort();
    typewriterRef.current?.cancel();
    setActiveSessionId(null);
    clear();
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-col gap-3 border-b border-border px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="font-semibold">Chat</h2>
          <p className="text-xs text-muted-foreground">
            Parent-child retrieval · {selectedSourceIds.length}/{completedDocuments.length} source selected
          </p>
        </div>
        <Button variant="secondary" onClick={clearChat} disabled={isStreaming}>
          New chat
        </Button>
      </div>
      <div ref={conversationViewport} className="flex-1 overflow-auto p-4">
        <div className="mx-auto max-w-4xl space-y-5">
          {!messages.length ? (
            <EmptyState
              title="Start a grounded conversation"
              description="Đặt câu hỏi về tài liệu đã upload. Câu trả lời sẽ kèm nguồn để kiểm chứng."
            />
          ) : (
            <AnimatePresence initial={false}>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                >
                  <ChatMessage message={message} />
                </motion.div>
              ))}
            </AnimatePresence>
          )}
        </div>
      </div>
      <ChatInput
        disabled={!selectedSourceIds.length}
        streaming={isStreaming}
        onSubmit={submit}
        onCancel={cancel}
      />
    </div>
  );
}
