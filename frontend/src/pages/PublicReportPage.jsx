import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ScoreGauge from "../components/ScoreGauge";
import MetricCard from "../components/MetricCard";
import DimensionBarChart from "../components/DimensionBarChart";
import ScoreExplanation from "../components/ScoreExplanation";
import RecommendationsList from "../components/RecommendationsList";
import IssuesTable from "../components/IssuesTable";
import Logo from "../components/Logo";
import { getPublicReport, publicPdfReportUrl } from "../api/client";

export default function PublicReportPage() {
  const { token } = useParams();
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getPublicReport(token)
      .then(setRun)
      .catch(() => setError("This report link is invalid or has been revoked."));
  }, [token]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface px-6">
        <div className="max-w-sm text-center">
          <p className="text-sm font-medium text-navy">{error}</p>
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface text-sm text-muted">
        Loading…
      </div>
    );
  }

  const { profile, issue_counts: issueCounts } = run;

  return (
    <div className="min-h-screen bg-surface">
      <header className="border-b border-border bg-navy px-8 py-4">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <div className="flex items-center gap-2 text-white">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10">
              <Logo size={18} />
            </div>
            <span className="text-sm font-semibold">Trusted Data Power</span>
          </div>
          <a
            href={publicPdfReportUrl(token)}
            className="rounded-lg bg-white/10 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/20"
          >
            Download PDF
          </a>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-8 py-12">
        <div className="mb-2 inline-block rounded-full bg-cyan-pale px-3 py-1 text-xs font-medium text-cyan">
          Read-only shared report
        </div>
        <h1 className="text-2xl font-semibold text-navy">{run.filename}</h1>
        <p className="mt-1 text-sm text-muted">
          {profile.n_rows.toLocaleString()} rows · {profile.n_columns} columns
        </p>

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[auto_1fr]">
          <div className="rounded-xl border border-border bg-white p-6 shadow-card">
            <ScoreGauge score={run.score} label={run.score_label} />
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
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
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <MetricCard label="Critical findings" value={issueCounts.Critical} />
          <MetricCard label="Warnings" value={issueCounts.Warning} />
          <MetricCard label="Good" value={issueCounts.Good} />
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
            <h2 className="mb-4 text-sm font-semibold text-navy">Why this score</h2>
            <ScoreExplanation sentences={run.score_explanation} />
          </div>
        </div>

        <div className="mt-8">
          <h2 className="mb-4 text-sm font-semibold text-navy">Top recommendations</h2>
          <RecommendationsList recommendations={run.recommendations} />
        </div>

        <div className="mt-8">
          <h2 className="mb-4 text-sm font-semibold text-navy">Findings</h2>
          <IssuesTable issues={run.issues} />
        </div>
      </div>
    </div>
  );
}
