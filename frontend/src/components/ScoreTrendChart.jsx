import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

const THRESHOLD_LINES = [
  { y: 85, label: "Strong", color: "#1BAA5E" },
  { y: 65, label: "Moderate", color: "#17B6E0" },
  { y: 40, label: "Weak", color: "#F5A623" },
];

export default function ScoreTrendChart({ runs }) {
  const data = runs.map((run) => ({
    date: new Date(run.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    score: run.score,
    filename: run.filename,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
        <CartesianGrid stroke="#E3E7EE" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: "#6B7686", fontSize: 12 }} />
        <YAxis domain={[0, 100]} tick={{ fill: "#6B7686", fontSize: 12 }} />
        {THRESHOLD_LINES.map((line) => (
          <ReferenceLine
            key={line.label}
            y={line.y}
            stroke={line.color}
            strokeDasharray="4 4"
            strokeOpacity={0.4}
          />
        ))}
        <Tooltip
          formatter={(value, _key, entry) => [`${value} / 100`, entry.payload.filename]}
          contentStyle={{ borderRadius: 12, borderColor: "#E3E7EE" }}
        />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#17B6E0"
          strokeWidth={2.5}
          dot={{ r: 4, fill: "#17B6E0" }}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
