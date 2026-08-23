'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Play, Trash2, Edit, Activity, Clock } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';
import api from '@/lib/api';
import { Scraper } from '@/types';

export default function ScrapersPage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<string>('');

  const { data, isLoading } = useQuery({
    queryKey: ['scrapers', filter],
    queryFn: () => api.listScrapers({ status: filter || undefined }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteScraper(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scrapers'] });
    },
  });

  const runMutation = useMutation({
    mutationFn: (id: string) => api.runScraper(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scrapers'] });
    },
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="border-b bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Scrapers</h1>
              <p className="mt-2 text-gray-600">
                Manage your self-healing web scrapers
              </p>
            </div>
            <Link
              href="/scrapers/new"
              className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 transition flex items-center space-x-2 shadow-lg shadow-primary-500/30"
            >
              <Plus className="w-5 h-5" />
              <span>Create Scraper</span>
            </Link>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="mb-6 flex items-center space-x-4">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            <option value="">All Status</option>
            <option value="ACTIVE">Active</option>
            <option value="DRAFT">Draft</option>
            <option value="PAUSED">Paused</option>
            <option value="ERROR">Error</option>
          </select>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 animate-pulse"
              >
                <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              </div>
            ))}
          </div>
        )}

        {/* Scrapers Grid */}
        {data && data.scrapers.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <Activity className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No scrapers yet
            </h3>
            <p className="text-gray-600 mb-6">
              Create your first scraper to get started
            </p>
            <Link
              href="/scrapers/new"
              className="inline-flex items-center space-x-2 bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 transition"
            >
              <Plus className="w-5 h-5" />
              <span>Create Scraper</span>
            </Link>
          </div>
        )}

        {data && data.scrapers.length > 0 && (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {data.scrapers.map((scraper: Scraper) => (
              <div
                key={scraper.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition"
              >
                <div className="p-6">
                  {/* Status Badge */}
                  <div className="flex items-center justify-between mb-4">
                    <StatusBadge status={scraper.status} />
                    {scraper.autoHeal && (
                      <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
                        Auto-Heal
                      </span>
                    )}
                  </div>

                  {/* Name & Description */}
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {scraper.name}
                  </h3>
                  {scraper.description && (
                    <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                      {scraper.description}
                    </p>
                  )}

                  {/* Stats */}
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center text-sm text-gray-600">
                      <Activity className="w-4 h-4 mr-2" />
                      <span>{scraper.targetUrls.length} URLs</span>
                    </div>
                    {scraper.lastHealed && (
                      <div className="flex items-center text-sm text-gray-600">
                        <Clock className="w-4 h-4 mr-2" />
                        <span>Healed {scraper.healCount}x</span>
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-2 pt-4 border-t border-gray-200">
                    <button
                      onClick={() => runMutation.mutate(scraper.id)}
                      disabled={runMutation.isPending}
                      className="flex-1 bg-primary-50 text-primary-600 px-4 py-2 rounded-lg hover:bg-primary-100 transition flex items-center justify-center space-x-2 disabled:opacity-50"
                    >
                      <Play className="w-4 h-4" />
                      <span>Run</span>
                    </button>
                    <Link
                      href={`/scrapers/${scraper.id}`}
                      className="flex-1 bg-gray-50 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-100 transition flex items-center justify-center space-x-2"
                    >
                      <Edit className="w-4 h-4" />
                      <span>View</span>
                    </Link>
                    <button
                      onClick={() => {
                        if (confirm('Delete this scraper?')) {
                          deleteMutation.mutate(scraper.id);
                        }
                      }}
                      className="bg-red-50 text-red-600 px-3 py-2 rounded-lg hover:bg-red-100 transition"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors = {
    ACTIVE: 'bg-green-100 text-green-800',
    DRAFT: 'bg-gray-100 text-gray-800',
    PAUSED: 'bg-yellow-100 text-yellow-800',
    ERROR: 'bg-red-100 text-red-800',
    ARCHIVED: 'bg-gray-100 text-gray-600',
  };

  return (
    <span
      className={`text-xs font-medium px-2.5 py-1 rounded-full ${
        colors[status as keyof typeof colors] || colors.DRAFT
      }`}
    >
      {status}
    </span>
  );
}
