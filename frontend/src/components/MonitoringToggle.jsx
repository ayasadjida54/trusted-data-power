import { useEffect, useState } from "react";
import { getMonitoringSettings, updateMonitoringSettings } from "../api/client";

export default function MonitoringToggle({ datasetId }) {
  const [settings, setSettings] = useState(null);
  const [threshold, setThreshold] = useState("5");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMonitoringSettings(datasetId)
      .then((data) => {
        setSettings(data);
        setThreshold(String(data.alert_threshold_points));
      })
      .catch(() => setError("Couldn't load monitoring settings."));
  }, [datasetId]);

  async function handleToggle() {
    if (!settings) return;
    const nextEnabled = !settings.monitoring_enabled;
    setIsSaving(true);
    setError(null);
    try {
      const updated = await updateMonitoringSettings(
        datasetId,
        nextEnabled,
        parseFloat(threshold) || 5
      );
      setSettings(updated);
    } catch {
      setError("Couldn't update monitoring settings.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleThresholdBlur() {
    if (!settings || !settings.monitoring_enabled) return;
    const parsed = parseFloat(threshold);
    if (!parsed || parsed <= 0) return;
    setIsSaving(true);
    try {
      const updated = await updateMonitoringSettings(datasetId, true, parsed);
      setSettings(updated);
    } catch {
      setError("Couldn't update the threshold.");
    } finally {
      setIsSaving(false);
    }
  }

  if (!settings) return null;

  return (
    <div className="rounded-xl border border-border bg-white p-6 shadow-card">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-navy">Monitoring</h2>
          <p className="mt-1 text-xs text-muted">
            Get an alert when a new upload's score drops too much from the last one.
          </p>
        </div>
        <button
          onClick={handleToggle}
          disabled={isSaving}
          className={`relative h-6 w-11 shrink-0 rounded-full transition ${
            settings.monitoring_enabled ? "bg-cyan" : "bg-panel"
          } disabled:opacity-50`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition ${
              settings.monitoring_enabled ? "left-5" : "left-0.5"
            }`}
          />
        </button>
      </div>

      {settings.monitoring_enabled && (
        <div className="mt-4 flex items-center gap-2 border-t border-border pt-4">
          <label className="text-xs text-muted">Alert when score drops by more than</label>
          <input
            type="number"
            min="0.1"
            step="0.5"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            onBlur={handleThresholdBlur}
            disabled={isSaving}
            className="w-16 rounded-lg border border-border bg-white px-2 py-1 text-sm text-navy outline-none focus:border-cyan"
          />
          <span className="text-xs text-muted">points</span>
        </div>
      )}

      {error && <div className="mt-3 text-xs text-danger">{error}</div>}
    </div>
  );
}
