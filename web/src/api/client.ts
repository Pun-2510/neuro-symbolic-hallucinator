/**
 * API client — match backend Pydantic schemas (src/integrity_checker/models/api_schemas.py).
 *
 * Base URL: import.meta.env.VITE_API_BASE_URL hoặc '/api' (Vite proxy).
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// --- Types ---

export type CitationType = 'in_text' | 'numeric' | 'reference_list' | 'doi' | 'url' | 'unknown';
export type ValidationLabel =
  | 'verified'
  | 'metadata_error'
  | 'suspected_hallucination'
  | 'unresolved';

export interface Citation {
  raw_text: string;
  citation_type: CitationType;
  style: string;
  authors: string[];
  year?: string | null;
  title?: string | null;
  venue?: string | null;
  doi?: string | null;
  url?: string | null;
  page_num: number;
  confidence: number;
}

export interface Verdict {
  citation_raw: string;
  label: ValidationLabel;
  confidence: number;
  reasoning: string;
  triggered_rules: string[];
  mismatched_fields: string[];
  matched_sources: Record<string, unknown>;
  is_overridden: boolean;
}

export interface CIS {
  score: number;
  components: Record<string, number>;
  weights_used: Record<string, number>;
  num_citations: number;
  num_unresolved: number;
  disclaimer: string;
}

export interface AnalysisReport {
  essay_id: number;
  filename: string;
  num_pages: number;
  num_citations: number;
  verdicts: Verdict[];
  cis: CIS;
  disclaimer: string;
}

export interface UploadResponse {
  essay_id: number;
  filename: string;
  num_pages: number;
  num_citations: number;
  citations: Citation[];
  summary: {
    cis_score: number | null;
    num_unresolved: number;
  };
}

export interface HealthResponse {
  status: string;
  version: string;
  disclaimer: string;
}

// --- Helpers ---

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      ...init?.headers,
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API ${resp.status}: ${text}`);
  }
  return resp.json();
}

// --- Endpoints ---

export const api = {
  health: () => request<HealthResponse>('/health'),

  uploadEssay: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return request<UploadResponse>('/essays', {
      method: 'POST',
      body: fd,
    });
  },

  getEssay: (id: number) => request<AnalysisReport>(`/essays/${id}/report`),

  getVerdicts: (id: number) => request<Verdict[]>(`/essays/${id}/verdicts`),

  downloadReport: (id: number, format: 'json' | 'csv' = 'json') =>
    `${BASE_URL}/essays/${id}/report?format=${format}`,
};