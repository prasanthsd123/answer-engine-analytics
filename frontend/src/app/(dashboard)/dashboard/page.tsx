"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  TrendingUp,
  TrendingDown,
  MessageSquare,
  Eye,
  ThumbsUp,
  BarChart2,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { VisibilityGauge } from "@/components/charts/VisibilityGauge";
import { TrendChart } from "@/components/charts/TrendChart";
import { PlatformBreakdown } from "@/components/charts/PlatformBreakdown";
import { brandApi, analysisApi } from "@/lib/api";
import { cn, getScoreColor, getSentimentColor } from "@/lib/utils";

export default function DashboardPage() {
  const [selectedBrandId, setSelectedBrandId] = useState<string | null>(null);

  // Fetch brands
  const { data: brandsData } = useQuery({
    queryKey: ["brands"],
    queryFn: () => brandApi.list(1, 10),
  });

  const brands = brandsData?.items || [];
  const activeBrandId = selectedBrandId || brands[0]?.id;

  // Fetch overview for selected brand
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ["overview", activeBrandId],
    queryFn: () => analysisApi.getOverview(activeBrandId),
    enabled: !!activeBrandId,
  });

  // Fetch visibility trends
  const { data: visibilityTrends } = useQuery({
    queryKey: ["trends", activeBrandId, "visibility"],
    queryFn: () => analysisApi.getTrends(activeBrandId, "visibility", 30),
    enabled: !!activeBrandId,
  });

  // Mock data for demo (replace with real data)
  const mockPlatformData = [
    { name: "ChatGPT", value: 35 },
    { name: "Claude", value: 25 },
    { name: "Perplexity", value: 25 },
    { name: "Gemini", value: 15 },
  ];

  const mockTrendData = Array.from({ length: 30 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (29 - i));
    return {
      date: date.toISOString().split("T")[0],
      value: 40 + Math.random() * 30,
    };
  });

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">
            Monitor your brand visibility across AI search engines
          </p>
        </div>

        {/* Brand Selector */}
        <div className="flex items-center gap-4">
          <select
            value={activeBrandId || ""}
            onChange={(e) => setSelectedBrandId(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            {brands.map((brand: any) => (
              <option key={brand.id} value={brand.id}>
                {brand.name}
              </option>
            ))}
          </select>
          <Button
            onClick={() => {
              if (activeBrandId) {
                analysisApi.triggerAnalysis(activeBrandId);
              }
            }}
          >
            Run Analysis
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardContent className="flex items-center gap-4">
            <div className="p-3 bg-primary-100 rounded-lg">
              <Eye className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Visibility Score</p>
              <p className={cn("text-2xl font-bold", getScoreColor(overview?.visibility_score || 0))}>
                {overview?.visibility_score?.toFixed(1) || "0"}
              </p>
              <p className={cn("text-xs", overview?.visibility_change >= 0 ? "text-green-600" : "text-red-600")}>
                {overview?.visibility_change >= 0 ? "+" : ""}
                {overview?.visibility_change?.toFixed(1) || "0"}% from last period
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <ThumbsUp className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Sentiment</p>
              <p className={cn("text-2xl font-bold capitalize", getSentimentColor(overview?.sentiment_label || "neutral"))}>
                {overview?.sentiment_label || "Neutral"}
              </p>
              <p className="text-xs text-gray-500">
                Score: {overview?.sentiment_score?.toFixed(2) || "0.00"}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <MessageSquare className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Mentions</p>
              <p className="text-2xl font-bold text-gray-900">
                {overview?.total_mentions || 0}
              </p>
              <p className="text-xs text-gray-500">Across all platforms</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center gap-4">
            <div className="p-3 bg-orange-100 rounded-lg">
              <BarChart2 className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Share of Voice</p>
              <p className="text-2xl font-bold text-gray-900">
                {overview?.share_of_voice?.toFixed(1) || "0"}%
              </p>
              <p className="text-xs text-gray-500">vs competitors</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Visibility Gauge */}
        <Card>
          <CardHeader>
            <CardTitle>AI Visibility Score</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center py-4">
            <VisibilityGauge
              score={overview?.visibility_score || 0}
              change={overview?.visibility_change}
              size="lg"
            />
          </CardContent>
        </Card>

        {/* Visibility Trend */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Visibility Trend (30 days)</CardTitle>
          </CardHeader>
          <CardContent>
            <TrendChart
              data={visibilityTrends?.data_points || mockTrendData}
              height={220}
            />
          </CardContent>
        </Card>
      </div>

      {/* Platform Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Platform Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <PlatformBreakdown data={mockPlatformData} />
          </CardContent>
        </Card>

        {/* Platform Scores Table */}
        <Card>
          <CardHeader>
            <CardTitle>Platform Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {Object.entries(overview?.platform_scores || {}).length > 0 ? (
                Object.entries(overview.platform_scores).map(([platform, score]: [string, any]) => (
                  <div key={platform} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          "w-3 h-3 rounded-full",
                          platform === "chatgpt" ? "bg-[#10a37f]" :
                          platform === "claude" ? "bg-[#d97706]" :
                          platform === "perplexity" ? "bg-[#6366f1]" :
                          "bg-[#4285f4]"
                        )}
                      />
                      <span className="text-sm font-medium capitalize">{platform}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary-600 rounded-full"
                          style={{ width: `${score}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-600 w-12 text-right">
                        {score.toFixed(0)}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-8">
                  No platform data available yet.
                  <br />
                  <span className="text-sm">Run an analysis to see results.</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
