import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import DeltaBadge from "../components/DeltaBadge";
import { listAlerts, markAlertRead } from "../api/client";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    listAlerts()
      .then(setAlerts)
      .catch(() => setError("Couldn't load alerts."));
  }, []);

  async function handleMarkRead(alertId) {
    try {
      await markAlertRead(alertId);
      setAlerts((current) =>
        current.map((a) => (a.id === alertId ? { ...a, is_read: true } : a))
      );
    } catch {
      /* leave it unread if the request failed */
    }
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-8 py-12">
        <div className="rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger">{error}</div>
      </div>
    );
  }

  if (!alerts) {
    return <div className="mx-auto max-w-3xl px-8 py-12 text-sm text-muted">Loading…</div>;
  }

  return (
    <div className="mx-auto max-w-3xl px-8 py-12">
      <h1 className="text-2xl font-semibold text-navy">Alerts</h1>
      <p className="mt-1 text-sm text-muted">
        Automatic notices when a monitored dataset's score drops past its threshold.
      </p>

      {alerts.length === 0 ? (
        <div className="mt-8 rounded-xl border border-dashed border-border bg-white px-8 py-16 text-center">
          <p className="text-sm font-medium text-navy">No alerts</p>
          <p className="mt-1 text-sm text-muted">
            Turn on monitoring for a dataset from its dashboard to get notified here.
          </p>
        </div>
      ) : (
        <div className="mt-8 space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`rounded-lg border p-4 shadow-card ${
                alert.is_read ? "border-border bg-white" : "border-cyan/40 bg-cyan-pale"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    {!alert.is_read && <span className="h-2 w-2 rounded-full bg-cyan" />}
                    <span className="text-sm font-medium text-navy">
                      Score dropped <DeltaBadge value={alert.score_delta} />
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-muted">
                    {new Date(alert.created_at).toLocaleString()}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Link
                    to={`/datasets/${alert.dataset_id}/compare`}
                    className="whitespace-nowrap rounded-lg border border-border bg-white px-3 py-1.5 text-xs font-semibold text-navy hover:border-cyan/50"
                  >
                    View comparison
                  </Link>
                  {!alert.is_read && (
                    <button
                      onClick={() => handleMarkRead(alert.id)}
                      className="whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium text-muted hover:text-navy"
                    >
                      Mark read
                    </button>
                  )}
                </div>
              </div>

              <ul className="mt-3 space-y-1 border-t border-border pt-3">
                {alert.summary.map((sentence, idx) => (
                  <li key={idx} className="text-xs text-navy">
                    {sentence}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
