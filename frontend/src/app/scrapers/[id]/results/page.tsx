'use client';

import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft, Star, ExternalLink, Package,
  RefreshCw, AlertCircle, Loader2, Download, Database,
} from 'lucide-react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import api from '@/lib/api';
import { Scraper, ScraperResult } from '@/types';

// ── tiny helpers ───────────────────────────────────────────────────────────────

function str(obj: Record<string, unknown>, ...keys: string[]): string {
  for (const k of keys) {
    const v = obj[k];
    if (v !== null && v !== undefined && v !== '') return String(v);
  }
  return '';
}

function num(obj: Record<string, unknown>, ...keys: string[]): number | null {
  for (const k of keys) {
    const v = obj[k];
    if (v !== null && v !== undefined && !isNaN(Number(v))) return Number(v);
  }
  return null;
}

const KNOWN = new Set([
  'title','name','product_name','heading',
  'image','image_url','thumbnail','img','picture',
  'price','Price','current_price','sale_price','cost',
  'rating','Rating','stars','score',
  'reviewsCount','reviews_count','review_count','num_reviews','reviews',
  'ASIN','asin','sku','id','product_id',
  'brand','Brand','manufacturer','seller','vendor',
  'productSpecs','specs','attributes','features',
  'input','url','source',
]);

// ── StarRating ────────────────────────────────────────────────────────────────

function StarRating({ rating }: { rating: number }) {
  const full  = Math.floor(rating);
  const half  = rating % 1 >= 0.5;
  const empty = 5 - full - (half ? 1 : 0);
  return (
    <span className="flex items-center space-x-0.5">
      {Array.from({ length: full  }).map((_, i) => <Star key={`f${i}`} className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />)}
      {half && <Star className="w-3.5 h-3.5 fill-amber-200 text-amber-400" />}
      {Array.from({ length: empty }).map((_, i) => <Star key={`e${i}`} className="w-3.5 h-3.5 text-gray-300" />)}
      <span className="text-sm font-semibold text-gray-700 ml-1">{rating}</span>
    </span>
  );
}

// ── ProductCard ───────────────────────────────────────────────────────────────

