/**
 * TypeScript types for VisualQA-Scraper
 */

export interface Scraper {
  id: string;
  name: string;
  description?: string;
  brightDataScraperId?: string;
  targetUrls: string[];
  status: 'DRAFT' | 'ACTIVE' | 'PAUSED' | 'ARCHIVED' | 'ERROR';
  isActive: boolean;
  autoHeal: boolean;
  lastHealed?: string;
  healCount: number;
  createdAt: string;
  updatedAt: string;
  fields?: ScraperField[];
  jobs?: ScraperJob[];
}

export interface ScraperField {
  id: string;
  scraperId: string;
  name: string;
  description: string;
  fieldType: 'TEXT' | 'NUMBER' | 'URL' | 'IMAGE' | 'DATE' | 'VISUAL';
  selector?: string;
  visualHints?: Record<string, any>;
  isRequired: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ScraperJob {
  id: string;
  scraperId: string;
  brightDataJobId?: string;
  urls: string[];
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
  progress: number;
  itemsScraped: number;
  errorCount: number;
  startedAt?: string;
  completedAt?: string;
  duration?: number;
  error?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ScraperResult {
  id: string;
  scraperId: string;
  jobId: string;
  url: string;
  scrapedAt: string;
  data: Record<string, any>;
  screenshotUrl?: string;
  tilesPath?: string;
  embeddingId?: string;
  metadata?: Record<string, any>;
  createdAt: string;
}

export interface VisualQuery {
  id: string;
  question: string;
  scraperId?: string;
  results: VisualQueryResult[];
  resultCount: number;
  answer?: string;
  duration: number;
  createdAt: string;
}

export interface VisualQueryResult {
  score: number;
  snippet: string;
  imageUrl?: string;
  metadata?: {
    resultId: string;
    url: string;
    scrapedAt: string;
    data: Record<string, any>;
  };
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version?: string;
  services?: {
    database: { status: string; connected: boolean };
    pixelrag: { status: string; model: string; device: string };
    bright_data: { status: string; configured: boolean };
  };
  config?: Record<string, any>;
}
