import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatMessage } from "@/components/chat/ChatMessage";
import { useDocuments } from "@/hooks/useDocuments";
import { useSendChatMessage } from "@/hooks/useChat";
import { useChatStore } from "@/store/chatStore";
import { useSettingsStore } from "@/store/settingsStore";
import { useEffect, useMemo } from "react";

function makeId() {
  return crypto.randomUUID();
}

export function ChatWindow() {
  const { messages, addMessage, updateMessage, clear, selectedSourceIds, setSelectedSourceIds } = useChatStore();
  const settings = useSettingsStore();
  const send = useSendChatMessage();
  const documents = useDocuments();
  const completedDocuments = useMemo(
    () => documents.data?.documents.filter((document) => document.status === "COMPLETED") ?? [],
    [documents.data?.documents],
  );

  useEffect(() => {
    const completedIds = new Set(completedDocuments.map((document) => document.source_id));
    const validSelected = selectedSourceIds.filter((sourceId) => completedIds.has(sourceId));
    if (validSelected.length !== selectedSourceIds.length) {
      setSelectedSourceIds(validSelected);
      return;
    }
    if (!selectedSourceIds.length && completedDocuments.length) {
      setSelectedSourceIds(completedDocuments.map((document) => document.source_id));
    }
  }, [completedDocuments, selectedSourceIds, setSelectedSourceIds]);

  const submit = (question: string) => {
    const userId = makeId();
    const assistantId = makeId();
    const now = new Date().toISOString();
    addMessage({ id: userId, role: "user", content: question, createdAt: now });
    addMessage({ id: assistantId, role: "assistant", content: "Đang tìm trong tài liệu...", createdAt: now, pending: true });
    send.mutate(
      {
        question,
        strategy: "parent_child",
        top_k: settings.topK,
        fetch_k: settings.fetchK,
        min_score: settings.minScore,
        filters: {
          source_id: selectedSourceIds.length === 1 ? selectedSourceIds[0] : { $in: selectedSourceIds },
        },
      },
      {
        onSuccess: (response) => {
          const stoppedByTokenLimit = response.report.llm_finish_reason === "MAX_TOKENS";
          updateMessage(assistantId, {
            content: response.answer,
            sources: response.sources,
            pending: false,
            warning: stoppedByTokenLimit
              ? "Câu trả lời có thể bị cắt do đạt giới hạn output token. Hãy tăng LLM_MAX_TOKENS hoặc hỏi hẹp hơn."
              : undefined,
          });
        },
        onError: (error) => {
          updateMessage(assistantId, {
            content: `Không thể tạo câu trả lời: ${error.message}`,
            pending: false,
          });
        },
      },
    );
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
        <Button variant="secondary" onClick={clear} disabled={!messages.length}>
          Clear
        </Button>
      </div>
      <div className="flex-1 overflow-auto p-4">
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
      <ChatInput disabled={send.isPending || !selectedSourceIds.length} onSubmit={submit} />
    </div>
  );
}
