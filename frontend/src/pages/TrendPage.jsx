import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ScoreTrendChart from "../components/ScoreTrendChart";
import { listRuns } from "../api/client";

const LABEL_COLOR = {
  Strong: "text-success",
  Moderate: "text-cyan",
  Weak: "text-warning",
  Poor: "text-danger",
};

export default function TrendPage() {
  const { datasetId } = useParams();
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setRuns(null);
    setError(null);
    listRuns(datasetId)
      .then(setRuns)
      .catch(() => setError("Couldn't load this dataset's run history."));
  }, [datasetId]);

  if (error) {
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
        <div>
          <h1 className="text-2xl font-semibold text-navy">Score trend</h1>
          <p className="mt-1 text-sm text-muted">
            {runs.length} run{runs.length === 1 ? "" : "s"} recorded for this dataset
          </p>
        </div>
        <div className="flex gap-2">
          {runs.length >= 2 && (
            <Link
              to={`/datasets/${datasetId}/compare`}
              className="rounded-lg bg-navy px-4 py-2.5 text-sm font-semibold text-white hover:bg-navy-light"
            >
              Compare runs
            </Link>
          )}
          <Link
            to={`/datasets/${datasetId}`}
            className="rounded-lg border border-border bg-white px-4 py-2.5 text-sm font-semibold text-navy hover:border-cyan/50"
          >
            Back to dashboard
          </Link>
        </div>
      </div>

      {runs.length < 2 ? (
        <div className="rounded-xl border border-dashed border-border bg-white px-8 py-16 text-center">
          <p className="text-sm font-medium text-navy">Not enough history yet</p>
          <p className="mt-1 text-sm text-muted">
            Upload another version of this dataset to start seeing a trend.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-white p-6 shadow-card">
          <ScoreTrendChart runs={runs} />
        </div>
      )}

      <div className="mt-8 space-y-2">
        {[...runs].reverse().map((run) => (
          <div
            key={run.id}
            className="flex items-center justify-between rounded-lg border border-border bg-white px-4 py-3"
          >
            <div>
              <div className="text-sm font-medium text-navy">{run.filename}</div>
              <div className="text-xs text-muted">
                {new Date(run.created_at).toLocaleString()}
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-navy">{run.score}</span>
              <span className={`text-xs font-medium ${LABEL_COLOR[run.score_label] || "text-muted"}`}>
                {run.score_label}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
