import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listDatasets } from "../api/client";

const LABEL_COLOR = {
  Strong: "text-success",
  Moderate: "text-cyan",
  Weak: "text-warning",
  Poor: "text-danger",
};

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    listDatasets()
      .then(setDatasets)
      .catch(() => setError("Couldn't load your datasets. Is the backend running?"));
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-8 py-12">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-navy">Datasets</h1>
          <p className="mt-1 text-sm text-muted">Every dataset you've analyzed, with its latest score.</p>
        </div>
        <Link
          to="/upload"
          className="rounded-lg bg-navy px-4 py-2.5 text-sm font-semibold text-white hover:bg-navy-light"
        >
          Upload dataset
        </Link>
      </div>

      {error && <div className="rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger">{error}</div>}

      {datasets === null && !error && (
        <div className="text-sm text-muted">Loading…</div>
      )}

      {datasets && datasets.length === 0 && (
        <div className="rounded-xl border border-dashed border-border bg-white px-8 py-16 text-center">
          <p className="text-sm font-medium text-navy">No datasets yet</p>
          <p className="mt-1 text-sm text-muted">Upload your first file to get a reliability score.</p>
          <Link
            to="/upload"
            className="mt-4 inline-block rounded-lg bg-navy px-4 py-2.5 text-sm font-semibold text-white hover:bg-navy-light"
          >
            Upload dataset
          </Link>
        </div>
      )}

      {datasets && datasets.length > 0 && (
        <div className="grid gap-3">
          {datasets.map((dataset) => (
            <Link
              key={dataset.id}
              to={`/datasets/${dataset.id}`}
              className="flex items-center justify-between rounded-lg border border-border bg-white p-4 shadow-card transition hover:border-cyan/50"
            >
              <div>
                <div className="text-sm font-medium text-navy">{dataset.name}</div>
                {dataset.latest_run && (
                  <div className="mt-0.5 text-xs text-muted">{dataset.latest_run.filename}</div>
                )}
              </div>
              {dataset.latest_run ? (
                <div className="flex items-center gap-3">
                  <span className="text-lg font-semibold text-navy">{dataset.latest_run.score}</span>
                  <span
                    className={`text-sm font-medium ${LABEL_COLOR[dataset.latest_run.score_label] || "text-muted"}`}
                  >
                    {dataset.latest_run.score_label}
                  </span>
                </div>
              ) : (
                <span className="text-xs text-muted">No runs yet</span>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
