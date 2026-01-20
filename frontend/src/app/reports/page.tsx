"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, FileText, FileJson, FileSpreadsheet } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { brandApi, reportApi } from "@/lib/api";

export default function ReportsPage() {
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [timeRange, setTimeRange] = useState<number>(30);

  const { data: brandsData } = useQuery({
    queryKey: ["brands"],
    queryFn: () => brandApi.list(1, 100),
  });

  const brands = brandsData?.items || [];
  const activeBrandId = selectedBrandId || brands[0]?.id;

  const { data: summary, isLoading } = useQuery({
    queryKey: ["report-summary", activeBrandId, timeRange],
    queryFn: () => reportApi.getSummary(activeBrandId, timeRange),
    enabled: !!activeBrandId,
  });

  const handleExportCsv = async () => {
    try {
      const blob = await reportApi.exportCsv(activeBrandId, timeRange);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${activeBrandId}_${timeRange}days.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Export failed:", error);
    }
  };

  const handleExportJson = async () => {
    try {
      const data = await reportApi.exportJson(activeBrandId, timeRange);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${activeBrandId}_${timeRange}days.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Export failed:", error);
    }
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="text-gray-500">Generate and export analytics reports</p>
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

      {/* Export Options */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={handleExportCsv}>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="p-3 bg-green-100 rounded-lg">
              <FileSpreadsheet className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Export CSV</h3>
              <p className="text-sm text-gray-500">Spreadsheet format</p>
            </div>
          </CardContent>
        </Card>

        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={handleExportJson}>
          <CardContent className="flex items-center gap-4 p-6">
            <div className="p-3 bg-blue-100 rounded-lg">
              <FileJson className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Export JSON</h3>
              <p className="text-sm text-gray-500">Structured data format</p>
            </div>
          </CardContent>
        </Card>

        <Card className="opacity-50">
          <CardContent className="flex items-center gap-4 p-6">
            <div className="p-3 bg-purple-100 rounded-lg">
              <FileText className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">Export PDF</h3>
              <p className="text-sm text-gray-500">Coming soon</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Report Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Report Summary</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : summary ? (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Avg Visibility</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {summary.summary.avg_visibility_score}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Avg Sentiment</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {summary.summary.avg_sentiment}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Total Mentions</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {summary.summary.total_mentions}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Share of Voice</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {summary.summary.avg_share_of_voice}%
                  </p>
                </div>
              </div>

              {/* Highlights */}
              {summary.highlights?.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Highlights</h4>
                  <ul className="list-disc list-inside space-y-1">
                    {summary.highlights.map((highlight: string, i: number) => (
                      <li key={i} className="text-gray-600">
                        {highlight}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Recommendations */}
              {summary.recommendations?.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">
                    Recommendations
                  </h4>
                  <ul className="list-disc list-inside space-y-1">
                    {summary.recommendations.map((rec: string, i: number) => (
                      <li key={i} className="text-gray-600">
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              No report data available
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