function ProductCard({ result }: { result: ScraperResult }) {
  const d       = result.data;
  const title   = str(d, 'title','name','product_name','heading');
  const image   = str(d, 'image','image_url','thumbnail','img','picture');
  const price   = str(d, 'price','Price','current_price','sale_price','cost');
  const rating  = num(d, 'rating','Rating','stars','score');
  const reviews = num(d, 'reviewsCount','reviews_count','review_count','num_reviews');
  const asin    = str(d, 'ASIN','asin','sku','product_id');
  const brand   = str(d, 'brand','Brand','manufacturer','seller','vendor');

  type Spec = { title: string; value?: string };
  const specs: Spec[] = Array.isArray(d.productSpecs)
    ? (d.productSpecs as Spec[]).filter(s => s.title && s.value)
    : [];

  const extras = Object.entries(d).filter(([k, v]) =>
    !KNOWN.has(k) && v !== null && v !== undefined && v !== '' && typeof v !== 'object'
  );

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 flex flex-col">

      {/* Image */}
      <div className="bg-gradient-to-br from-gray-50 to-gray-100 h-52 flex items-center justify-center flex-shrink-0 relative">
        {image ? (
          <img
            src={image}
            alt={title || 'Product image'}
            className="h-full w-full object-contain p-4"
            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        ) : (
          <Package className="w-16 h-16 text-gray-300" />
        )}
        {asin && (
          <span className="absolute top-2 right-2 text-xs bg-white/80 backdrop-blur text-gray-500 font-mono px-2 py-0.5 rounded-full border border-gray-200">
            {asin}
          </span>
        )}
      </div>

      <div className="p-4 flex flex-col flex-1 space-y-2.5">

        {/* Title + brand */}
        <div>
          <h3 className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2 min-h-[2.5rem]">
            {title || <span className="text-gray-400 italic">No title</span>}
          </h3>
          {brand && <p className="text-xs text-gray-400 mt-0.5">{brand}</p>}
        </div>

        {/* Price */}
        {price && (
          <p className="text-xl font-bold text-emerald-600">{price}</p>
        )}

        {/* Rating + reviews */}
        {rating !== null && (
          <div className="flex items-center flex-wrap gap-2">
            <StarRating rating={rating} />
            {reviews !== null && (
              <span className="text-xs text-gray-400">
                {reviews.toLocaleString()} reviews
              </span>
            )}
          </div>
        )}

        {/* Specs */}
        {specs.length > 0 && (
          <div className="border-t border-gray-100 pt-2">
            <dl className="space-y-1">
              {specs.slice(0, 4).map((s, i) => (
                <div key={i} className="flex justify-between text-xs">
                  <dt className="text-gray-400">{s.title}</dt>
                  <dd className="text-gray-700 font-medium text-right ml-2 truncate max-w-[56%]">{s.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        )}

        {/* Extra fields */}
        {extras.length > 0 && (
          <div className="border-t border-gray-100 pt-2 space-y-1">
            {extras.slice(0, 4).map(([k, v]) => (
              <div key={k} className="flex justify-between text-xs">
                <span className="text-gray-400 capitalize">{k.replace(/_/g,' ')}</span>
                <span className="text-gray-700 font-medium text-right ml-2 truncate max-w-[56%]">{String(v)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="mt-auto pt-2 flex items-center justify-between border-t border-gray-50">
          <span className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(result.scrapedAt), { addSuffix: true })}
          </span>
          <a
            href={result.url || str(d, 'url','source')}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center space-x-1 text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            <span>Source</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}

// ── RawCard (fallback for non-product data) ────────────────────────────────────

function RawCard({ result }: { result: ScraperResult }) {
  const title = str(result.data, 'title','name','heading') || result.url;
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-gray-700 truncate">{title}</span>
        <div className="flex items-center space-x-2 flex-shrink-0 ml-2">
          <span className="text-xs text-gray-400">
            {formatDistanceToNow(new Date(result.scrapedAt), { addSuffix: true })}
          </span>
          {result.url && (
            <a href={result.url} target="_blank" rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-600">
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
        {Object.entries(result.data)
          .filter(([, v]) => v !== null && v !== undefined && typeof v !== 'object')
          .map(([k, v]) => (
            <div key={k} className="flex flex-col">
              <span className="text-xs text-gray-400 capitalize">{k.replace(/_/g,' ')}</span>
              <span className="text-sm text-gray-800 font-medium truncate">{String(v)}</span>
            </div>
          ))}
      </div>
      {/* JSON sub-objects */}
      {Object.entries(result.data)
        .filter(([, v]) => v !== null && typeof v === 'object' && !Array.isArray(v))
        .slice(0,1)
        .map(([k, v]) => (
          <details key={k} className="mt-3">
            <summary className="text-xs text-gray-400 cursor-pointer capitalize">{k}</summary>
            <pre className="mt-1 text-xs bg-gray-50 rounded p-2 overflow-auto max-h-32 whitespace-pre-wrap">
              {JSON.stringify(v, null, 2)}
            </pre>
          </details>
        ))}
    </div>
  );
}

// ── CSV export ────────────────────────────────────────────────────────────────

function exportCSV(results: ScraperResult[], name: string) {
  const flatKeys = Array.from(new Set(
    results.flatMap(r =>
      Object.entries(r.data)
        .filter(([, v]) => typeof v !== 'object' || v === null)
        .map(([k]) => k)
    )
  ));
  const header = ['scraped_at','source_url', ...flatKeys].join(',');
  const rows = results.map(r => [
    `"${r.scrapedAt}"`,
    `"${r.url}"`,
    ...flatKeys.map(k => {
      const v = r.data[k];
      if (v === null || v === undefined) return '';
      return `"${String(v).replace(/"/g, '""')}"`;
    }),
  ].join(','));
  const csv = [header, ...rows].join('\n');
  const a   = document.createElement('a');
  a.href    = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
  a.download = `${name.replace(/\s+/g,'_')}_results.csv`;
  a.click();
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ResultsPage() {
  const { id } = useParams<{ id: string }>();

  const { data: scraper } = useQuery<Scraper>({
    queryKey: ['scraper', id],
    queryFn: () => api.getScraper(id),
  });

  const { data, isLoading, refetch, isFetching } = useQuery<{
    results: ScraperResult[];
    total: number;
  }>({
    queryKey: ['scraper-results', id],
    queryFn: async () => {
      const jobsResp = await api.listScraperJobs(id, { limit: 50 });
      const completed = jobsResp.jobs.filter(j => j.status === 'COMPLETED');
      const all: ScraperResult[] = [];
      for (const job of completed) {
        try {
          const r = await api.getJobResults(job.id, { limit: 200 });
          all.push(...(r.results as unknown as ScraperResult[]));
        } catch { /* skip failed fetches */ }
      }
      // deduplicate by id
      const seen = new Set<string>();
      const unique = all.filter(r => { if (seen.has(r.id)) return false; seen.add(r.id); return true; });
      return { results: unique, total: unique.length };
    },
    refetchInterval: 15000,
  });

  const results  = data?.results ?? [];

  // Detect if data looks like product cards
  const isProduct = results.some(r =>
    r.data && (r.data.title || r.data.ASIN || r.data.image || r.data.rating)
  );

  return (
    <div className="min-h-screen bg-gray-50">

      {/* Sticky header */}
      <div className="border-b bg-white sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <Link href={`/scrapers/${id}`} className="text-gray-400 hover:text-gray-700 transition">
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-xl font-bold text-gray-900 flex items-center space-x-2">
                  <Database className="w-5 h-5 text-blue-500" />
                  <span>{scraper?.name ?? 'Scraper'} — Results</span>
                </h1>
                <p className="text-sm text-gray-500">
                  {results.length} record{results.length !== 1 ? 's' : ''} scraped
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => refetch()}
                disabled={isFetching}
                className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition"
                title="Refresh"
              >
                <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
              </button>
              {results.length > 0 && (
                <button
                  onClick={() => exportCSV(results, scraper?.name ?? 'results')}
                  className="flex items-center space-x-1.5 px-3 py-2 text-sm bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition"
                >
                  <Download className="w-4 h-4" />
                  <span>Export CSV</span>
                </button>
              )}
              <Link
                href={`/scrapers/${id}`}
                className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Run again
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Loading state */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-32 space-y-3">
            <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
            <p className="text-gray-500">Loading results...</p>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && results.length === 0 && (
          <div className="flex flex-col items-center justify-center py-32 text-center space-y-4">
            <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center">
              <AlertCircle className="w-10 h-10 text-gray-300" />
            </div>
            <div>
              <p className="text-lg font-semibold text-gray-700">No results yet</p>
              <p className="text-gray-400 text-sm mt-1">
                Run the scraper and wait for a job to complete
              </p>
            </div>
            <Link
              href={`/scrapers/${id}`}
              className="px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition"
            >
              Go to scraper
            </Link>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <>
            {/* Summary bar */}
            <div className="flex items-center justify-between mb-6 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
              <div className="flex items-center space-x-2 text-sm text-blue-700">
                <Database className="w-4 h-4" />
                <span>
                  <strong>{results.length}</strong> record{results.length !== 1 ? 's' : ''} from{' '}
                  <strong>{scraper?.targetUrls?.length ?? 0}</strong> URL{(scraper?.targetUrls?.length ?? 0) !== 1 ? 's' : ''}
                </span>
              </div>
              <span className="text-xs text-blue-500">auto-refreshes every 15s</span>
            </div>

            {isProduct ? (
              /* Product card grid */
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {results.map(r => <ProductCard key={r.id} result={r} />)}
              </div>
            ) : (
              /* Generic key-value cards */
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {results.map(r => <RawCard key={r.id} result={r} />)}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
