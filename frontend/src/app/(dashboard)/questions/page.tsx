"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Play, RefreshCw } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { brandApi, questionApi } from "@/lib/api";

export default function QuestionsPage() {
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const queryClient = useQueryClient();

  const { data: brandsData } = useQuery({
    queryKey: ["brands"],
    queryFn: () => brandApi.list(1, 100),
  });

  const brands = brandsData?.items || [];
  const activeBrandId = selectedBrandId || brands[0]?.id;

  const { data: questionsData, isLoading } = useQuery({
    queryKey: ["questions", activeBrandId],
    queryFn: () => questionApi.list(activeBrandId, 1, 50),
    enabled: !!activeBrandId,
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      questionApi.generate(activeBrandId, {
        categories: null,
        include_competitors: true,
        max_questions_per_category: 5,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["questions", activeBrandId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: questionApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["questions", activeBrandId] });
    },
  });

  const questions = questionsData?.items || [];

  const categorizedQuestions = questions.reduce((acc: any, q: any) => {
    const category = q.category || "uncategorized";
    if (!acc[category]) acc[category] = [];
    acc[category].push(q);
    return acc;
  }, {});

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Questions</h1>
          <p className="text-gray-500">
            Manage research questions for your brands
          </p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={activeBrandId || ""}
            onChange={(e) => setSelectedBrandId(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">Select a brand</option>
            {brands.map((brand: any) => (
              <option key={brand.id} value={brand.id}>
                {brand.name}
              </option>
            ))}
          </select>
          <Button
            onClick={() => generateMutation.mutate()}
            disabled={!activeBrandId || generateMutation.isPending}
          >
            <RefreshCw
              className={`w-4 h-4 mr-2 ${generateMutation.isPending ? "animate-spin" : ""}`}
            />
            Generate Questions
          </Button>
        </div>
      </div>

      {!activeBrandId ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-gray-500">Select a brand to view questions</p>
          </CardContent>
        </Card>
      ) : isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : questions.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No questions yet
            </h3>
            <p className="text-gray-500 mb-4">
              Generate questions automatically based on your brand profile
            </p>
            <Button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
            >
              Generate Questions
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {Object.entries(categorizedQuestions).map(
            ([category, categoryQuestions]: [string, any]) => (
              <Card key={category}>
                <CardHeader>
                  <CardTitle className="capitalize">
                    {category.replace(/_/g, " ")}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {categoryQuestions.map((question: any) => (
                      <div
                        key={question.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                      >
                        <span className="text-sm text-gray-700">
                          {question.question_text}
                        </span>
                        <div className="flex items-center gap-2">
                          <Button variant="ghost" size="sm">
                            <Play className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              if (confirm("Delete this question?")) {
                                deleteMutation.mutate(question.id);
                              }
                            }}
                          >
                            <Trash2 className="w-4 h-4 text-red-500" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )
          )}
        </div>
      )}
    </div>
  );
}
