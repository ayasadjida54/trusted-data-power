import { useState } from "react";
import { Link } from "react-router-dom";
import { cleanRun } from "../api/client";

const BoltIcon = ({ color = "#fff" }) => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
    <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" fill={color} />
  </svg>
);

export default function CleaningPipelineAction({ run, datasetId, onCleaned }) {
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleExecute() {
    setIsRunning(true);
    setError(null);
    setResult(null);
    try {
      const cleaned = await cleanRun(run.id);
      setResult(cleaned);
      onCleaned?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRunning(false);
    }
  }

  // This run IS itself a cleaning-pipeline output - show what changed
  // and a way to see the before/after, rather than the "run it" button.
  if (run.cleaned_from_run_id) {
    return (
      <div className="rounded-lg bg-success-bg px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-semibold text-success">
            ✓ This is a cleaned version (DataScore {run.score})
          </span>
          <Link
            to={`/datasets/${datasetId}/compare`}
            className="whitespace-nowrap text-xs font-medium text-success underline"
          >
            Compare to original
          </Link>
        </div>
        {run.cleaning_actions && run.cleaning_actions.length > 0 && (
          <ul className="mt-2 space-y-1">
            {run.cleaning_actions.map((action, idx) => (
              <li key={idx} className="text-xs text-navy/80">
                • {action}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <div>
      <button
        onClick={handleExecute}
        disabled={isRunning}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-navy px-4 py-3 text-sm font-semibold text-white transition hover:bg-navy-light disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isRunning ? (
          <>
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            Running pipeline…
          </>
        ) : (
          <>
            <BoltIcon />
            Execute DataScore Pipeline
          </>
        )}
      </button>
      <p className="mt-2 text-xs text-muted">
        Automatically fixes exact duplicates, whitespace, and inconsistent capitalization.
        Missing values and outliers are left for you to review — see "Why this score" above.
      </p>

      {result && (
        <div className="mt-3 rounded-lg bg-success-bg px-4 py-3 text-sm text-success">
          Pipeline executed — DataScore updated to {result.score} ({result.score_label}).
        </div>
      )}
      {error && (
        <div className="mt-3 rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger">{error}</div>
      )}
    </div>
  );
}
