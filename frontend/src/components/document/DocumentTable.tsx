import { RefreshCw, Trash2 } from "lucide-react";

import { Button } from "@/components/common/Button";
import { EmptyState } from "@/components/common/EmptyState";
import { Spinner } from "@/components/common/Spinner";
import { StatusPill } from "@/components/common/StatusPill";
import { useDeleteDocument, useDocuments, useReindexDocument } from "@/hooks/useDocuments";

export function DocumentTable() {
  const { data, isLoading, isError, error } = useDocuments();
  const remove = useDeleteDocument();
  const reindex = useReindexDocument();

  if (isLoading) return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Spinner /> Loading documents</div>;
  if (isError) return <EmptyState title="Cannot load documents" description={error.message} />;
  if (!data?.documents.length) return <EmptyState title="No documents" description="Upload tài liệu để bắt đầu index và chat với dữ liệu cá nhân." />;

  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <table className="w-full text-sm">
        <thead className="border-b border-border bg-muted text-left text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-4 py-3">Filename</th>
            <th className="px-4 py-3">Type</th>
            <th className="px-4 py-3">Chunks</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.documents.map((document) => (
            <tr key={document.source_id} className="border-b border-border last:border-0">
              <td className="max-w-md truncate px-4 py-3 font-medium">{document.source_name}</td>
              <td className="px-4 py-3 text-muted-foreground">{document.source_type ?? "unknown"}</td>
              <td className="px-4 py-3">{document.chunk_count}</td>
              <td className="px-4 py-3">
                <StatusPill status={document.status} />
              </td>
              <td className="px-4 py-3">
                <div className="flex justify-end gap-2">
                  <Button
                    variant="secondary"
                    aria-label="Reindex document"
                    onClick={() => reindex.mutate(document.source_id)}
                    disabled={reindex.isPending}
                  >
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="danger"
                    aria-label="Delete document"
                    onClick={() => remove.mutate(document.source_id)}
                    disabled={remove.isPending}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
