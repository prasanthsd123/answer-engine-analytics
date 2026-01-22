"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Play,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  X,
  MessageSquare,
  Target,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Award,
  ThumbsUp,
  ThumbsDown,
  Scale,
  Star,
  Shield,
  Zap,
  DollarSign,
  HeadphonesIcon,
  Puzzle,
  MousePointerClick
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { TrendChart } from "@/components/charts/TrendChart";
import { brandApi, analysisApi } from "@/lib/api";
import { cn, getSentimentColor } from "@/lib/utils";

const PLATFORMS = ["chatgpt", "perplexity"] as const;

interface AspectSentiment {
  aspect: string;
  label: string;
  score: number;
  evidence?: string[];
  mention_count?: number;
}

interface QuestionAnalysis {
  question_id: string;
  question_text: string;
  category: string;
  platforms: {
    [key: string]: {
      brand_mentioned: boolean;
      mention_count: number;
      position: number | null;
      total_in_list: number | null;
      sentiment: string;
      sentiment_score: number;
      competitor_mentions: { [key: string]: { count: number } };
      citations: { url: string; domain: string; title?: string }[];
      // Enhanced analysis fields
      brand_attributed_citations?: number;
      citation_quality?: {
        avg_authority: number;
        source_types: { [key: string]: number };
      };
      mention_type_breakdown?: {
        recommendation: number;
        criticism: number;
        comparison: number;
        neutral: number;
        feature_highlight: number;
      };
      comparison_stats?: {
        total: number;
        wins: number;
        losses: number;
        draws: number;
        targets: { [key: string]: number };
      };
      aspect_sentiments?: AspectSentiment[];
      dominant_aspect?: string;
    };
  };
}

interface DetailedAnalysis {
  brand_id: string;
  brand_name: string;
  summary: {
    total_questions_analyzed: number;
    total_executions: number;
    overall_mention_rate: number;
    overall_sentiment: string;
    overall_position_avg: number | null;
    brand_share_of_voice: number;
    // Enhanced summary fields
    avg_citation_authority?: number;
    total_brand_attributed_citations?: number;
    mention_context_totals?: {
      recommendation: number;
      criticism: number;
      comparison: number;
      neutral: number;
      feature_highlight: number;
    };
    comparison_totals?: {
      wins: number;
      losses: number;
      draws: number;
    };
  };
  by_question: QuestionAnalysis[];
  citation_sources: { domain: string; count: number; percentage: number; source_type?: string; authority_score?: number }[];
  competitor_summary: { [key: string]: { total_mentions: number; share_of_voice: number } };
  // Aggregated aspect sentiment across all responses
  aspect_sentiment_summary?: { [aspect: string]: { avg_score: number; total_mentions: number; label: string } };
}

