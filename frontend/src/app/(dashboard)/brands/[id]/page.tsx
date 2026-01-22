"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Play,
  Globe,
  Tag,
  Building2,
  Users,
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2
} from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { brandApi, analysisApi } from "@/lib/api";

export default function BrandDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const brandId = params.id as string;

  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [analysisSuccess, setAnalysisSuccess] = useState(false);

  const { data: brand, isLoading, error } = useQuery({
    queryKey: ["brand", brandId],
    queryFn: () => brandApi.get(brandId),
  });

  const { data: analysisOverview } = useQuery({
    queryKey: ["analysis-overview", brandId],
    queryFn: () => analysisApi.getOverview(brandId),
    enabled: !!brandId,
  });

  const runAnalysisMutation = useMutation({
    mutationFn: () => analysisApi.triggerAnalysis(brandId, ["chatgpt", "perplexity"]),
    onSuccess: () => {
      setAnalysisSuccess(true);
      setRunningAnalysis(false);
      queryClient.invalidateQueries({ queryKey: ["analysis-overview", brandId] });
      // Redirect to analysis page after short delay
      setTimeout(() => {
        router.push("/analysis");
      }, 2000);
    },
    onError: (err: any) => {
      setAnalysisError(err.response?.data?.detail || "Failed to run analysis");
      setRunningAnalysis(false);
    },
  });

  const handleRunAnalysis = () => {
    setRunningAnalysis(true);
    setAnalysisError(null);
    setAnalysisSuccess(false);
    runAnalysisMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error || !brand) {
    return (
      <div className="p-8">
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Brand not found</h2>
          <p className="text-gray-500 mb-4">The brand you're looking for doesn't exist or has been deleted.</p>
          <Link href="/brands">
            <Button>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Brands
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link href="/brands">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{brand.name}</h1>
          {brand.domain && (
            <p className="text-gray-500 flex items-center gap-1">
              <Globe className="w-4 h-4" />
              {brand.domain}
            </p>
          )}
        </div>
        <Button
          onClick={handleRunAnalysis}
          disabled={runningAnalysis}
          className="gap-2"
        >
          {runningAnalysis ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Running Analysis...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Analysis
            </>
          )}
        </Button>
      </div>

      {/* Status Messages */}
      {analysisError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-700">{analysisError}</span>
        </div>
      )}

      {analysisSuccess && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-green-500" />
          <span className="text-green-700">Analysis started successfully! Redirecting to analysis page...</span>
        </div>
      )}

      {/* Brand Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Industry */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              Industry
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold text-gray-900">
              {brand.industry || "Not specified"}
            </p>
          </CardContent>
        </Card>

        {/* Keywords */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
              <Tag className="w-4 h-4" />
              Keywords
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {brand.keywords?.length > 0 ? (
                brand.keywords.map((keyword: string, i: number) => (
                  <span
                    key={i}
                    className="px-2 py-1 text-sm bg-primary-50 text-primary-700 rounded"
                  >
                    {keyword}
                  </span>
                ))
              ) : (
                <span className="text-gray-400">No keywords</span>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Competitors */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-2">
              <Users className="w-4 h-4" />
              Competitors
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {brand.competitors?.length > 0 ? (
                brand.competitors.map((competitor: string, i: number) => (
                  <span
                    key={i}
                    className="px-2 py-1 text-sm bg-gray-100 text-gray-700 rounded"
                  >
                    {competitor}
                  </span>
                ))
              ) : (
                <span className="text-gray-400">No competitors</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Analysis Overview */}
      {analysisOverview && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Latest Analysis Overview
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-primary-600">
                  {analysisOverview.visibility_score?.toFixed(0) || 0}%
                </p>
                <p className="text-sm text-gray-500">Visibility Score</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-green-600">
                  {analysisOverview.total_mentions || 0}
                </p>
                <p className="text-sm text-gray-500">Total Mentions</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className={`text-2xl font-bold ${
                  analysisOverview.avg_sentiment_score > 0 ? 'text-green-600' :
                  analysisOverview.avg_sentiment_score < 0 ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {analysisOverview.avg_sentiment_score?.toFixed(2) || '0.00'}
                </p>
                <p className="text-sm text-gray-500">Avg Sentiment</p>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-blue-600">
                  {analysisOverview.total_citations || 0}
                </p>
                <p className="text-sm text-gray-500">Citations</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Products */}
      {brand.products?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Products</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {brand.products.map((product: string, i: number) => (
                <span
                  key={i}
                  className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium"
                >
                  {product}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Timestamps */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              Created: {new Date(brand.created_at).toLocaleDateString()}
            </span>
            <span>
              Last updated: {new Date(brand.updated_at).toLocaleDateString()}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
