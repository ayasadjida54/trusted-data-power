import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ScoreGauge from "../components/ScoreGauge";
import CleaningPipelineAction from "../components/CleaningPipelineAction";
import MetricCard from "../components/MetricCard";
import DimensionBarChart from "../components/DimensionBarChart";
import RecommendationsList from "../components/RecommendationsList";
import ScoreExplanation from "../components/ScoreExplanation";
import ReportActions from "../components/ReportActions";
import MonitoringToggle from "../components/MonitoringToggle";
import DataSourceCard from "../components/DataSourceCard";

import { getLatestRun } from "../api/client";

export default function DashboardPage() {
  const { datasetId } = useParams();
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    setRun(null);
    setError(null);
    getLatestRun(datasetId)
      .then(setRun)
      .catch(() => setError("Couldn't load this dataset's analysis."));
  }, [datasetId, refreshKey]);

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-8 py-12">
        <div className="rounded-lg bg-danger-bg px-4 py-3 text-sm text-danger">{error}</div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="mx-auto max-w-4xl px-8 py-12 text-sm text-muted">Loading…</div>
    );
  }

  const { profile, issue_counts: issueCounts } = run;

  return (
    <div className="mx-auto max-w-5xl px-8 py-12">
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-navy">{run.filename}</h1>
          <p className="mt-1 text-sm text-muted">
            {profile.n_rows.toLocaleString()} rows · {profile.n_columns} columns
          </p>
        </div>
        <div className="flex gap-2">
          <ReportActions runId={run.id} filename={run.filename} />
          <Link
            to={`/datasets/${datasetId}/trend`}
            className="rounded-lg border border-border bg-white px-4 py-2.5 text-sm font-semibold text-navy hover:border-cyan/50"
          >
            View trend
          </Link>
          <Link
            to={`/datasets/${datasetId}/findings`}
            className="rounded-lg border border-border bg-white px-4 py-2.5 text-sm font-semibold text-navy hover:border-cyan/50"
          >
            View all findings
          </Link>
        </div>
      </div>

      <div className="max-w-[280px] rounded-xl border border-border bg-white p-6 shadow-card">
        <ScoreGauge score={run.score} label={run.score_label} />
        <div className="mt-5 border-t border-border pt-5">
          <CleaningPipelineAction
            run={run}
            datasetId={datasetId}
            onCleaned={() => setRefreshKey((k) => k + 1)}
          />
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard label="Rows" value={profile.n_rows.toLocaleString()} />
        <MetricCard label="Columns" value={profile.n_columns} />
        <MetricCard
          label="Missing cells"
          value={`${profile.missing_cells_pct}%`}
          sublabel={`${profile.total_missing_cells.toLocaleString()} cells`}
        />
        <MetricCard
          label="Duplicate rows"
          value={`${profile.duplicate_rows_pct}%`}
          sublabel={`${profile.duplicate_rows.toLocaleString()} rows`}
        />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard label="Critical findings" value={issueCounts.Critical} />
        <MetricCard label="Warnings" value={issueCounts.Warning} />
        <MetricCard label="Good" value={issueCounts.Good} />
      </div>

      <div className="mt-8">
        <DataSourceCard datasetId={datasetId} onSynced={() => setRefreshKey((k) => k + 1)} />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-white p-6 shadow-card">
          <h2 className="mb-4 text-sm font-semibold text-navy">Score breakdown by dimension</h2>
          <DimensionBarChart
            dimensionScores={run.dimension_scores}
            dimensionWeights={run.dimension_weights}
          />
        </div>

        <div className="rounded-xl border border-border bg-white p-6 shadow-card">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-navy">Why this score</h2>
            <Link
              to={`/datasets/${datasetId}/columns`}
              className="text-xs font-medium text-cyan hover:underline"
            >
              See column-by-column breakdown →
            </Link>
          </div>
          <ScoreExplanation sentences={run.score_explanation} />
        </div>
      </div>

      <div className="mt-8">
        <h2 className="mb-4 text-sm font-semibold text-navy">Top recommendations</h2>
        <RecommendationsList recommendations={run.recommendations} />
      </div>

      <div className="mt-8">
        <MonitoringToggle datasetId={datasetId} />
      </div>
    </div>
  );
}
