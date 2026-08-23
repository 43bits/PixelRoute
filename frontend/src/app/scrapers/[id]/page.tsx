'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Play,
  Trash2,
  Activity,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  RefreshCw,
  Globe,
  Layers,
  Eye,
} from 'lucide-react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import api from '@/lib/api';
import { Scraper, ScraperJob } from '@/types';

export default function ScraperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: scraper, isLoading, error } = useQuery<Scraper>({
    queryKey: ['scraper', id],
    queryFn: () => api.getScraper(id),
    refetchInterval: 5000,
  });

  const { data: jobsData } = useQuery({
    queryKey: ['jobs', id],
    queryFn: () => api.listScraperJobs(id, { limit: 10 }),
    refetchInterval: 5000,
  });

  const runMutation = useMutation({
    mutationFn: () => api.runScraper(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scraper', id] });
      queryClient.invalidateQueries({ queryKey: ['jobs', id] });
    },
  });

  const healMutation = useMutation({
    mutationFn: () => api.triggerSelfHeal(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scraper', id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteScraper(id),
    onSuccess: () => router.push('/scrapers'),
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (error || !scraper) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <XCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <p className="text-gray-600">Scraper not found</p>
          <Link href="/scrapers" className="text-primary-600 hover:underline mt-2 inline-block">
            Back to scrapers
          </Link>
        </div>
      </div>
    );
  }

  const jobs: ScraperJob[] = jobsData?.jobs ?? [];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="border-b bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-4">
              <Link href="/scrapers" className="text-gray-500 hover:text-gray-700 transition">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <div className="flex items-center space-x-3">
                  <h1 className="text-2xl font-bold text-gray-900">{scraper.name}</h1>
                  <StatusBadge status={scraper.status} />
                  {scraper.autoHeal && (
                    <span className="text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
                      Auto-Heal
                    </span>
                  )}
                </div>
                {scraper.description && (
                  <p className="text-gray-500 mt-1 text-sm">{scraper.description}</p>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => healMutation.mutate()}
                disabled={healMutation.isPending}
                title="Trigger self-heal"
                className="p-2 text-gray-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition disabled:opacity-50"
              >
                <RefreshCw className={`w-5 h-5 ${healMutation.isPending ? 'animate-spin' : ''}`} />
              </button>
              <button
                onClick={() => runMutation.mutate()}
                disabled={runMutation.isPending}
                className="flex items-center space-x-2 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition disabled:opacity-60"
              >
                {runMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                <span>Run</span>
              </button>
              <button
                onClick={() => {
                  if (confirm(`Delete "${scraper.name}"? This cannot be undone.`)) {
                    deleteMutation.mutate();
                  }
                }}
                className="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard label="Target URLs" value={scraper.targetUrls.length} icon={<Globe className="w-5 h-5" />} />
          <StatCard label="Fields" value={scraper.fields?.length ?? 0} icon={<Layers className="w-5 h-5" />} />
          <StatCard label="Jobs run" value={jobs.length} icon={<Activity className="w-5 h-5" />} />
          <StatCard label="Self-heals" value={scraper.healCount} icon={<RefreshCw className="w-5 h-5" />} />
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* Target URLs */}
          <section className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Target URLs</h2>
            <ul className="space-y-2">
              {scraper.targetUrls.map((url, i) => (
                <li key={i} className="flex items-center space-x-2 text-sm">
                  <Globe className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:underline truncate"
                  >
                    {url}
                  </a>
                </li>
              ))}
            </ul>
          </section>

          {/* Fields */}
          <section className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="font-semibold text-gray-900 mb-3">Data Fields</h2>
            {scraper.fields && scraper.fields.length > 0 ? (
              <ul className="space-y-3">
                {scraper.fields.map((field) => (
                  <li key={field.id} className="text-sm">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-gray-800">{field.name}</span>
                      <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                        {field.fieldType}
                      </span>
                      {field.isRequired && (
                        <span className="text-xs text-red-500">required</span>
                      )}
                    </div>
                    <p className="text-gray-500 mt-0.5">{field.description}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-400">No fields defined</p>
            )}
          </section>
        </div>

        {/* Recent Jobs */}
        <section className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="font-semibold text-gray-900 mb-4">Recent Jobs</h2>
          {jobs.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Activity className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No jobs yet — click Run to start scraping</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Items</th>
                    <th className="pb-2 font-medium">Progress</th>
                    <th className="pb-2 font-medium">Duration</th>
                    <th className="pb-2 font-medium">Started</th>
                    <th className="pb-2 font-medium">Results</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {jobs.map((job) => (
                    <tr key={job.id}>
                      <td className="py-3">
                        <JobStatusBadge status={job.status} />
                      </td>
                      <td className="py-3 text-gray-700">{job.itemsScraped}</td>
                      <td className="py-3">
                        <div className="flex items-center space-x-2">
                          <div className="w-24 bg-gray-100 rounded-full h-1.5">
                            <div
                              className="bg-primary-500 h-1.5 rounded-full"
                              style={{ width: `${job.progress}%` }}
                            />
                          </div>
                          <span className="text-gray-500">{job.progress}%</span>
                        </div>
                      </td>
                      <td className="py-3 text-gray-500">
                        {job.duration ? `${job.duration}s` : '—'}
                      </td>
                      <td className="py-3 text-gray-500">
                        {job.startedAt
                          ? formatDistanceToNow(new Date(job.startedAt), { addSuffix: true })
                          : '—'}
                      </td>
                      <td className="py-3">
                        {job.status === 'COMPLETED' && job.itemsScraped > 0 ? (
                          <Link
                            href={`/scrapers/${scraper.id}/results`}
                            className="flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-700 font-medium"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>View</span>
                          </Link>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Metadata */}
        <p className="text-xs text-gray-400 text-center pb-4">
          Created {formatDistanceToNow(new Date(scraper.createdAt), { addSuffix: true })}
          {scraper.lastHealed &&
            ` · Last healed ${formatDistanceToNow(new Date(scraper.lastHealed), { addSuffix: true })}`}
        </p>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center space-x-2 text-gray-400 mb-1">
        {icon}
        <span className="text-xs font-medium uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ACTIVE: 'bg-green-100 text-green-800',
    DRAFT: 'bg-gray-100 text-gray-800',
    PAUSED: 'bg-yellow-100 text-yellow-800',
    ERROR: 'bg-red-100 text-red-800',
    ARCHIVED: 'bg-gray-100 text-gray-600',
  };
  return (
    <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${colors[status] ?? colors.DRAFT}`}>
      {status}
    </span>
  );
}

function JobStatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; icon: React.ReactNode }> = {
    COMPLETED: { color: 'text-green-600', icon: <CheckCircle2 className="w-4 h-4" /> },
    RUNNING:   { color: 'text-blue-600',  icon: <Loader2 className="w-4 h-4 animate-spin" /> },
    FAILED:    { color: 'text-red-600',   icon: <XCircle className="w-4 h-4" /> },
    PENDING:   { color: 'text-gray-500',  icon: <Clock className="w-4 h-4" /> },
    CANCELLED: { color: 'text-gray-400',  icon: <XCircle className="w-4 h-4" /> },
  };
  const { color, icon } = map[status] ?? map.PENDING;
  return (
    <span className={`flex items-center space-x-1 ${color}`}>
      {icon}
      <span className="text-xs font-medium">{status}</span>
    </span>
  );
}
