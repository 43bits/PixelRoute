'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { Plus, Trash2, ArrowLeft, Loader2, AlertCircle } from 'lucide-react';
import Link from 'next/link';
import api from '@/lib/api';

interface FieldDraft {
  name: string;
  description: string;
  fieldType: 'TEXT' | 'NUMBER' | 'URL' | 'IMAGE' | 'DATE' | 'VISUAL';
  isRequired: boolean;
}

const FIELD_TYPES = ['TEXT', 'NUMBER', 'URL', 'IMAGE', 'DATE', 'VISUAL'] as const;

export default function NewScraperPage() {
  const router = useRouter();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [urlInput, setUrlInput] = useState('');
  const [targetUrls, setTargetUrls] = useState<string[]>([]);
  const [autoHeal, setAutoHeal] = useState(true);
  const [fields, setFields] = useState<FieldDraft[]>([
    { name: '', description: '', fieldType: 'TEXT', isRequired: false },
  ]);
  const [error, setError] = useState('');

  const createMutation = useMutation({
    mutationFn: api.createScraper.bind(api),
    onSuccess: (data) => {
      router.push(`/scrapers/${data.id}`);
    },
    onError: (err: any) => {
      setError(err?.response?.data?.detail || err?.message || 'Failed to create scraper');
    },
  });

  // URL helpers
  const addUrl = () => {
    const url = urlInput.trim();
    if (!url) return;
    try { new URL(url); } catch { setError('Invalid URL — include http:// or https://'); return; }
    if (targetUrls.includes(url)) return;
    setTargetUrls((prev) => [...prev, url]);
    setUrlInput('');
    setError('');
  };

  const removeUrl = (idx: number) =>
    setTargetUrls((prev) => prev.filter((_, i) => i !== idx));

  // Field helpers
  const addField = () =>
    setFields((prev) => [
      ...prev,
      { name: '', description: '', fieldType: 'TEXT', isRequired: false },
    ]);

  const updateField = (idx: number, patch: Partial<FieldDraft>) =>
    setFields((prev) => prev.map((f, i) => (i === idx ? { ...f, ...patch } : f)));

  const removeField = (idx: number) =>
    setFields((prev) => prev.filter((_, i) => i !== idx));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim()) { setError('Scraper name is required'); return; }
    if (targetUrls.length === 0) { setError('Add at least one target URL'); return; }
    if (fields.some((f) => !f.name.trim() || !f.description.trim())) {
      setError('All fields need a name and description'); return;
    }

    createMutation.mutate({
      name: name.trim(),
      description: description.trim() || undefined,
      targetUrls,
      fields,
      autoHeal,
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="border-b bg-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center space-x-4">
            <Link
              href="/scrapers"
              className="text-gray-500 hover:text-gray-700 transition"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Create Scraper</h1>
              <p className="text-sm text-gray-500 mt-1">
                Define what to scrape and how to identify the data
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <form onSubmit={handleSubmit} className="space-y-8">

          {/* Error banner */}
          {error && (
            <div className="flex items-center space-x-2 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {/* Basic Info */}
          <section className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold mb-4">Basic Information</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Product Prices Scraper"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="What does this scraper do?"
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none"
                />
              </div>
              <div className="flex items-center space-x-3">
                <input
                  id="autoHeal"
                  type="checkbox"
                  checked={autoHeal}
                  onChange={(e) => setAutoHeal(e.target.checked)}
                  className="w-4 h-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                />
                <label htmlFor="autoHeal" className="text-sm text-gray-700">
                  Enable auto-healing (scraper adapts when the site changes)
                </label>
              </div>
            </div>
          </section>

          {/* Target URLs */}
          <section className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-semibold mb-1">Target URLs</h2>
            <p className="text-sm text-gray-500 mb-4">Pages to scrape</p>

            <div className="flex space-x-2 mb-4">
              <input
                type="text"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addUrl())}
                placeholder="https://example.com/products"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
              />
              <button
                type="button"
                onClick={addUrl}
                className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition flex items-center space-x-1"
              >
                <Plus className="w-4 h-4" />
                <span>Add</span>
              </button>
            </div>

            {targetUrls.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4 border-2 border-dashed border-gray-200 rounded-lg">
                No URLs added yet
              </p>
            ) : (
              <ul className="space-y-2">
                {targetUrls.map((url, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded-lg text-sm"
                  >
                    <span className="text-gray-700 truncate">{url}</span>
                    <button
                      type="button"
                      onClick={() => removeUrl(i)}
                      className="ml-2 text-gray-400 hover:text-red-500 transition flex-shrink-0"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Fields */}
          <section className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-lg font-semibold">Data Fields</h2>
              <button
                type="button"
                onClick={addField}
                className="text-sm text-primary-600 hover:text-primary-700 flex items-center space-x-1"
              >
                <Plus className="w-4 h-4" />
                <span>Add field</span>
              </button>
            </div>
            <p className="text-sm text-gray-500 mb-4">
              Describe each piece of data you want to extract. Plain-language descriptions help
              PixelRAG locate visual elements automatically.
            </p>

            <div className="space-y-4">
              {fields.map((field, idx) => (
                <div
                  key={idx}
                  className="border border-gray-200 rounded-lg p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                      Field {idx + 1}
                    </span>
                    {fields.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeField(idx)}
                        className="text-gray-400 hover:text-red-500 transition"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Field name <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={field.name}
                        onChange={(e) => updateField(idx, { name: e.target.value })}
                        placeholder="e.g. price"
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">
                        Type
                      </label>
                      <select
                        value={field.fieldType}
                        onChange={(e) =>
                          updateField(idx, { fieldType: e.target.value as FieldDraft['fieldType'] })
                        }
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                      >
                        {FIELD_TYPES.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      Description <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={field.description}
                      onChange={(e) => updateField(idx, { description: e.target.value })}
                      placeholder='e.g. "The product price shown in red near the Buy button"'
                      className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                    />
                  </div>

                  <div className="flex items-center space-x-2">
                    <input
                      id={`required-${idx}`}
                      type="checkbox"
                      checked={field.isRequired}
                      onChange={(e) => updateField(idx, { isRequired: e.target.checked })}
                      className="w-4 h-4 text-primary-600 rounded border-gray-300"
                    />
                    <label htmlFor={`required-${idx}`} className="text-xs text-gray-600">
                      Required field
                    </label>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Submit */}
          <div className="flex items-center justify-end space-x-3 pb-8">
            <Link
              href="/scrapers"
              className="px-6 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-6 py-2.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 disabled:opacity-60 transition flex items-center space-x-2"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Creating...</span>
                </>
              ) : (
                <span>Create Scraper</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
