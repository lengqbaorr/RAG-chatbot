import { useEffect } from "react";

import { useRuntimeSettings } from "@/hooks/useRuntimeSettings";
import { useSettingsStore } from "@/store/settingsStore";

export function RuntimeSettingsHydrator() {
  const runtime = useRuntimeSettings();
  const applyRuntimeSettings = useSettingsStore((state) => state.applyRuntimeSettings);

  useEffect(() => {
    if (runtime.data) {
      applyRuntimeSettings(runtime.data);
    }
  }, [applyRuntimeSettings, runtime.data]);

  return null;
}
