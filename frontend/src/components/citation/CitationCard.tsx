import { FileText } from "lucide-react";

import type { SourceCitation } from "@/types/api";

export function CitationCard({ source, onClick }: { source: SourceCitation; onClick?: () => void }) {
  return (
    <button
      className="w-full rounded-md border border-border bg-card p-3 text-left transition hover:bg-muted"
      onClick={onClick}
      type="button"
    >
      <div className="flex items-start gap-3">
        <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium">{source.source_name}</div>
          <div className="mt-1 text-xs text-muted-foreground">
            Page {source.page_start ?? "?"}-{source.page_end ?? "?"} · score {source.score.toFixed(4)}
          </div>
          {source.section_title ? <div className="mt-1 truncate text-xs">{source.section_title}</div> : null}
        </div>
      </div>
    </button>
  );
}
