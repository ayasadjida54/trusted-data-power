import SeverityBadge from "./SeverityBadge";

const PREFIX_PATTERN = /^\[(Critical|Warning|Good)\]\s*/;

export default function RecommendationsList({ recommendations }) {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-white p-6 text-sm text-muted">
        No high-priority recommendations right now — the dataset is in good shape.
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {recommendations.map((rec, idx) => {
        const match = rec.match(PREFIX_PATTERN);
        const severity = match ? match[1] : null;
        const text = match ? rec.slice(match[0].length) : rec;

        return (
          <li
            key={idx}
            className="flex items-start gap-3 rounded-lg border border-border bg-white p-4 shadow-card"
          >
            {severity && <SeverityBadge severity={severity} />}
            <span className="text-sm text-navy">{text}</span>
          </li>
        );
      })}
    </ul>
  );
}
