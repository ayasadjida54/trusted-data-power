const LABEL_COLOR = {
  Strong: "#1BAA5E",
  Moderate: "#17B6E0",
  Weak: "#F5A623",
  Poor: "#E0524C",
};

const SIZE = 168;
const STROKE = 14;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function ScoreGauge({ score, label }) {
  const color = LABEL_COLOR[label] || "#6B7686";
  const progress = Math.max(0, Math.min(100, score)) / 100;
  const dashOffset = CIRCUMFERENCE * (1 - progress);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: SIZE, height: SIZE }}>
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} className="-rotate-90">
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke="#EDEFF2"
            strokeWidth={STROKE}
          />
          <circle
            cx={SIZE / 2}
            cy={SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke={color}
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>
        {/* Absolutely centered within the ring's own box (not a guessed
            negative margin) - this stays correct regardless of the
            actual rendered text height, so content after this box
            (the badge below) can never end up positioned inside the
            ring. */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-navy">{score}</span>
          <span className="text-xs text-muted">out of 100</span>
        </div>
      </div>
      <span
        className="mt-3 rounded-full px-3 py-1 text-sm font-semibold"
        style={{ color, backgroundColor: `${color}1A` }}
      >
        {label}
      </span>
    </div>
  );
}
