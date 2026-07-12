import { useMutation, useQuery } from "@tanstack/react-query";

import { getRuntimeSettings, resetRuntimeSettings, updateRuntimeSettings } from "@/api/settings";
import { queryClient } from "@/services/queryClient";
import { useSettingsStore } from "@/store/settingsStore";

export function useRuntimeSettings() {
  return useQuery({
    queryKey: ["runtime-settings"],
    queryFn: getRuntimeSettings,
    staleTime: 60_000,
  });
}

export function useUpdateRuntimeSettings() {
  const applyRuntimeSettings = useSettingsStore((state) => state.applyRuntimeSettings);
  return useMutation({
    mutationFn: updateRuntimeSettings,
    onSuccess: (settings) => {
      applyRuntimeSettings(settings);
      queryClient.setQueryData(["runtime-settings"], settings);
    },
  });
}

export function useResetRuntimeSettings() {
  const applyRuntimeSettings = useSettingsStore((state) => state.applyRuntimeSettings);
  return useMutation({
    mutationFn: resetRuntimeSettings,
    onSuccess: (settings) => {
      applyRuntimeSettings(settings);
      queryClient.setQueryData(["runtime-settings"], settings);
    },
  });
}
