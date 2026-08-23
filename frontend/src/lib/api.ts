/**
 * API client for VisualQA-Scraper backend
 */

import axios, { AxiosInstance } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/api`,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Response interceptor for error handling
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

  // Health
  async healthCheck() {
    const { data } = await this.client.get('/health');
    return data;
  }

  async detailedHealthCheck() {
    const { data } = await this.client.get('/health/detailed');
    return data;
  }

  // Scrapers
  async listScrapers(params?: { skip?: number; limit?: number; status?: string }) {
    const { data } = await this.client.get('/scrapers', { params });
    return data;
  }

  async getScraper(id: string) {
    const { data } = await this.client.get(`/scrapers/${id}`);
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
      visualHints?: any;
      isRequired?: boolean;
    }>;
    autoHeal?: boolean;
  }) {
    const { data } = await this.client.post('/scrapers', scraperData);
    return data;
  }

  async updateScraper(
    id: string,
    updates: {
      name?: string;
      description?: string;
      targetUrls?: string[];
      fields?: any[];
      isActive?: boolean;
      autoHeal?: boolean;
    }
  ) {
    const { data } = await this.client.patch(`/scrapers/${id}`, updates);
    return data;
  }

  async deleteScraper(id: string) {
    const { data } = await this.client.delete(`/scrapers/${id}`);
    return data;
  }

  async runScraper(id: string, urls?: string[]) {
    const { data } = await this.client.post(`/scrapers/${id}/run`, { urls });
    return data;
  }

  async triggerSelfHeal(id: string) {
    const { data } = await this.client.post(`/scrapers/${id}/heal`);
    return data;
  }

  // Jobs
  async getJobStatus(jobId: string) {
    const { data } = await this.client.get(`/jobs/${jobId}`);
    return data;
  }

  async getJobResults(jobId: string, params?: { skip?: number; limit?: number }) {
    const { data } = await this.client.get(`/jobs/${jobId}/results`, { params });
    return data;
  }

  async syncJobResults(jobId: string) {
    const { data } = await this.client.post(`/jobs/${jobId}/sync`);
    return data;
  }

  async listScraperJobs(scraperId: string, params?: { skip?: number; limit?: number }) {
    const { data } = await this.client.get(`/jobs/scraper/${scraperId}`, { params });
    return data;
  }

  // Query
  async queryVisual(params: {
    question: string;
    scraperId?: string;
    nResults?: number;
  }) {
    const { data } = await this.client.post('/query/visual', params);
    return data;
  }

  async queryText(params: {
    question: string;
    scraperId?: string;
    limit?: number;
  }) {
    const { data } = await this.client.post('/query/text', params);
    return data;
  }

  async getQueryHistory(params?: {
    skip?: number;
    limit?: number;
    scraperId?: string;
  }) {
    const { data } = await this.client.get('/query/history', { params });
    return data;
  }

  async getQuery(queryId: string) {
    const { data } = await this.client.get(`/query/${queryId}`);
    return data;
  }
}

export const api = new ApiClient();
export default api;
