import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import DeltaBadge from "../components/DeltaBadge";
import SeverityBadge from "../components/SeverityBadge";
import { listRuns, compareRuns } from "../api/client";

function IssueList({ title, issues, emptyText }) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{title}</h3>
      {issues.length === 0 ? (
        <p className="text-xs text-muted">{emptyText}</p>
      ) : (
        <ul className="space-y-2">
          {issues.map((issue, idx) => (
            <li key={idx} className="flex items-start gap-2 rounded-lg border border-border bg-white p-3">
              <SeverityBadge severity={issue.severity} />
              <div className="text-xs text-navy">
                <div className="font-medium">{issue.category}</div>
                <div className="text-muted">
                  {issue.columns && issue.columns.length > 0 ? issue.columns.join(", ") : "dataset-wide"}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function ComparePage() {
  const { datasetId } = useParams();
  const [runs, setRuns] = useState(null);
  const [runAId, setRunAId] = useState("");
  const [runBId, setRunBId] = useState("");
  const [comparison, setComparison] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    listRuns(datasetId)
      .then((data) => {
        setRuns(data);
        if (data.length >= 2) {
          setRunAId(String(data[data.length - 2].id));
          setRunBId(String(data[data.length - 1].id));
        }
      })
      .catch(() => setError("Couldn't load this dataset's run history."));
  }, [datasetId]);

  useEffect(() => {
    if (!runAId || !runBId || runAId === runBId) {
      setComparison(null);
      return;
    }
    setError(null);
    compareRuns(datasetId, runAId, runBId)
      .then(setComparison)
      .catch(() => setError("Couldn't compare these two runs."));
  }, [datasetId, runAId, runBId]);

  if (error && !runs) {
    return (
      <div className="mx-auto max-w-4xl px-8 py-12">
        <div className="rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger">{error}</div>
      </div>
    );
  }

  if (!runs) {
    return <div className="mx-auto max-w-4xl px-8 py-12 text-sm text-muted">Loading…</div>;
  }

  return (
    <div className="mx-auto max-w-4xl px-8 py-12">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-navy">Compare runs</h1>
        <Link
          to={`/datasets/${datasetId}/trend`}
          className="rounded-lg border border-border bg-white px-4 py-2.5 text-sm font-semibold text-navy hover:border-cyan/50"
        >
          Back to trend
        </Link>
      </div>

      {runs.length < 2 ? (
        <div className="rounded-xl border border-dashed border-border bg-white px-8 py-16 text-center">
          <p className="text-sm font-medium text-navy">Need at least two runs to compare</p>
        </div>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">
                Earlier run
              </label>
              <select
                value={runAId}
                onChange={(e) => setRunAId(e.target.value)}
                className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-navy outline-none focus:border-cyan"
              >
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.filename} — {new Date(run.created_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted">
                Later run
              </label>
              <select
                value={runBId}
                onChange={(e) => setRunBId(e.target.value)}
                className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-navy outline-none focus:border-cyan"
              >
                {runs.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.filename} — {new Date(run.created_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {error && (
            <div className="mb-6 rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger">{error}</div>
          )}

          {runAId === runBId && (
            <div className="rounded-xl border border-dashed border-border bg-white px-8 py-12 text-center text-sm text-muted">
              Pick two different runs to compare.
            </div>
          )}

          {comparison && (
            <div className="space-y-8">
              <div className="rounded-xl border border-border bg-white p-6 shadow-card">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-muted">Score change</div>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-lg text-muted line-through">{comparison.previous_score}</span>
                      <span className="text-2xl font-semibold text-navy">{comparison.current_score}</span>
                      <DeltaBadge value={comparison.score_delta} />
                    </div>
                  </div>
                </div>

                <ul className="mt-4 space-y-1.5 border-t border-border pt-4">
                  {comparison.summary.map((sentence, idx) => (
                    <li key={idx} className="flex gap-2 text-sm text-navy">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-cyan" />
                      <span>{sentence}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-xl border border-border bg-white p-6 shadow-card">
                <h2 className="mb-4 text-sm font-semibold text-navy">Dimension changes</h2>
                <div className="space-y-2">
                  {Object.entries(comparison.dimension_deltas).map(([dimension, delta]) => (
                    <div key={dimension} className="flex items-center justify-between text-sm">
                      <span className="text-navy">{dimension}</span>
                      <DeltaBadge value={delta} />
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <IssueList
                  title="New issues"
                  issues={comparison.new_issues}
                  emptyText="No new issues appeared."
                />
                <IssueList
                  title="Resolved issues"
                  issues={comparison.resolved_issues}
                  emptyText="No issues were resolved."
                />
                <IssueList
                  title="Got worse"
                  issues={comparison.worsened_issues}
                  emptyText="Nothing got worse."
                />
                <IssueList
                  title="Improved"
                  issues={comparison.improved_issues}
                  emptyText="Nothing improved."
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
