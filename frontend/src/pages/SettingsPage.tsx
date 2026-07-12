import { RotateCcw } from "lucide-react";

import { Button } from "@/components/common/Button";
import { Spinner } from "@/components/common/Spinner";
import {
  useResetRuntimeSettings,
  useRuntimeSettings,
  useUpdateRuntimeSettings,
} from "@/hooks/useRuntimeSettings";
import { useSettingsStore } from "@/store/settingsStore";
import type { RuntimeSettingsUpdate } from "@/types/api";

export function SettingsPage() {
  const settings = useSettingsStore();
  const runtime = useRuntimeSettings();
  const updateRuntime = useUpdateRuntimeSettings();
  const resetRuntime = useResetRuntimeSettings();
  const save = (patch: RuntimeSettingsUpdate) => {
    void updateRuntime.mutateAsync(patch);
  };
  const setNumber = (patch: RuntimeSettingsUpdate, applyLocal: () => void) => {
    applyLocal();
    save(patch);
  };

  return (
    <section className="max-w-5xl space-y-6 p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">Settings</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Cấu hình retrieval và generation cho các request chat tiếp theo.
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => {
            settings.resetRagSettings();
            void resetRuntime.mutateAsync();
          }}
          disabled={resetRuntime.isPending}
          leftIcon={<RotateCcw className="h-4 w-4" />}
        >
          Reset RAG
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-semibold">Retrieval</h3>
          <div className="mt-4 space-y-4">
            <label className="block text-sm">
              <span className="font-medium">Strategy</span>
              <select
                className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-sm"
                value={settings.retrievalStrategy}
                onChange={(event) => {
                  const retrievalStrategy = event.target.value as typeof settings.retrievalStrategy;
                  settings.setRetrieval({ retrievalStrategy });
                  save({ retrieval_strategy: retrievalStrategy });
                }}
              >
                <option value="parent_child">Parent-child</option>
                <option value="dense">Dense</option>
              </select>
            </label>

            <NumberField
              label="Top K"
              min={1}
              max={20}
              value={settings.topK}
              onChange={(value) => settings.setRetrieval({ topK: value })}
              onCommit={(value) => setNumber({ top_k: value }, () => settings.setRetrieval({ topK: value }))}
            />

            <NumberField
              label="Fetch K"
              min={1}
              max={100}
              value={settings.fetchK}
              onChange={(value) => settings.setRetrieval({ fetchK: value })}
              onCommit={(value) => setNumber({ fetch_k: value }, () => settings.setRetrieval({ fetchK: value }))}
            />

            <NumberField
              label="Min score"
              min={0}
              max={1}
              step={0.01}
              value={settings.minScore}
              onChange={(value) => settings.setRetrieval({ minScore: value })}
              onCommit={(value) =>
                setNumber({ min_score: value }, () => settings.setRetrieval({ minScore: value }))
              }
            />

            <label className="flex items-center justify-between gap-4 rounded-md border border-border p-3 text-sm">
              <span>
                <span className="block font-medium">Reranker</span>
                <span className="text-xs text-muted-foreground">
                  Reorder retrieved candidates before building context.
                </span>
              </span>
              <input
                type="checkbox"
                checked={settings.rerankerEnabled}
                onChange={(event) => {
                  settings.setGeneration({ rerankerEnabled: event.target.checked });
                  save({ reranker_enabled: event.target.checked });
                }}
                className="h-4 w-4"
              />
            </label>

            <label className="block text-sm">
              <span className="font-medium">Reranker model</span>
              <input
                className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-sm"
                value={settings.rerankerModel}
                onChange={(event) => settings.setGeneration({ rerankerModel: event.target.value })}
                onBlur={(event) => save({ reranker_model: event.target.value })}
              />
            </label>
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-4">
          <h3 className="text-sm font-semibold">Generation</h3>
          <div className="mt-4 space-y-4">
            <label className="block text-sm">
              <span className="font-medium">Model</span>
              <input
                className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-sm"
                value={settings.model}
                onChange={(event) => settings.setGeneration({ model: event.target.value })}
                onBlur={(event) => save({ llm_model: event.target.value })}
              />
            </label>

            <NumberField
              label="Temperature"
              min={0}
              max={2}
              step={0.1}
              value={settings.temperature}
              onChange={(value) => settings.setGeneration({ temperature: value })}
              onCommit={(value) =>
                setNumber({ llm_temperature: value }, () => settings.setGeneration({ temperature: value }))
              }
            />

            <NumberField
              label="Max tokens"
              min={1}
              max={8192}
              value={settings.maxTokens}
              onChange={(value) => settings.setGeneration({ maxTokens: value })}
              onCommit={(value) =>
                setNumber({ llm_max_tokens: value }, () => settings.setGeneration({ maxTokens: value }))
              }
            />

            <label className="flex items-center justify-between gap-4 rounded-md border border-border p-3 text-sm">
              <span>
                <span className="block font-medium">Streaming</span>
                <span className="text-xs text-muted-foreground">Render câu trả lời realtime bằng SSE.</span>
              </span>
              <input
                type="checkbox"
                checked={settings.streaming}
                onChange={(event) => settings.setGeneration({ streaming: event.target.checked })}
                className="h-4 w-4"
              />
            </label>
          </div>
        </section>
      </div>

      <section className="rounded-lg border border-border bg-card p-4">
        <h3 className="text-sm font-semibold">Runtime</h3>
        {runtime.isLoading ? (
          <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> Loading backend settings
          </div>
        ) : null}
        {runtime.isError ? (
          <p className="mt-4 text-sm text-destructive">{runtime.error.message}</p>
        ) : null}
        {updateRuntime.isError ? (
          <p className="mt-4 text-sm text-destructive">{updateRuntime.error.message}</p>
        ) : null}
        {runtime.data ? (
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
            <RuntimeItem label="App" value={`${runtime.data.app_name} ${runtime.data.app_version}`} />
            <RuntimeItem label="Environment" value={runtime.data.environment} />
            <RuntimeItem label="Auth" value={runtime.data.auth_enabled ? "enabled" : "disabled"} />
            <RuntimeItem label="LLM" value={`${runtime.data.llm_provider}/${runtime.data.llm_model}`} />
            <RuntimeItem label="Embedding" value={runtime.data.embedding_model} />
            <RuntimeItem label="Collection" value={runtime.data.chroma_collection} />
          </dl>
        ) : null}
      </section>
    </section>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step,
  onChange,
  onCommit,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (value: number) => void;
  onCommit: (value: number) => void;
}) {
  const commit = (rawValue: string) => {
    const value = Number(rawValue);
    if (Number.isFinite(value)) onCommit(value);
  };

  return (
    <label className="block text-sm">
      <span className="font-medium">{label}</span>
      <input
        className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-sm"
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => {
          const next = Number(event.target.value);
          if (Number.isFinite(next)) onChange(next);
        }}
        onBlur={(event) => commit(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.currentTarget.blur();
          }
        }}
      />
    </label>
  );
}

function RuntimeItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted p-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 truncate font-medium">{value}</dd>
    </div>
  );
}
