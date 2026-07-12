import { FileText, X } from "lucide-react";
import { useEffect, useMemo } from "react";

import { getDocumentFileUrl } from "@/api/documents";
import { Button } from "@/components/common/Button";
import { Spinner } from "@/components/common/Spinner";
import { useDocumentChunkPreview, useDocumentPreview } from "@/hooks/useDocuments";
import { useChatStore } from "@/store/chatStore";

export function DocumentPreviewDialog() {
  const activeSource = useChatStore((state) => state.activeSource);
  const setActiveSource = useChatStore((state) => state.setActiveSource);
  const preview = useDocumentPreview(activeSource?.source_id ?? null);
  const chunk = useDocumentChunkPreview(
    activeSource?.source_id ?? null,
    activeSource?.chunk_id ?? null,
  );

  useEffect(() => {
    if (!activeSource) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setActiveSource(null);
    };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [activeSource, setActiveSource]);

  const fileUrl = useMemo(() => {
    if (!activeSource) return "";
    const page = Math.max(1, activeSource.page_start ?? 1);
    return `${getDocumentFileUrl(activeSource.source_id)}#page=${page}`;
  }, [activeSource]);

  if (!activeSource) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Preview ${activeSource.source_name}`}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) setActiveSource(null);
      }}
    >
      <div className="flex h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-lg border border-border bg-background shadow-2xl">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold">{activeSource.source_name}</h2>
            <p className="truncate text-xs text-muted-foreground">
              Page {activeSource.page_start ?? "?"}-{activeSource.page_end ?? "?"}
              {activeSource.section_title ? ` · ${activeSource.section_title}` : ""}
            </p>
          </div>
          <Button variant="ghost" onClick={() => setActiveSource(null)} aria-label="Close preview">
            <X className="h-4 w-4" />
          </Button>
        </header>

        {preview.isLoading || chunk.isLoading ? (
          <div className="flex flex-1 items-center justify-center gap-3 text-sm text-muted-foreground">
            <Spinner /> Loading document preview
          </div>
        ) : null}

        {preview.isError || chunk.isError ? (
          <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-destructive">
            {preview.error?.message ?? chunk.error?.message ?? "Cannot load preview"}
          </div>
        ) : null}

        {preview.data && !preview.isLoading && !chunk.isLoading ? (
          <div className="flex min-h-0 flex-1 flex-col">
            {chunk.data?.content ? (
              <section className="max-h-40 shrink-0 overflow-auto border-b border-border bg-muted/50 px-5 py-3">
                <div className="mb-1 text-xs font-semibold uppercase text-muted-foreground">Retrieved passage</div>
                <mark className="whitespace-pre-wrap bg-yellow-200 text-sm leading-6 text-black dark:bg-yellow-700 dark:text-white">
                  {chunk.data.content}
                </mark>
              </section>
            ) : null}

            {preview.data.preview_kind === "pdf" ? (
              <div className="min-h-0 flex-1 bg-muted">
                <iframe
                  key={fileUrl}
                  src={fileUrl}
                  title={`PDF preview: ${preview.data.source_name}`}
                  className="h-full w-full border-0"
                />
              </div>
            ) : (
              <TextDocumentPreview
                content={preview.data.content ?? ""}
                highlightedContent={chunk.data?.content ?? activeSource.content_preview}
                truncated={preview.data.truncated}
              />
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function TextDocumentPreview({
  content,
  highlightedContent,
  truncated,
}: {
  content: string;
  highlightedContent: string;
  truncated: boolean;
}) {
  const match = findHighlight(content, highlightedContent);
  return (
    <div className="min-h-0 flex-1 overflow-auto p-6">
      {truncated ? (
        <div className="mb-4 flex items-center gap-2 text-xs text-amber-700 dark:text-amber-300">
          <FileText className="h-4 w-4" /> Preview was truncated for performance.
        </div>
      ) : null}
      <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-7 text-foreground">
        {match ? (
          <>
            {content.slice(0, match.start)}
            <mark className="bg-yellow-200 text-black dark:bg-yellow-700 dark:text-white">
              {content.slice(match.start, match.end)}
            </mark>
            {content.slice(match.end)}
          </>
        ) : (
          content
        )}
      </pre>
    </div>
  );
}

function findHighlight(content: string, chunk: string): { start: number; end: number } | null {
  const candidates = [chunk.trim(), chunk.replace(/^Section:[^\n]*\n+/i, "").trim()]
    .filter(Boolean)
    .map((value) => value.slice(0, 240));
  for (const candidate of candidates) {
    const index = content.indexOf(candidate);
    if (index >= 0) return { start: index, end: index + candidate.length };
  }
  return null;
}
