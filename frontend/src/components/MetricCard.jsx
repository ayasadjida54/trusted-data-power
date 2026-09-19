export default function MetricCard({ label, value, sublabel }) {
  return (
    <div className="rounded-lg border border-border bg-white p-4 shadow-card">
      <div className="text-xs font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-navy">{value}</div>
      {sublabel && <div className="mt-0.5 text-xs text-muted">{sublabel}</div>}
    </div>
  );
}
