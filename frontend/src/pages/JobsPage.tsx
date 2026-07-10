import { EmptyState } from "@/components/common/EmptyState";
import { Spinner } from "@/components/common/Spinner";
import { JobProgress } from "@/components/jobs/JobProgress";
import { useJobs } from "@/hooks/useJobs";

export function JobsPage() {
  const { data, isLoading, isError, error } = useJobs();

  return (
    <section className="space-y-6 p-6">
      <div>
        <h2 className="text-xl font-semibold">Jobs</h2>
        <p className="mt-1 text-sm text-muted-foreground">Theo dõi indexing pipeline: loading, chunking, embedding và upsert vector.</p>
      </div>
      {isLoading ? <div className="flex items-center gap-2 text-sm text-muted-foreground"><Spinner /> Loading jobs</div> : null}
      {isError ? <EmptyState title="Cannot load jobs" description={error.message} /> : null}
      {!isLoading && !isError && !data?.jobs.length ? <EmptyState title="No jobs" description="Upload tài liệu để tạo indexing job." /> : null}
      <div className="grid gap-3 lg:grid-cols-2">
        {data?.jobs.map((job) => <JobProgress key={job.job_id} job={job} />)}
      </div>
    </section>
  );
}
