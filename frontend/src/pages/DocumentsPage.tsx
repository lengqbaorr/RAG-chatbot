import { DocumentTable } from "@/components/document/DocumentTable";
import { UploadZone } from "@/components/upload/UploadZone";

export function DocumentsPage() {
  return (
    <section className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-semibold">Documents</h2>
        <p className="mt-1 text-sm text-muted-foreground">Upload, index, reindex và xóa tài liệu khỏi metadata store + vector store.</p>
      </div>
      <UploadZone />
      <DocumentTable />
    </section>
  );
}
