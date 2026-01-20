"use client";

import { cn, getScoreColor, getScoreBgColor } from "@/lib/utils";

interface VisibilityGaugeProps {
  score: number;
  change?: number;
  size?: "sm" | "md" | "lg";
}

export function VisibilityGauge({
  score,
  change,
  size = "md",
}: VisibilityGaugeProps) {
  const radius = size === "sm" ? 40 : size === "md" ? 60 : 80;
  const strokeWidth = size === "sm" ? 8 : size === "md" ? 10 : 12;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  const getStrokeColor = (score: number) => {
    if (score >= 70) return "#22c55e";
    if (score >= 40) return "#f59e0b";
    return "#ef4444";
  };

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <svg
          width={(radius + strokeWidth) * 2}
          height={(radius + strokeWidth) * 2}
          className="transform -rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            fill="none"
            stroke={getStrokeColor(score)}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            strokeLinecap="round"
            className="transition-all duration-500"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={cn(
              "font-bold",
              getScoreColor(score),
              size === "sm" ? "text-xl" : size === "md" ? "text-3xl" : "text-4xl"
            )}
          >
            {Math.round(score)}
          </span>
          <span className="text-xs text-gray-500">/ 100</span>
        </div>
      </div>
      {change !== undefined && (
        <div
          className={cn(
            "mt-2 text-sm font-medium",
            change >= 0 ? "text-green-600" : "text-red-600"
          )}
        >
          {change >= 0 ? "+" : ""}
          {change.toFixed(1)}%
        </div>
      )}
    </div>
  );
}
