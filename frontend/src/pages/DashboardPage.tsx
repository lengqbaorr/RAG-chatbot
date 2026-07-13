import { Activity, Boxes, Database, FileText } from "lucide-react";

import { MetricCard } from "@/components/common/MetricCard";
import { Spinner } from "@/components/common/Spinner";
import { StatusPill } from "@/components/common/StatusPill";
import { useDocuments } from "@/hooks/useDocuments";
import { useHealth } from "@/hooks/useHealth";
import { useJobs } from "@/hooks/useJobs";

export function DashboardPage() {
  const health = useHealth();
  const documents = useDocuments();
  const jobs = useJobs();
  const totalChunks = documents.data?.documents.reduce((sum, document) => sum + document.chunk_count, 0) ?? 0;
  const runningJobs = jobs.data?.jobs.filter((job) => ["PENDING", "RUNNING"].includes(job.status.toUpperCase())).length ?? 0;

  return (
    <section className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-semibold">Dashboard</h2>
        <p className="mt-1 text-sm text-muted-foreground">Theo dõi trạng thái RAG backend và dữ liệu đã index.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Documents" value={documents.data?.documents.length ?? 0} icon={<FileText className="h-4 w-4" />} />
        <MetricCard title="Chunks" value={totalChunks} icon={<Boxes className="h-4 w-4" />} />
        <MetricCard title="Collection vectors" value={health.data?.collection_count ?? 0} icon={<Database className="h-4 w-4" />} />
        <MetricCard title="Active jobs" value={runningJobs} icon={<Activity className="h-4 w-4" />} />
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">System health</h3>
          {health.isLoading ? <Spinner /> : <StatusPill status={health.data?.ready ? "ready" : "not ready"} />}
        </div>
        <div className="mt-4 grid gap-3 text-sm md:grid-cols-2 xl:grid-cols-3">
          <div>App: {health.data?.app ?? "unknown"}</div>
          <div>Database: {health.data?.database ?? "unknown"}</div>
          <div>Vector store: {health.data?.vector_store ?? "unknown"}</div>
          <div>Embedding: {health.data?.embedding_service ?? "unknown"}</div>
          <div>LLM: {health.data?.llm_provider ?? "unknown"}</div>
          <div>Collection: {health.data?.collection ?? "none"}</div>
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Model runtime</h3>
          {health.isLoading ? <Spinner /> : null}
        </div>
        <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <ModelStatus
            label="Embedding"
            model={health.data?.embedding_model}
            loaded={health.data?.embedding_model_loaded}
            cached={health.data?.embedding_model_cached}
          />
          <ModelStatus
            label="Reranker"
            model={health.data?.reranker_model}
            loaded={health.data?.reranker_model_loaded}
            cached={health.data?.reranker_model_cached}
            unavailable={!health.data?.reranker_available}
          />
        </div>
      </div>
    </section>
  );
}

function ModelStatus({
  label,
  model,
  loaded,
  cached,
  unavailable = false,
}: {
  label: string;
  model?: string | null;
  loaded?: boolean;
  cached?: boolean;
  unavailable?: boolean;
}) {
  return (
    <div className="rounded-md border border-border p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="font-medium">{label}</div>
        <StatusPill status={unavailable ? "unavailable" : loaded ? "loaded" : cached ? "cached" : "not cached"} />
      </div>
      <div className="mt-2 break-all text-muted-foreground">{model ?? "none"}</div>
    </div>
  );
}
