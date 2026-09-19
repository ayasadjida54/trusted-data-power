import { useEffect, useState } from "react";
import { getDatasource, syncDatasetNow, unlinkDatasource } from "../api/client";

const INTERVAL_LABELS = {
  60: "Hourly",
  1440: "Daily",
  10080: "Weekly",
};

export default function DataSourceCard({ datasetId, onSynced }) {
  const [datasource, setDatasource] = useState(undefined); // undefined = loading, null = not linked
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDatasource(datasetId)
      .then(setDatasource)
      .catch(() => setDatasource(null));
  }, [datasetId]);

  async function handleSyncNow() {
    setIsSyncing(true);
    setError(null);
    try {
      await syncDatasetNow(datasetId);
      const updated = await getDatasource(datasetId);
      setDatasource(updated);
      onSynced?.();
    } catch (err) {
      setError(err.message);
      const updated = await getDatasource(datasetId).catch(() => null);
      setDatasource(updated);
    } finally {
      setIsSyncing(false);
    }
  }

  async function handleUnlink() {
    setIsSyncing(true);
    try {
      await unlinkDatasource(datasetId);
      setDatasource(null);
    } catch {
      setError("Couldn't disconnect this source.");
    } finally {
      setIsSyncing(false);
    }
  }

  if (!datasource) return null; // loading, or nothing linked - nothing to show

  return (
    <div className="rounded-xl border border-border bg-white p-6 shadow-card">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-navy">Connected Google Sheet</h2>
          <p className="mt-1 truncate text-xs text-muted" style={{ maxWidth: 360 }}>
            {datasource.source_url}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSyncNow}
            disabled={isSyncing}
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-navy hover:border-cyan/50 disabled:opacity-50"
          >
            {isSyncing ? "Syncing…" : "Sync now"}
          </button>
          <button
            onClick={handleUnlink}
            disabled={isSyncing}
            className="rounded-lg px-3 py-1.5 text-xs font-medium text-muted hover:text-danger disabled:opacity-50"
          >
            Disconnect
          </button>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-3 border-t border-border pt-3 text-xs text-muted">
        <span>
          {datasource.sync_interval_minutes
            ? `Auto-sync: ${INTERVAL_LABELS[datasource.sync_interval_minutes] || `every ${datasource.sync_interval_minutes} min`}`
            : "Manual sync only"}
        </span>
        {datasource.last_synced_at && (
          <span>· Last synced {new Date(datasource.last_synced_at).toLocaleString()}</span>
        )}
        {datasource.last_sync_status === "error" && (
          <span className="font-medium text-danger">· Last sync failed</span>
        )}
      </div>

      {datasource.last_sync_status === "error" && datasource.last_sync_error && (
        <div className="mt-2 rounded-lg bg-danger-bg px-3 py-2 text-xs text-danger">
          {datasource.last_sync_error}
        </div>
      )}

      {error && <div className="mt-2 text-xs text-danger">{error}</div>}
    </div>
  );
}
