const STYLES = {
  Critical: "bg-danger-bg text-danger",
  Warning: "bg-warning-bg text-warning",
  Good: "bg-success-bg text-success",
};

export default function SeverityBadge({ severity }) {
  const style = STYLES[severity] || "bg-panel text-muted";
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${style}`}>
      {severity}
    </span>
  );
}
