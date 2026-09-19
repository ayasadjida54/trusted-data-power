import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import IssuesTable from "../components/IssuesTable";
import { getLatestRun } from "../api/client";

export default function FindingsPage() {
  const { datasetId } = useParams();
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setRun(null);
    setError(null);
    getLatestRun(datasetId)
      .then(setRun)
      .catch(() => setError("Couldn't load this dataset's findings."));
  }, [datasetId]);

  if (error) {
    return (
      <div className="mx-auto max-w-5xl px-8 py-12">
        <div className="rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger">{error}</div>
      </div>
    );
  }

  if (!run) {
    return <div className="mx-auto max-w-5xl px-8 py-12 text-sm text-muted">Loading…</div>;
  }

  return (
    <div className="mx-auto max-w-5xl px-8 py-12">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-navy">Findings</h1>
          <p className="mt-1 text-sm text-muted">{run.filename}</p>
        </div>
        <Link
          to={`/datasets/${datasetId}`}
          className="rounded-lg border border-border bg-white px-4 py-2.5 text-sm font-semibold text-navy hover:border-cyan/50"
        >
          Back to dashboard
        </Link>
      </div>

      <IssuesTable issues={run.issues} />
    </div>
  );
}
