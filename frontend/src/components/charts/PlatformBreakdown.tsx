"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from "recharts";

interface PlatformData {
  name: string;
  value: number;
  color: string;
}

interface PlatformBreakdownProps {
  data: PlatformData[];
  height?: number;
}

const PLATFORM_COLORS: Record<string, string> = {
  chatgpt: "#10a37f",
  claude: "#d97706",
  perplexity: "#6366f1",
  gemini: "#4285f4",
};

export function PlatformBreakdown({
  data,
  height = 250,
}: PlatformBreakdownProps) {
  const chartData = data.map((d) => ({
    ...d,
    color: PLATFORM_COLORS[d.name.toLowerCase()] || "#6b7280",
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
          nameKey="name"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: "white",
            border: "1px solid #e5e7eb",
            borderRadius: "8px",
            padding: "8px 12px",
          }}
          formatter={(value: number) => [`${value.toFixed(1)}%`, "Share"]}
        />
        <Legend
          verticalAlign="bottom"
          height={36}
          formatter={(value) => (
            <span className="text-sm text-gray-600 capitalize">{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
