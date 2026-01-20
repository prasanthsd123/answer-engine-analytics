import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(num: number): string {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + "M";
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K";
  }
  return num.toString();
}

export function formatPercent(num: number): string {
  return `${num >= 0 ? "+" : ""}${num.toFixed(1)}%`;
}

export function getSentimentColor(sentiment: string): string {
  switch (sentiment?.toLowerCase()) {
    case "positive":
      return "text-green-600";
    case "negative":
      return "text-red-600";
    default:
      return "text-gray-600";
  }
}

export function getScoreColor(score: number): string {
  if (score >= 70) return "text-green-600";
  if (score >= 40) return "text-yellow-600";
  return "text-red-600";
}

export function getScoreBgColor(score: number): string {
  if (score >= 70) return "bg-green-100";
  if (score >= 40) return "bg-yellow-100";
  return "bg-red-100";
}
