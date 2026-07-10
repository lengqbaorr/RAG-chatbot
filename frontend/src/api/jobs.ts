import { apiRequest } from "@/api/client";
import type { JobInfo, JobListResponse } from "@/types/api";

export function listJobs(): Promise<JobListResponse> {
  return apiRequest<JobListResponse>("/jobs");
}

export function getJob(jobId: string): Promise<JobInfo> {
  return apiRequest<JobInfo>(`/jobs/${jobId}`);
}
