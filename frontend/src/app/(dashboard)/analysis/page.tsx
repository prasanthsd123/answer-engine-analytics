"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { TrendChart } from "@/components/charts/TrendChart";
import { brandApi, analysisApi } from "@/lib/api";
import { cn, getSentimentColor } from "@/lib/utils";

const PLATFORMS = ["chatgpt", "claude", "perplexity", "gemini"];

export default function AnalysisPage() {
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");
  const [timeRange, setTimeRange] = useState<number>(30);

  const { data: brandsData } = useQuery({
    queryKey: ["brands"],
    queryFn: () => brandApi.list(1, 100),
  });

  const brands = brandsData?.items || [];
  const activeBrandId = selectedBrandId || brands[0]?.id;

  const { data: competitorData } = useQuery({
    queryKey: ["competitors", activeBrandId, timeRange],
    queryFn: () => analysisApi.getCompetitorAnalysis(activeBrandId, timeRange),
    enabled: !!activeBrandId,
  });

  const { data: sentimentTrend } = useQuery({
    queryKey: ["trends", activeBrandId, "sentiment", timeRange],
    queryFn: () => analysisApi.getTrends(activeBrandId, "sentiment", timeRange),
    enabled: !!activeBrandId,
  });

  const { data: mentionsTrend } = useQuery({
    queryKey: ["trends", activeBrandId, "mentions", timeRange],
    queryFn: () => analysisApi.getTrends(activeBrandId, "mentions", timeRange),
    enabled: !!activeBrandId,
  });

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analysis</h1>
          <p className="text-gray-500">
            Deep dive into your brand performance
          </p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={activeBrandId || ""}
            onChange={(e) => setSelectedBrandId(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          >
            {brands.map((brand: any) => (
              <option key={brand.id} value={brand.id}>
                {brand.name}
              </option>
            ))}
          </select>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </div>

      {/* Competitor Comparison */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Competitor Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          {competitorData ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 font-medium text-gray-500">
                      Brand
                    </th>
                    <th className="text-center py-3 px-4 font-medium text-gray-500">
                      Visibility
                    </th>
                    <th className="text-center py-3 px-4 font-medium text-gray-500">
                      Sentiment
                    </th>
                    <th className="text-center py-3 px-4 font-medium text-gray-500">
                      Mentions
                    </th>
                    <th className="text-center py-3 px-4 font-medium text-gray-500">
                      Share of Voice
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b bg-primary-50">
                    <td className="py-3 px-4 font-medium">
                      {competitorData.brand.name}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {competitorData.brand.visibility_score.toFixed(1)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {competitorData.brand.sentiment_score.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {competitorData.brand.mention_count}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {competitorData.brand.share_of_voice.toFixed(1)}%
                    </td>
                  </tr>
                  {competitorData.competitors.map((comp: any) => (
                    <tr key={comp.name} className="border-b">
                      <td className="py-3 px-4">{comp.name}</td>
                      <td className="py-3 px-4 text-center">
                        {comp.visibility_score.toFixed(1)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {comp.sentiment_score.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {comp.mention_count}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {comp.share_of_voice.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              No competitor data available
            </div>
          )}
        </CardContent>
      </Card>

      {/* Trend Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Sentiment Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {sentimentTrend?.data_points?.length > 0 ? (
              <TrendChart
                data={sentimentTrend.data_points}
                color="#22c55e"
                height={250}
              />
            ) : (
              <div className="flex items-center justify-center h-[250px] text-gray-500">
                No sentiment data available
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Mentions Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {mentionsTrend?.data_points?.length > 0 ? (
              <TrendChart
                data={mentionsTrend.data_points}
                color="#6366f1"
                height={250}
              />
            ) : (
              <div className="flex items-center justify-center h-[250px] text-gray-500">
                No mentions data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
