import { useSettingsStore } from "@/store/settingsStore";

export function SettingsPage() {
  const settings = useSettingsStore();

  return (
    <section className="max-w-3xl space-y-6 p-6">
      <div>
        <h2 className="text-xl font-semibold">Settings</h2>
        <p className="mt-1 text-sm text-muted-foreground">Cấu hình retrieval và generation ở phía client cho mỗi request chat.</p>
      </div>
      <div className="space-y-4 rounded-lg border border-border bg-card p-4">
        <label className="block text-sm">
          <span className="font-medium">Theme</span>
          <select
            className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2"
            value={settings.theme}
            onChange={(event) => settings.setTheme(event.target.value as typeof settings.theme)}
          >
            <option value="system">System</option>
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </label>
        <label className="block text-sm">
          <span className="font-medium">Top K</span>
          <input
            className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2"
            type="number"
            min={1}
            max={20}
            value={settings.topK}
            onChange={(event) => settings.setRetrieval({ topK: Number(event.target.value) })}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Fetch K</span>
          <input
            className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2"
            type="number"
            min={1}
            max={50}
            value={settings.fetchK}
            onChange={(event) => settings.setRetrieval({ fetchK: Number(event.target.value) })}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Min score</span>
          <input
            className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2"
            type="number"
            min={0}
            max={1}
            step={0.01}
            value={settings.minScore}
            onChange={(event) => settings.setRetrieval({ minScore: Number(event.target.value) })}
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Temperature</span>
          <input
            className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2"
            type="number"
            min={0}
            max={2}
            step={0.1}
            value={settings.temperature}
            onChange={(event) => settings.setGeneration({ temperature: Number(event.target.value) })}
          />
        </label>
      </div>
    </section>
  );
}
