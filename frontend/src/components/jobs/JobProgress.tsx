import { StatusPill } from "@/components/common/StatusPill";
import type { JobInfo } from "@/types/api";

export function JobProgress({ job }: { job: JobInfo }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{job.job_id}</div>
          <div className="mt-1 text-xs text-muted-foreground">
            {job.current_stage || "Waiting"} · source {job.source_id.slice(0, 12)}
          </div>
        </div>
        <StatusPill status={job.status} />
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full bg-primary transition-all" style={{ width: `${Math.max(0, Math.min(100, job.progress))}%` }} />
      </div>
      {job.error_message ? <p className="mt-3 text-sm text-destructive">{job.error_message}</p> : null}
    </div>
  );
}
