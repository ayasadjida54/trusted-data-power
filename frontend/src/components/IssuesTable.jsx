import { useMemo, useState } from "react";
import SeverityBadge from "./SeverityBadge";

const SEVERITIES = ["Critical", "Warning", "Good"];

export default function IssuesTable({ issues }) {
  const [activeSeverities, setActiveSeverities] = useState(["Critical", "Warning"]);

  const filtered = useMemo(
    () => issues.filter((issue) => activeSeverities.includes(issue.severity)),
    [issues, activeSeverities]
  );

  function toggleSeverity(severity) {
    setActiveSeverities((current) =>
      current.includes(severity)
        ? current.filter((s) => s !== severity)
        : [...current, severity]
    );
  }

  return (
    <div>
      <div className="mb-4 flex gap-2">
        {SEVERITIES.map((severity) => {
          const active = activeSeverities.includes(severity);
          return (
            <button
              key={severity}
              onClick={() => toggleSeverity(severity)}
              className={`rounded-full border px-3 py-1.5 text-sm font-medium transition ${
                active
                  ? "border-navy bg-navy text-white"
                  : "border-border bg-white text-muted hover:border-navy/30"
              }`}
            >
              {severity}
            </button>
          );
        })}
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-lg border border-border bg-white p-8 text-center text-sm text-muted">
          No findings match the selected filters.
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-panel text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Category</th>
                <th className="px-4 py-3 font-medium">Severity</th>
                <th className="px-4 py-3 font-medium">Column(s)</th>
                <th className="px-4 py-3 font-medium">Finding</th>
                <th className="px-4 py-3 font-medium">Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((issue, idx) => (
                <tr key={idx} className="border-t border-border align-top">
                  <td className="px-4 py-3 font-medium text-navy">{issue.category}</td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={issue.severity} />
                  </td>
                  <td className="px-4 py-3 text-muted">
                    {issue.columns && issue.columns.length > 0 ? issue.columns.join(", ") : "—"}
                  </td>
                  <td className="px-4 py-3 text-navy">{issue.metric}</td>
                  <td className="px-4 py-3 text-muted">{issue.recommendation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