export default function AnalysisPage() {
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("all");
  const [timeRange, setTimeRange] = useState<number>(30);
  const [analysisStatus, setAnalysisStatus] = useState<"idle" | "running" | "success" | "error">("idle");
  const [expandedQuestions, setExpandedQuestions] = useState<Set<string>>(new Set());
  const [responseModal, setResponseModal] = useState<{ executionId: string; platform: string } | null>(null);
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
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["competitors", activeBrandId] });
        queryClient.invalidateQueries({ queryKey: ["trends", activeBrandId] });
        queryClient.invalidateQueries({ queryKey: ["overview", activeBrandId] });
        queryClient.invalidateQueries({ queryKey: ["detailed", activeBrandId] });
      }, 5000);
      setTimeout(() => setAnalysisStatus("idle"), 10000);
    },
    onError: () => {
      setAnalysisStatus("error");
      setTimeout(() => setAnalysisStatus("idle"), 5000);
    },
  });

  const { data: detailedAnalysis } = useQuery<DetailedAnalysis>({
    queryKey: ["detailed", activeBrandId, timeRange],
    queryFn: () => analysisApi.getDetailedAnalysis(activeBrandId, timeRange),
    enabled: !!activeBrandId,
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

  const toggleQuestion = (questionId: string) => {
    const newExpanded = new Set(expandedQuestions);
    if (newExpanded.has(questionId)) {
      newExpanded.delete(questionId);
    } else {
      newExpanded.add(questionId);
    }
    setExpandedQuestions(newExpanded);
  };

  const getSentimentBadgeColor = (sentiment: string) => {
    switch (sentiment?.toLowerCase()) {
      case "positive":
        return "bg-green-100 text-green-800";
      case "negative":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getAspectIcon = (aspect: string) => {
    switch (aspect) {
      case "pricing":
        return <DollarSign className="w-4 h-4" />;
      case "features":
        return <Zap className="w-4 h-4" />;
      case "support":
        return <HeadphonesIcon className="w-4 h-4" />;
      case "ease_of_use":
        return <MousePointerClick className="w-4 h-4" />;
      case "performance":
        return <TrendingUp className="w-4 h-4" />;
      case "integration":
        return <Puzzle className="w-4 h-4" />;
      case "security":
        return <Shield className="w-4 h-4" />;
      default:
        return <Star className="w-4 h-4" />;
    }
  };

  const getSourceTypeColor = (sourceType: string) => {
    switch (sourceType) {
      case "review_site":
        return "bg-yellow-100 text-yellow-800";
      case "news":
        return "bg-blue-100 text-blue-800";
      case "community":
        return "bg-purple-100 text-purple-800";
      case "official":
        return "bg-green-100 text-green-800";
      case "blog":
        return "bg-orange-100 text-orange-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  // Calculate aggregated mention context from by_question data
  const aggregatedMentionContext = detailedAnalysis?.by_question?.reduce(
    (acc, q) => {
      Object.values(q.platforms).forEach((platform) => {
        if (platform.mention_type_breakdown) {
          acc.recommendation += platform.mention_type_breakdown.recommendation || 0;
          acc.criticism += platform.mention_type_breakdown.criticism || 0;
          acc.comparison += platform.mention_type_breakdown.comparison || 0;
          acc.neutral += platform.mention_type_breakdown.neutral || 0;
          acc.feature_highlight += platform.mention_type_breakdown.feature_highlight || 0;
        }
      });
      return acc;
    },
    { recommendation: 0, criticism: 0, comparison: 0, neutral: 0, feature_highlight: 0 }
  );

  // Calculate aggregated comparison stats
  const aggregatedComparisonStats = detailedAnalysis?.by_question?.reduce(
    (acc, q) => {
      Object.values(q.platforms).forEach((platform) => {
        if (platform.comparison_stats) {
          acc.wins += platform.comparison_stats.wins || 0;
          acc.losses += platform.comparison_stats.losses || 0;
          acc.draws += platform.comparison_stats.draws || 0;
        }
      });
      return acc;
    },
    { wins: 0, losses: 0, draws: 0 }
  );

  // Calculate aggregated aspect sentiments
  const aggregatedAspectSentiments = detailedAnalysis?.by_question?.reduce(
    (acc: { [key: string]: { scores: number[]; mentions: number } }, q) => {
      Object.values(q.platforms).forEach((platform) => {
        if (platform.aspect_sentiments) {
          platform.aspect_sentiments.forEach((asp) => {
            if (!acc[asp.aspect]) {
              acc[asp.aspect] = { scores: [], mentions: 0 };
            }
            acc[asp.aspect].scores.push(asp.score);
            acc[asp.aspect].mentions += asp.mention_count || 1;
          });
        }
      });
      return acc;
    },
    {}
  );

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analysis</h1>
          <p className="text-gray-500">
            Deep dive into your brand performance across AI platforms
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
                Querying ChatGPT and Perplexity with your questions...
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      {detailedAnalysis?.summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-lg">
                  <MessageSquare className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Mention Rate</p>
                  <p className="text-xl font-bold">
                    {(detailedAnalysis.summary.overall_mention_rate * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-lg">
                  <Target className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Avg Position</p>
                  <p className="text-xl font-bold">
                    {detailedAnalysis.summary.overall_position_avg
                      ? `#${detailedAnalysis.summary.overall_position_avg}`
                      : "N/A"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "p-2 rounded-lg",
                  detailedAnalysis.summary.overall_sentiment === "positive"
                    ? "bg-green-100"
                    : detailedAnalysis.summary.overall_sentiment === "negative"
                    ? "bg-red-100"
                    : "bg-gray-100"
                )}>
                  <BarChart3 className={cn(
                    "w-5 h-5",
                    detailedAnalysis.summary.overall_sentiment === "positive"
                      ? "text-green-600"
                      : detailedAnalysis.summary.overall_sentiment === "negative"
                      ? "text-red-600"
                      : "text-gray-600"
                  )} />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Sentiment</p>
                  <p className={cn(
                    "text-xl font-bold capitalize",
                    getSentimentColor(detailedAnalysis.summary.overall_sentiment)
                  )}>
                    {detailedAnalysis.summary.overall_sentiment}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-lg">
                  <BarChart3 className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">Share of Voice</p>
                  <p className="text-xl font-bold">
                    {detailedAnalysis.summary.brand_share_of_voice.toFixed(1)}%
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Mention Context Breakdown */}
      {aggregatedMentionContext && (
        aggregatedMentionContext.recommendation > 0 ||
        aggregatedMentionContext.criticism > 0 ||
        aggregatedMentionContext.comparison > 0
      ) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Mention Type Distribution */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="w-5 h-5" />
                Mention Context Analysis
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { key: "recommendation", label: "Recommendations", icon: <ThumbsUp className="w-4 h-4 text-green-600" />, color: "bg-green-500" },
                  { key: "criticism", label: "Criticisms", icon: <ThumbsDown className="w-4 h-4 text-red-600" />, color: "bg-red-500" },
                  { key: "comparison", label: "Comparisons", icon: <Scale className="w-4 h-4 text-blue-600" />, color: "bg-blue-500" },
                  { key: "feature_highlight", label: "Feature Highlights", icon: <Star className="w-4 h-4 text-yellow-600" />, color: "bg-yellow-500" },
                  { key: "neutral", label: "Neutral", icon: <MessageSquare className="w-4 h-4 text-gray-600" />, color: "bg-gray-400" },
                ].map((item) => {
                  const count = aggregatedMentionContext[item.key as keyof typeof aggregatedMentionContext] || 0;
                  const total = Object.values(aggregatedMentionContext).reduce((a, b) => a + b, 0);
                  const percentage = total > 0 ? (count / total) * 100 : 0;

                  return count > 0 ? (
                    <div key={item.key} className="flex items-center gap-3">
                      <div className="flex items-center gap-2 w-40">
                        {item.icon}
                        <span className="text-sm font-medium">{item.label}</span>
                      </div>
                      <div className="flex-1">
                        <div className="w-full bg-gray-200 rounded-full h-3">
                          <div
                            className={cn("h-3 rounded-full transition-all", item.color)}
                            style={{ width: `${percentage}%` }}
                          />
                        </div>
                      </div>
                      <span className="text-sm text-gray-600 w-20 text-right">
                        {count} ({percentage.toFixed(0)}%)
                      </span>
                    </div>
                  ) : null;
                })}
              </div>
            </CardContent>
          </Card>

          {/* Comparison Win/Loss */}
          {aggregatedComparisonStats && (
            aggregatedComparisonStats.wins > 0 ||
            aggregatedComparisonStats.losses > 0 ||
            aggregatedComparisonStats.draws > 0
          ) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Award className="w-5 h-5" />
                  Competitive Comparisons
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <p className="text-3xl font-bold text-green-600">{aggregatedComparisonStats.wins}</p>
                    <p className="text-sm text-green-700">Wins</p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-lg">
                    <p className="text-3xl font-bold text-gray-600">{aggregatedComparisonStats.draws}</p>
                    <p className="text-sm text-gray-700">Draws</p>
                  </div>
                  <div className="text-center p-4 bg-red-50 rounded-lg">
                    <p className="text-3xl font-bold text-red-600">{aggregatedComparisonStats.losses}</p>
                    <p className="text-sm text-red-700">Losses</p>
                  </div>
                </div>
                <p className="text-sm text-gray-500 text-center">
                  When AI compares your brand to competitors, these are the outcomes
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Aspect Sentiment Grid */}
      {aggregatedAspectSentiments && Object.keys(aggregatedAspectSentiments).length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Aspect-Based Sentiment Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {Object.entries(aggregatedAspectSentiments).map(([aspect, data]) => {
                const avgScore = data.scores.length > 0
                  ? data.scores.reduce((a, b) => a + b, 0) / data.scores.length
                  : 0;
                const label = avgScore > 0.2 ? "positive" : avgScore < -0.2 ? "negative" : "neutral";

                return (
                  <div
                    key={aspect}
                    className={cn(
                      "p-4 rounded-lg border-2",
                      label === "positive" && "bg-green-50 border-green-200",
                      label === "negative" && "bg-red-50 border-red-200",
                      label === "neutral" && "bg-gray-50 border-gray-200"
                    )}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className={cn(
                        "p-1.5 rounded",
                        label === "positive" && "bg-green-100 text-green-600",
                        label === "negative" && "bg-red-100 text-red-600",
                        label === "neutral" && "bg-gray-100 text-gray-600"
                      )}>
                        {getAspectIcon(aspect)}
                      </span>
                      <span className="font-medium capitalize text-sm">
                        {aspect.replace(/_/g, " ")}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className={cn(
                        "text-lg font-bold",
                        label === "positive" && "text-green-600",
                        label === "negative" && "text-red-600",
                        label === "neutral" && "text-gray-600"
                      )}>
                        {avgScore > 0 ? "+" : ""}{avgScore.toFixed(2)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {data.mentions} mentions
                      </span>
                    </div>
                    <div className="mt-2 flex items-center gap-1">
                      {label === "positive" && <TrendingUp className="w-3 h-3 text-green-600" />}
                      {label === "negative" && <TrendingDown className="w-3 h-3 text-red-600" />}
                      <span className={cn(
                        "text-xs capitalize",
                        getSentimentBadgeColor(label)
                      )}>
                        {label}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Citation Sources (Enhanced) */}
      {detailedAnalysis?.citation_sources && detailedAnalysis.citation_sources.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Top Citation Sources</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {detailedAnalysis.citation_sources.slice(0, 10).map((source, idx) => (
                <div key={source.domain} className="flex items-center gap-4">
                  <span className="text-sm text-gray-500 w-6">{idx + 1}.</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{source.domain}</span>
                        {source.source_type && (
                          <span className={cn(
                            "px-2 py-0.5 rounded text-xs capitalize",
                            getSourceTypeColor(source.source_type)
                          )}>
                            {source.source_type.replace(/_/g, " ")}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {source.authority_score && (
                          <span className="text-xs text-gray-400" title="Authority Score">
                            ★ {(source.authority_score * 100).toFixed(0)}
                          </span>
                        )}
                        <span className="text-sm text-gray-500">{source.count} citations ({source.percentage}%)</span>
                      </div>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-primary-600 h-2 rounded-full transition-all"
                        style={{ width: `${source.percentage}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Share of Voice Chart */}
      {detailedAnalysis?.competitor_summary && Object.keys(detailedAnalysis.competitor_summary).length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Share of Voice vs Competitors</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {/* Brand */}
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium w-32 truncate">{detailedAnalysis.brand_name}</span>
                <div className="flex-1">
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div
                      className="bg-primary-600 h-4 rounded-full transition-all flex items-center justify-end pr-2"
                      style={{ width: `${Math.max(detailedAnalysis.summary.brand_share_of_voice, 5)}%` }}
                    >
                      <span className="text-xs text-white font-medium">
                        {detailedAnalysis.summary.brand_share_of_voice.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              {/* Competitors */}
              {Object.entries(detailedAnalysis.competitor_summary)
                .sort((a, b) => b[1].share_of_voice - a[1].share_of_voice)
                .map(([name, data]) => (
                <div key={name} className="flex items-center gap-4">
                  <span className="text-sm w-32 truncate text-gray-600">{name}</span>
                  <div className="flex-1">
                    <div className="w-full bg-gray-200 rounded-full h-4">
                      <div
                        className="bg-gray-400 h-4 rounded-full transition-all flex items-center justify-end pr-2"
                        style={{ width: `${Math.max(data.share_of_voice, 5)}%` }}
                      >
                        <span className="text-xs text-white font-medium">
                          {data.share_of_voice.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Per-Question Analysis */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Per-Question Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          {detailedAnalysis?.by_question && detailedAnalysis.by_question.length > 0 ? (
            <div className="space-y-2">
              {/* Header */}
              <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-gray-50 rounded-t-lg text-sm font-medium text-gray-500">
                <div className="col-span-5">Question</div>
                <div className="col-span-2 text-center">ChatGPT</div>
                <div className="col-span-2 text-center">Perplexity</div>
                <div className="col-span-2 text-center">Sentiment</div>
                <div className="col-span-1"></div>
              </div>

              {/* Rows */}
              {detailedAnalysis.by_question.map((q) => (
                <div key={q.question_id} className="border rounded-lg">
                  <div
                    className="grid grid-cols-12 gap-2 px-4 py-3 items-center cursor-pointer hover:bg-gray-50"
                    onClick={() => toggleQuestion(q.question_id)}
                  >
                    <div className="col-span-5 text-sm truncate" title={q.question_text}>
                      {q.question_text}
                    </div>
                    <div className="col-span-2 text-center">
                      {q.platforms.chatgpt ? (
                        <span className={cn(
                          "inline-flex items-center px-2 py-1 rounded text-xs font-medium",
                          q.platforms.chatgpt.brand_mentioned
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-600"
                        )}>
                          {q.platforms.chatgpt.brand_mentioned ? (
                            <>
                              <CheckCircle className="w-3 h-3 mr-1" />
                              {q.platforms.chatgpt.position ? `#${q.platforms.chatgpt.position}` : "Yes"}
                            </>
                          ) : "No"}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">-</span>
                      )}
                    </div>
                    <div className="col-span-2 text-center">
                      {q.platforms.perplexity ? (
                        <span className={cn(
                          "inline-flex items-center px-2 py-1 rounded text-xs font-medium",
                          q.platforms.perplexity.brand_mentioned
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-600"
                        )}>
                          {q.platforms.perplexity.brand_mentioned ? (
                            <>
                              <CheckCircle className="w-3 h-3 mr-1" />
                              {q.platforms.perplexity.position ? `#${q.platforms.perplexity.position}` : "Yes"}
                            </>
                          ) : "No"}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">-</span>
                      )}
                    </div>
                    <div className="col-span-2 text-center">
                      {(() => {
                        const sentiment = q.platforms.chatgpt?.sentiment || q.platforms.perplexity?.sentiment;
                        return sentiment ? (
                          <span className={cn(
                            "px-2 py-1 rounded text-xs font-medium capitalize",
                            getSentimentBadgeColor(sentiment)
                          )}>
                            {sentiment}
                          </span>
                        ) : (
                          <span className="text-gray-400 text-xs">-</span>
                        );
                      })()}
                    </div>
                    <div className="col-span-1 text-center">
                      {expandedQuestions.has(q.question_id) ? (
                        <ChevronUp className="w-4 h-4 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-gray-400" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {expandedQuestions.has(q.question_id) && (
                    <div className="px-4 py-3 bg-gray-50 border-t">
                      <div className="grid grid-cols-2 gap-4">
                        {Object.entries(q.platforms).map(([platform, data]) => (
                          <div key={platform} className="bg-white p-3 rounded border">
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="font-medium capitalize">{platform}</h4>
                              <span className={cn(
                                "px-2 py-0.5 rounded text-xs",
                                data.brand_mentioned ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-600"
                              )}>
                                {data.brand_mentioned ? `${data.mention_count} mentions` : "Not mentioned"}
                              </span>
                            </div>
                            <div className="space-y-1 text-sm text-gray-600">
                              {data.position && (
                                <p>Position: #{data.position} {data.total_in_list && `of ${data.total_in_list}`}</p>
                              )}
                              <p>Sentiment: <span className="capitalize">{data.sentiment}</span> ({data.sentiment_score?.toFixed(2)})</p>
                              {data.citations && data.citations.length > 0 && (
                                <p>Citations: {data.citations.length}</p>
                              )}
                              {data.competitor_mentions && Object.keys(data.competitor_mentions).length > 0 && (
                                <div>
                                  <p className="font-medium mt-2">Competitors mentioned:</p>
                                  <ul className="list-disc list-inside">
                                    {Object.entries(data.competitor_mentions).map(([comp, compData]: [string, any]) => (
                                      <li key={comp}>{comp}: {compData.count} mentions</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              No analysis data available. Run an analysis to see results.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Competitor Comparison (from old API) */}
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
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Brand</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-500">Visibility</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-500">Sentiment</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-500">Mentions</th>
                    <th className="text-center py-3 px-4 font-medium text-gray-500">Share of Voice</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b bg-primary-50">
                    <td className="py-3 px-4 font-medium">{competitorData.brand.name}</td>
                    <td className="py-3 px-4 text-center">{competitorData.brand.visibility_score.toFixed(1)}</td>
                    <td className="py-3 px-4 text-center">{competitorData.brand.sentiment_score.toFixed(2)}</td>
                    <td className="py-3 px-4 text-center">{competitorData.brand.mention_count}</td>
                    <td className="py-3 px-4 text-center">{competitorData.brand.share_of_voice.toFixed(1)}%</td>
                  </tr>
                  {competitorData.competitors.map((comp: any) => (
                    <tr key={comp.name} className="border-b">
                      <td className="py-3 px-4">{comp.name}</td>
                      <td className="py-3 px-4 text-center">{comp.visibility_score.toFixed(1)}</td>
                      <td className="py-3 px-4 text-center">{comp.sentiment_score.toFixed(2)}</td>
                      <td className="py-3 px-4 text-center">{comp.mention_count}</td>
                      <td className="py-3 px-4 text-center">{comp.share_of_voice.toFixed(1)}%</td>
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
