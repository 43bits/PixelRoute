/**
 * API client for VisualQA-Scraper backend
 */

import axios, { AxiosInstance } from 'axios';
import type {
  Scraper,
  ScraperField,
  ScraperJob,
  VisualQuery,
  HealthStatus,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Response shapes ────────────────────────────────────────────────────────────

export interface ListScrapersResponse {
  scrapers: Scraper[];
  total: number;
  skip: number;
  limit: number;
}

export interface ListJobsResponse {
  jobs: ScraperJob[];
  total: number;
}

export interface JobResultsResponse {
  results: Record<string, unknown>[];
  total: number;
}

export interface RunScraperResponse {
  jobId: string;
  status: string;
  message: string;
}

export interface HealResponse {
  success: boolean;
  message: string;
  healCount: number;
}

export interface DeleteResponse {
  success: boolean;
  message: string;
}

export interface SyncResponse {
  synced: number;
  message: string;
}

export interface QueryHistoryResponse {
  queries: VisualQuery[];
  total: number;
}

// ── API client ─────────────────────────────────────────────────────────────────

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/api`,
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000,
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response) {
          console.error('API Error:', error.response.data);
        }
        return Promise.reject(error);
      }
    );
  }

  // ── Health ──────────────────────────────────────────────────────────────────

  async healthCheck(): Promise<HealthStatus> {
    const { data } = await this.client.get<HealthStatus>('/health');
    return data;
  }

  async detailedHealthCheck(): Promise<HealthStatus> {
    const { data } = await this.client.get<HealthStatus>('/health/detailed');
    return data;
  }

  // ── Scrapers ────────────────────────────────────────────────────────────────

  async listScrapers(params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<ListScrapersResponse> {
    const { data } = await this.client.get<ListScrapersResponse>('/scrapers', { params });
    return data;
  }

  async getScraper(id: string): Promise<Scraper> {
    const { data } = await this.client.get<Scraper>(`/scrapers/${id}`);
    return data;
  }

  async createScraper(scraperData: {
    name: string;
    description?: string;
    targetUrls: string[];
    fields: Array<{
      name: string;
      description: string;
      fieldType?: string;
      selector?: string;
      visualHints?: Record<string, unknown>;
      isRequired?: boolean;
    }>;
    autoHeal?: boolean;
  }): Promise<Scraper> {
    const { data } = await this.client.post<Scraper>('/scrapers', scraperData);
    return data;
  }

  async updateScraper(
    id: string,
    updates: {
      name?: string;
      description?: string;
      targetUrls?: string[];
      fields?: Partial<ScraperField>[];
      isActive?: boolean;
      autoHeal?: boolean;
    }
  ): Promise<Scraper> {
    const { data } = await this.client.patch<Scraper>(`/scrapers/${id}`, updates);
    return data;
  }

  async deleteScraper(id: string): Promise<DeleteResponse> {
    const { data } = await this.client.delete<DeleteResponse>(`/scrapers/${id}`);
    return data;
  }

  async runScraper(id: string, urls?: string[]): Promise<RunScraperResponse> {
    const { data } = await this.client.post<RunScraperResponse>(
      `/scrapers/${id}/run`,
      { urls }
    );
    return data;
  }

  async triggerSelfHeal(id: string): Promise<HealResponse> {
    const { data } = await this.client.post<HealResponse>(`/scrapers/${id}/heal`);
    return data;
  }

  // ── Jobs ────────────────────────────────────────────────────────────────────

  async getJobStatus(jobId: string): Promise<ScraperJob> {
    const { data } = await this.client.get<ScraperJob>(`/jobs/${jobId}`);
    return data;
  }

  async getJobResults(
    jobId: string,
    params?: { skip?: number; limit?: number }
  ): Promise<JobResultsResponse> {
    const { data } = await this.client.get<JobResultsResponse>(
      `/jobs/${jobId}/results`,
      { params }
    );
    return data;
  }

  async syncJobResults(jobId: string): Promise<SyncResponse> {
    const { data } = await this.client.post<SyncResponse>(`/jobs/${jobId}/sync`);
    return data;
  }

  async listScraperJobs(
    scraperId: string,
    params?: { skip?: number; limit?: number }
  ): Promise<ListJobsResponse> {
    const { data } = await this.client.get<ListJobsResponse>(
      `/jobs/scraper/${scraperId}`,
      { params }
    );
    return data;
  }

  // ── Query ───────────────────────────────────────────────────────────────────

  async queryVisual(params: {
    question: string;
    scraperId?: string;
    nResults?: number;
  }): Promise<VisualQuery> {
    const { data } = await this.client.post<VisualQuery>('/query/visual', params);
    return data;
  }

  async queryText(params: {
    question: string;
    scraperId?: string;
    limit?: number;
  }): Promise<VisualQuery> {
    const { data } = await this.client.post<VisualQuery>('/query/text', params);
    return data;
  }

  async getQueryHistory(params?: {
    skip?: number;
    limit?: number;
    scraperId?: string;
  }): Promise<QueryHistoryResponse> {
    const { data } = await this.client.get<QueryHistoryResponse>(
      '/query/history',
      { params }
    );
    return data;
  }

  async getQuery(queryId: string): Promise<VisualQuery> {
    const { data } = await this.client.get<VisualQuery>(`/query/${queryId}`);
    return data;
  }
}

export const api = new ApiClient();
export default api;
