'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Send, Bot, User, Image as ImageIcon, Clock } from 'lucide-react';
import api from '@/lib/api';
import { VisualQuery } from '@/types';

export default function QueryPage() {
  const [question, setQuestion] = useState('');
  const [selectedScraper, setSelectedScraper] = useState<string>('');
  const [queries, setQueries] = useState<VisualQuery[]>([]);

  // Load scrapers for filter
  const { data: scrapersData } = useQuery({
    queryKey: ['scrapers'],
    queryFn: () => api.listScrapers({ limit: 100 }),
  });

  // Query mutation
  const queryMutation = useMutation({
    mutationFn: (params: { question: string; scraperId?: string }) =>
      api.queryVisual(params),
    onSuccess: (data) => {
      setQueries((prev) => [data, ...prev]);
      setQuestion('');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    queryMutation.mutate({
      question: question.trim(),
      scraperId: selectedScraper || undefined,
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="border-b bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900">Visual Query</h1>
          <p className="mt-2 text-gray-600">
            Ask questions about your scraped visual content
          </p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filter */}
        {scrapersData && scrapersData.scrapers.length > 0 && (
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Scraper (optional)
            </label>
            <select
              value={selectedScraper}
              onChange={(e) => setSelectedScraper(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All Scrapers</option>
              {scrapersData.scrapers.map((scraper: any) => (
                <option key={scraper.id} value={scraper.id}>
                  {scraper.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Chat Interface */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          {/* Messages */}
          <div className="h-[500px] overflow-y-auto p-6 space-y-6">
            {queries.length === 0 ? (
              <div className="text-center py-12">
                <Bot className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500">
                  Start by asking a question about your visual data
                </p>
                <div className="mt-6 space-y-2 text-sm text-gray-400">
                  <p>Try asking:</p>
                  <ul className="space-y-1">
                    <li>"Show me all price comparison tables"</li>
                    <li>"What are the trends in the charts?"</li>
                    <li>"Find products with red badges"</li>
                  </ul>
                </div>
              </div>
            ) : (
              queries.map((query) => (
                <div key={query.id} className="space-y-4">
                  {/* User Question */}
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                        <User className="w-5 h-5 text-primary-600" />
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="bg-primary-50 rounded-lg p-4">
                        <p className="text-gray-900">{query.question}</p>
                      </div>
                    </div>
                  </div>

                  {/* Bot Response */}
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                        <Bot className="w-5 h-5 text-gray-600" />
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="bg-gray-50 rounded-lg p-4">
                        {query.answer && (
                          <p className="text-gray-900 mb-4">{query.answer}</p>
                        )}

                        {/* Results */}
                        {query.results.length > 0 && (
                          <div className="space-y-3">
                            <p className="text-sm font-medium text-gray-700">
                              Found {query.resultCount} results:
                            </p>
                            {query.results.map((result, idx) => (
                              <div
                                key={idx}
                                className="border border-gray-200 rounded-lg p-3 hover:border-primary-300 transition"
                              >
                                <div className="flex items-start justify-between mb-2">
                                  <div className="flex items-center space-x-2">
                                    <ImageIcon className="w-4 h-4 text-gray-400" />
                                    <span className="text-sm font-medium text-gray-900">
                                      Score: {(result.score * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                  {result.metadata && (
                                    <a
                                      href={result.metadata.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-xs text-primary-600 hover:underline"
                                    >
                                      View Source
                                    </a>
                                  )}
                                </div>
                                {result.snippet && (
                                  <p className="text-sm text-gray-600">
                                    {result.snippet}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Metadata */}
                        <div className="mt-3 flex items-center space-x-4 text-xs text-gray-500">
                          <div className="flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>{query.duration}ms</span>
                          </div>
                          <span>
                            {new Date(query.createdAt).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}

            {/* Loading State */}
            {queryMutation.isPending && (
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                    <Bot className="w-5 h-5 text-gray-600 animate-pulse" />
                  </div>
                </div>
                <div className="flex-1">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="animate-pulse space-y-2">
                      <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                      <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <form
            onSubmit={handleSubmit}
            className="border-t border-gray-200 p-4 bg-gray-50"
          >
            <div className="flex space-x-3">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask a question about your visual data..."
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                disabled={queryMutation.isPending}
              />
              <button
                type="submit"
                disabled={!question.trim() || queryMutation.isPending}
                className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                <Send className="w-5 h-5" />
                <span>Send</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
