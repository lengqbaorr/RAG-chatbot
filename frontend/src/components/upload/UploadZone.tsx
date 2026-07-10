import { Link, Upload } from "lucide-react";
import { type FormEvent, useRef, useState } from "react";

import { Button } from "@/components/common/Button";
import { Spinner } from "@/components/common/Spinner";
import { useUploadDocument, useUploadDocumentUrl } from "@/hooks/useDocuments";
import { cn } from "@/utils/cn";

const allowed = [
  ".pdf",
  ".docx",
  ".txt",
  ".md",
  ".png",
  ".jpg",
  ".jpeg",
  ".bmp",
  ".gif",
  ".tif",
  ".tiff",
  ".webp",
];

export function UploadZone() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const upload = useUploadDocument();
  const uploadUrl = useUploadDocumentUrl();

  const submit = (file: File | undefined) => {
    if (!file) return;
    void upload.mutateAsync(file);
  };

  const submitUrl = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleanUrl = url.trim();
    if (!cleanUrl) return;
    void uploadUrl.mutateAsync({ url: cleanUrl, title: title.trim() || undefined }).then(() => {
      setUrl("");
      setTitle("");
    });
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
      <div
        className={cn(
          "rounded-lg border border-dashed border-border bg-card p-6 transition",
          dragging && "border-primary bg-muted",
        )}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          submit(event.dataTransfer.files[0]);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={allowed.join(",")}
          onChange={(event) => submit(event.target.files?.[0])}
        />
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
            <Upload className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="text-sm font-medium">Upload document</div>
            <div className="mt-1 text-xs text-muted-foreground">
              PDF, DOCX, TXT, Markdown hoặc ảnh OCR. Indexing chạy qua job.
            </div>
          </div>
          <Button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={upload.isPending}
            leftIcon={upload.isPending ? <Spinner /> : <Upload className="h-4 w-4" />}
          >
            {upload.isPending ? "Uploading" : "Choose file"}
          </Button>
          {upload.isError ? <p className="text-sm text-destructive">{upload.error.message}</p> : null}
          {upload.data ? (
            <p className="text-sm text-muted-foreground">
              Job {upload.data.job_id ?? "n/a"} · {upload.data.status}
            </p>
          ) : null}
        </div>
      </div>

      <form className="rounded-lg border border-border bg-card p-6" onSubmit={submitUrl}>
        <div className="flex flex-col gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
            <Link className="h-5 w-5 text-muted-foreground" />
          </div>
          <div>
            <div className="text-sm font-medium">Index web page</div>
            <div className="mt-1 text-xs text-muted-foreground">Nhập URL HTML để hệ thống tải nội dung và index.</div>
          </div>
          <input
            className="h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus:border-primary"
            placeholder="https://example.com/article"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
          <input
            className="h-9 rounded-md border border-input bg-background px-3 text-sm outline-none focus:border-primary"
            placeholder="Tên hiển thị tùy chọn"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
          <Button
            type="submit"
            disabled={uploadUrl.isPending || !url.trim()}
            leftIcon={uploadUrl.isPending ? <Spinner /> : <Link className="h-4 w-4" />}
          >
            {uploadUrl.isPending ? "Submitting" : "Add URL"}
          </Button>
          {uploadUrl.isError ? <p className="text-sm text-destructive">{uploadUrl.error.message}</p> : null}
          {uploadUrl.data ? (
            <p className="text-sm text-muted-foreground">
              Job {uploadUrl.data.job_id ?? "n/a"} · {uploadUrl.data.status}
            </p>
          ) : null}
        </div>
      </form>
    </div>
  );
}
