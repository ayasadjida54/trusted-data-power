import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const BAR_COLOR = (value) => {
  if (value >= 85) return "#1BAA5E";
  if (value >= 65) return "#17B6E0";
  if (value >= 40) return "#F5A623";
  return "#E0524C";
};

export default function DimensionBarChart({ dimensionScores, dimensionWeights }) {
  const data = Object.entries(dimensionScores).map(([name, value]) => ({
    name,
    value: Math.round(value * 10) / 10,
    weight: dimensionWeights?.[name],
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} layout="vertical" margin={{ left: 24, right: 24 }}>
        <CartesianGrid horizontal={false} stroke="#E3E7EE" />
        <XAxis type="number" domain={[0, 100]} tick={{ fill: "#6B7686", fontSize: 12 }} />
        <YAxis
          type="category"
          dataKey="name"
          width={140}
          tick={{ fill: "#0B2545", fontSize: 12 }}
        />
        <Tooltip
          formatter={(value, key, entry) => [
            `${value} / 100${entry.payload.weight ? ` · weight ${Math.round(entry.payload.weight * 100)}%` : ""}`,
            "Score",
          ]}
          contentStyle={{ borderRadius: 12, borderColor: "#E3E7EE" }}
        />
        <Bar dataKey="value" radius={[0, 8, 8, 0]} barSize={18}>
          {data.map((entry) => (
            <Cell key={entry.name} fill={BAR_COLOR(entry.value)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
