export default function DeltaBadge({ value, invertColor = false }) {
  if (value === 0) {
    return <span className="text-xs font-medium text-muted">no change</span>;
  }

  const isPositive = value > 0;
  const isGood = invertColor ? !isPositive : isPositive;
  const color = isGood ? "text-success" : "text-danger";
  const sign = isPositive ? "+" : "";

  return (
    <span className={`text-xs font-semibold ${color}`}>
      {sign}
      {value}
    </span>
  );
}
