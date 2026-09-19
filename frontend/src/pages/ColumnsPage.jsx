import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ColumnScoreCard from "../components/ColumnScoreCard";
import { getLatestRun } from "../api/client";

export default function ColumnsPage() {
  const { datasetId } = useParams();
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setRun(null);
    setError(null);
    getLatestRun(datasetId)
      .then(setRun)
      .catch(() => setError("Couldn't load this dataset's column scores."));
  }, [datasetId]);

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-8 py-12">
        <div className="rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger">{error}</div>
      </div>
    );
  }

  if (!run) {
    return <div className="mx-auto max-w-4xl px-8 py-12 text-sm text-muted">Loading…</div>;
  }

  const dtypeByColumn = Object.fromEntries(
    run.column_dtypes.map((entry) => [entry.column, entry.dtype])
  );

  // Sort weakest first so the columns that need the most attention are
  // immediately visible at the top of the list.
  const sortedColumns = Object.entries(run.column_scores).sort(
    ([, a], [, b]) => a.score - b.score
  );

  return (
    <div className="mx-auto max-w-3xl px-8 py-12">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-navy">Column reliability</h1>
          <p className="mt-1 text-sm text-muted">{run.filename} — weakest columns first</p>
        </div>
        <Link
          to={`/datasets/${datasetId}`}
          className="rounded-lg border border-border bg-white px-4 py-2.5 text-sm font-semibold text-navy hover:border-cyan/50"
        >
          Back to dashboard
        </Link>
      </div>

      <div className="space-y-3">
        {sortedColumns.map(([name, result]) => (
          <ColumnScoreCard key={name} name={name} dtype={dtypeByColumn[name]} result={result} />
        ))}
      </div>
    </div>
  );
}
