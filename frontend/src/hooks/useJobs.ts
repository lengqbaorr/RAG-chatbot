import { useQuery } from "@tanstack/react-query";

import { listJobs } from "@/api/jobs";

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: listJobs,
    refetchInterval: 2_000,
  });
}
