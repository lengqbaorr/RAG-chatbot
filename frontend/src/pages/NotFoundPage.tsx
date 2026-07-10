import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="flex min-h-[calc(100vh-4rem)] flex-col items-center justify-center p-6 text-center">
      <h2 className="text-xl font-semibold">Page not found</h2>
      <p className="mt-2 text-sm text-muted-foreground">Đường dẫn này không tồn tại trong RAG Client.</p>
      <Link
        className="mt-4 inline-flex h-9 items-center justify-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
        to="/"
      >
        Back to dashboard
      </Link>
    </section>
  );
}
