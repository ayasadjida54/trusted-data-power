import { useState } from "react";

const LABEL_COLOR = {
  Strong: "text-success",
  Moderate: "text-cyan",
  Weak: "text-warning",
  Poor: "text-danger",
};

const BAR_COLOR = {
  Strong: "bg-success",
  Moderate: "bg-cyan",
  Weak: "bg-warning",
  Poor: "bg-danger",
};

export default function ColumnScoreCard({ name, dtype, result }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-border bg-white shadow-card">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
      >
        <div>
          <div className="text-sm font-medium text-navy">{name}</div>
          {dtype && <div className="text-xs text-muted">{dtype}</div>}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-navy">{result.score}</span>
          <span className={`text-sm font-medium ${LABEL_COLOR[result.label] || "text-muted"}`}>
            {result.label}
          </span>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            className={`transition-transform ${expanded ? "rotate-180" : ""}`}
          >
            <path d="M6 9l6 6 6-6" stroke="#6B7686" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border px-5 py-4">
          <div className="mb-4 space-y-2">
            {Object.entries(result.dimension_scores).map(([dimension, score]) => (
              <div key={dimension} className="flex items-center gap-3">
                <span className="w-36 shrink-0 text-xs text-muted">{dimension}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-panel">
                  <div
                    className={`h-full rounded-full ${BAR_COLOR[result.label] || "bg-muted"}`}
                    style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right text-xs text-navy">
                  {Math.round(score)}
                </span>
              </div>
            ))}
          </div>

          <ul className="space-y-1.5">
            {result.explanation.map((sentence, idx) => (
              <li key={idx} className="text-xs text-muted">
                {sentence}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
