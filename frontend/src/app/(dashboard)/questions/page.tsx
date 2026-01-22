"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Play, RefreshCw, Sparkles, Zap, Globe } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { brandApi, questionApi } from "@/lib/api";

export default function QuestionsPage() {
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [generationMode, setGenerationMode] = useState<"smart" | "template">("smart");
  const [numQuestions, setNumQuestions] = useState(20);
  const [additionalUrls, setAdditionalUrls] = useState<string>("");
  const queryClient = useQueryClient();

  const { data: brandsData } = useQuery({
    queryKey: ["brands"],
    queryFn: () => brandApi.list(1, 100),
  });

  const brands = brandsData?.items || [];
  const activeBrandId = selectedBrandId || brands[0]?.id;
  const activeBrand = brands.find((b: any) => b.id === activeBrandId);

  const { data: questionsData, isLoading } = useQuery({
    queryKey: ["questions", activeBrandId],
    queryFn: () => questionApi.list(activeBrandId, 1, 50),
    enabled: !!activeBrandId,
  });

  // Template-based generation (basic)
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

  // Smart AI-powered generation
  const generateSmartMutation = useMutation({
    mutationFn: () => {
      // Parse additional URLs (comma or newline separated)
      const urlList = additionalUrls
        .split(/[,\n]/)
        .map(url => url.trim())
        .filter(url => url.length > 0);

      return questionApi.generateSmart(activeBrandId, {
        num_questions: numQuestions,
        research_website: true,
        additional_urls: urlList.length > 0 ? urlList : undefined,
      });
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["questions", activeBrandId] });
      setAdditionalUrls(""); // Clear after success
      // Show success message with research summary
      if (data.research_summary) {
        console.log("Research Summary:", data.research_summary);
      }
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

  const handleGenerate = () => {
    if (generationMode === "smart") {
      generateSmartMutation.mutate();
    } else {
      generateMutation.mutate();
    }
  };

  const isGenerating = generateMutation.isPending || generateSmartMutation.isPending;

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
        </div>
      </div>

      {/* Generation Options Card */}
      {activeBrandId && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-yellow-500" />
              Generate Questions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Generation Mode Toggle */}
              <div className="flex gap-4">
                <button
                  onClick={() => setGenerationMode("smart")}
                  className={`flex-1 p-4 rounded-lg border-2 transition-all ${
                    generationMode === "smart"
                      ? "border-primary-500 bg-primary-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <Sparkles className="w-5 h-5 text-yellow-500" />
                    <span className="font-medium">Smart Generation</span>
                    <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                      Recommended
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 text-left">
                    AI researches your brand website and generates realistic questions
                    that real users would ask in ChatGPT, Perplexity, etc.
                  </p>
                </button>

                <button
                  onClick={() => setGenerationMode("template")}
                  className={`flex-1 p-4 rounded-lg border-2 transition-all ${
                    generationMode === "template"
                      ? "border-primary-500 bg-primary-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <Zap className="w-5 h-5 text-blue-500" />
                    <span className="font-medium">Template Generation</span>
                  </div>
                  <p className="text-sm text-gray-500 text-left">
                    Quick generation using predefined templates.
                    Good for basic questions, less personalized.
                  </p>
                </button>
              </div>

              {/* Smart Generation Options */}
              {generationMode === "smart" && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="font-medium text-gray-900">Smart Generation Settings</h4>
                      <p className="text-sm text-gray-500">
                        {activeBrand?.domain ? (
                          <span className="flex items-center gap-1">
                            <Globe className="w-4 h-4" />
                            Will analyze: {activeBrand.domain}
                          </span>
                        ) : (
                          "Add a website domain to your brand for better results"
                        )}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-sm text-gray-600">Questions:</label>
                      <select
                        value={numQuestions}
                        onChange={(e) => setNumQuestions(Number(e.target.value))}
                        className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                      >
                        <option value={10}>10</option>
                        <option value={15}>15</option>
                        <option value={20}>20</option>
                        <option value={30}>30</option>
                        <option value={50}>50</option>
                      </select>
                    </div>
                  </div>

                  {/* Additional URLs input */}
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Additional URLs (optional)
                    </label>
                    <textarea
                      value={additionalUrls}
                      onChange={(e) => setAdditionalUrls(e.target.value)}
                      placeholder={`e.g., /blog, /docs, /case-studies\nor full URLs like https://example.com/pricing`}
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                      rows={2}
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      Add specific pages to crawl (comma or newline separated). Useful for small websites or specific content.
                    </p>
                  </div>

                  <div className="text-xs text-gray-500 space-y-1 mt-4">
                    <p>Questions will include (40% discovery, 15% comparison, etc.):</p>
                    <ul className="list-disc list-inside ml-2">
                      <li>Discovery questions (finding options in your category)</li>
                      <li>Comparison questions (your brand vs competitors)</li>
                      <li>Evaluation questions (is your brand right for them)</li>
                      <li>Feature-specific questions</li>
                      <li>Problem-solving questions</li>
                    </ul>
                  </div>
                </div>
              )}

              {/* Generate Button */}
              <Button
                onClick={handleGenerate}
                disabled={!activeBrandId || isGenerating}
                className="w-full"
                size="lg"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    {generationMode === "smart" ? "Researching & Generating..." : "Generating..."}
                  </>
                ) : (
                  <>
                    {generationMode === "smart" ? (
                      <Sparkles className="w-4 h-4 mr-2" />
                    ) : (
                      <Zap className="w-4 h-4 mr-2" />
                    )}
                    Generate {generationMode === "smart" ? "Smart" : "Template"} Questions
                  </>
                )}
              </Button>

              {generateSmartMutation.isError && (
                <p className="text-sm text-red-600">
                  Failed to generate questions. Please try again.
                </p>
              )}

              {generateSmartMutation.isSuccess && (
                <p className="text-sm text-green-600">
                  Successfully generated {generateSmartMutation.data?.questions_generated || 0} questions!
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

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
            <Sparkles className="w-12 h-12 text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No questions yet
            </h3>
            <p className="text-gray-500 mb-4 text-center max-w-md">
              Generate questions using the panel above. Smart generation will
              research your brand and create realistic user search queries.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Questions Summary */}
          <div className="flex items-center justify-between text-sm text-gray-500">
            <span>{questions.length} questions total</span>
            <span>{Object.keys(categorizedQuestions).length} categories</span>
          </div>

          {Object.entries(categorizedQuestions).map(
            ([category, categoryQuestions]: [string, any]) => (
              <Card key={category}>
                <CardHeader>
                  <CardTitle className="capitalize flex items-center justify-between">
                    <span>{category.replace(/_/g, " ")}</span>
                    <span className="text-sm font-normal text-gray-500">
                      {categoryQuestions.length} questions
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {categoryQuestions.map((question: any) => (
                      <div
                        key={question.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        <span className="text-sm text-gray-700">
                          {question.question_text}
                        </span>
                        <div className="flex items-center gap-2">
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
