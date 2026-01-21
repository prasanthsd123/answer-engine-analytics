"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Play, RefreshCw, CheckCircle, AlertCircle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { TrendChart } from "@/components/charts/TrendChart";
import { brandApi, analysisApi } from "@/lib/api";
import { cn, getSentimentColor } from "@/lib/utils";

const PLATFORMS = ["chatgpt", "perplexity"] as const;

export default function AnalysisPage() {
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");
  const [timeRange, setTimeRange] = useState<number>(30);
  const [analysisStatus, setAnalysisStatus] = useState<"idle" | "running" | "success" | "error">("idle");
  const queryClient = useQueryClient();

  const { data: brandsData } = useQuery({
    queryKey: ["brands"],
    queryFn: () => brandApi.list(1, 100),
  });

  const brands = brandsData?.items || [];
  const activeBrandId = selectedBrandId || brands[0]?.id;

  const runAnalysisMutation = useMutation({
    mutationFn: () => analysisApi.triggerAnalysis(activeBrandId, [...PLATFORMS]),
    onMutate: () => {
      setAnalysisStatus("running");
    },
    onSuccess: () => {
      setAnalysisStatus("success");
      // Refresh data after a delay to allow analysis to complete
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["competitors", activeBrandId] });
        queryClient.invalidateQueries({ queryKey: ["trends", activeBrandId] });
        queryClient.invalidateQueries({ queryKey: ["overview", activeBrandId] });
      }, 5000);
      // Reset status after showing success
      setTimeout(() => setAnalysisStatus("idle"), 10000);
    },
    onError: () => {
      setAnalysisStatus("error");
      setTimeout(() => setAnalysisStatus("idle"), 5000);
    },
  });

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
          <Button
            onClick={() => runAnalysisMutation.mutate()}
            disabled={!activeBrandId || analysisStatus === "running"}
            className={cn(
              analysisStatus === "success" && "bg-green-600 hover:bg-green-700",
              analysisStatus === "error" && "bg-red-600 hover:bg-red-700"
            )}
          >
            {analysisStatus === "running" ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Running Analysis...
              </>
            ) : analysisStatus === "success" ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2" />
                Analysis Complete
              </>
            ) : analysisStatus === "error" ? (
              <>
                <AlertCircle className="w-4 h-4 mr-2" />
                Analysis Failed
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Run Analysis
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Analysis Status Banner */}
      {analysisStatus === "running" && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center">
            <RefreshCw className="w-5 h-5 mr-3 text-blue-600 animate-spin" />
            <div>
              <p className="font-medium text-blue-800">Analysis in Progress</p>
              <p className="text-sm text-blue-600">
                Querying ChatGPT and Perplexity with your questions. This may take a few minutes...
              </p>
            </div>
          </div>
        </div>
      )}

      {analysisStatus === "success" && (
        <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center">
            <CheckCircle className="w-5 h-5 mr-3 text-green-600" />
            <div>
              <p className="font-medium text-green-800">Analysis Complete</p>
              <p className="text-sm text-green-600">
                Results are being processed. Dashboard will update shortly.
              </p>
            </div>
          </div>
        </div>
      )}

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
