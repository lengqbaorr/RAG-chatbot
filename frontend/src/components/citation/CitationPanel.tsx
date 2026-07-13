import { Check, FileSearch, FileText, X } from "lucide-react";

import { Button } from "@/components/common/Button";
import { CitationCard } from "@/components/citation/CitationCard";
import { EmptyState } from "@/components/common/EmptyState";
import { Spinner } from "@/components/common/Spinner";
import { StatusPill } from "@/components/common/StatusPill";
import { useDocuments } from "@/hooks/useDocuments";
import { useChatStore } from "@/store/chatStore";
import { cn } from "@/utils/cn";

export function CitationPanel() {
  const {
    activeSource,
    selectedSourceIds,
    setActiveSource,
    setSelectedSourceIds,
    toggleSelectedSource,
    messages,
  } = useChatStore();
  const documents = useDocuments();
  const completedDocuments = documents.data?.documents.filter((document) => document.status === "COMPLETED") ?? [];
  const allCompletedSelected =
    completedDocuments.length > 0 && completedDocuments.every((document) => selectedSourceIds.includes(document.source_id));
  const latestAnswerSources =
    [...messages]
      .reverse()
      .find((message) => message.role === "assistant" && message.sources?.length)?.sources ?? [];
  const bestAnswerSource = latestAnswerSources.length
    ? [...latestAnswerSources].sort((a, b) => b.score - a.score)[0]
    : null;

  const toggleAll = () => {
    setSelectedSourceIds(allCompletedSelected ? [] : completedDocuments.map((document) => document.source_id));
  };

  return (
    <aside className="hidden w-96 border-l border-border bg-card xl:flex xl:flex-col">
      <div className="border-b border-border p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold">Sources</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              Tick tài liệu muốn dùng cho câu hỏi.
            </p>
          </div>
          <Button variant="secondary" onClick={toggleAll} disabled={!completedDocuments.length}>
            {allCompletedSelected ? "Clear" : "All"}
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4">
        {documents.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> Loading sources
          </div>
        ) : null}

        {documents.isError ? (
          <EmptyState title="Cannot load sources" description={documents.error.message} />
        ) : null}

        {!documents.isLoading && !documents.isError && !documents.data?.documents.length ? (
          <EmptyState title="No documents" description="Upload tài liệu ở trang Documents để chọn source chat." />
        ) : null}

        <div className="space-y-2">
          {documents.data?.documents.map((document) => {
            const completed = document.status === "COMPLETED";
            const checked = selectedSourceIds.includes(document.source_id);
            return (
              <div
                key={document.source_id}
                className={cn(
                  "flex items-start gap-3 rounded-md border border-border p-3 transition",
                  checked ? "bg-muted" : "bg-background hover:bg-muted",
                  !completed && "opacity-60",
                )}
              >
                <button
                  type="button"
                  disabled={!completed}
                  onClick={() => toggleSelectedSource(document.source_id)}
                  className={cn(
                    "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border border-border",
                    checked && "border-primary bg-primary text-primary-foreground",
                    completed ? "cursor-pointer" : "cursor-not-allowed",
                  )}
                  aria-label={checked ? "Unselect source" : "Select source"}
                >
                  {checked ? <Check className="h-3.5 w-3.5" /> : null}
                </button>
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{document.source_name}</span>
                  <span className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    {document.chunk_count} chunks
                    <StatusPill status={document.status} />
                  </span>
                </span>
                <Button
                  variant="ghost"
                  className="h-8 w-8 shrink-0 px-0"
                  disabled={!completed}
                  onClick={() =>
                    setActiveSource({
                      source_id: document.source_id,
                      source_name: document.source_name,
                      content_preview: "",
                    })
                  }
                  aria-label="Open document preview"
                  title="Preview"
                >
                  <FileSearch className="h-4 w-4" />
                </Button>
              </div>
            );
          })}
        </div>

        <div className="mt-6 border-t border-border pt-4">
          <div className="mb-3">
            <h3 className="text-sm font-semibold">Best source</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Nguồn có điểm cao nhất cho câu trả lời gần nhất.
            </p>
          </div>
          {bestAnswerSource ? (
            <div className="space-y-2">
              <CitationCard
                key={`${bestAnswerSource.chunk_id}-${bestAnswerSource.source_id}`}
                source={bestAnswerSource}
                onClick={() => setActiveSource(bestAnswerSource)}
              />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Chưa có nguồn truy xuất cho cuộc trò chuyện này.</p>
          )}
        </div>

        <div className="mt-6 border-t border-border pt-4">
          {!activeSource ? (
            <p className="text-sm text-muted-foreground">
              Chọn một retrieved source để xem page, section và preview chunk.
            </p>
          ) : (
            <div className="space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-semibold">Citation detail</h3>
                <Button variant="ghost" aria-label="Close source" onClick={() => setActiveSource(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Document</div>
                <div className="font-medium">{activeSource.source_name}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Page</div>
                <div>
                  {activeSource.page_start ?? "?"}-{activeSource.page_end ?? "?"}
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Section</div>
                <div>{activeSource.section_title ?? "No section"}</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
