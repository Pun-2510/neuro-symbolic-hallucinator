/**
 * API client — v1.2 schema (2-layer: integrity mapping_status + source label).
 *
 * Base URL: import.meta.env.VITE_API_BASE_URL hoặc '/api' (Vite proxy).
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// --- Enums / Literal Types ---

export type CitationType =
  | 'in_text'
  | 'numeric'
  | 'reference_list'
  | 'doi'
  | 'url'
  | 'unknown';

export type ValidationLabel =
  | 'verified'
  | 'metadata_error'
  | 'suspected_hallucination'
  | 'unresolved';

export type CitationMappingStatus =
  | 'matched'
  | 'missing_reference'
  | 'uncited_reference'
  | 'in_text_mismatch'
  | 'duplicate_reference'
  | 'ambiguous_mapping'
  | 'style_inconsistent'
  | 'unresolved';

// --- Sub-types ---

export interface MappingMethod {
  type: 'doi' | 'numeric_index' | 'author_year' | 'fuzzy' | 'none';
  confidence: number;
}

export interface CitationLink {
  occurrence_id: string;
  reference_id: string;
  method: string;
  confidence: number;
}

export interface MatchedSource {
  source: string; // 'crossref' | 'openalex' | 's2' | 'arxiv'
  matched_fields: string[];
  checked_at: string;
  url?: string;
}

export interface StyleProfile {
  style: 'APA_LIKE' | 'IEEE_LIKE' | 'MIXED' | 'UNKNOWN';
  confidence: number;
  apa_count: number;
  ieee_count: number;
  mixed_count: number;
  features: Record<string, boolean | number>;
  ratios: Record<string, number>;
  explanation: string;
}

export interface MappingStatusSummary {
  matched: number;
  missing_reference: number;
  uncited_reference: number;
  in_text_mismatch: number;
  duplicate_reference: number;
  ambiguous_mapping: number;
  style_inconsistent: number;
  unresolved: number;
}

export interface OverrideRecord {
  overridden_at: string;
  previous_label?: ValidationLabel;
  previous_status?: CitationMappingStatus;
  new_label: ValidationLabel;
  new_status?: CitationMappingStatus;
  reason?: string;
  overridden_by?: string;
}

// --- Verdict (v1.2 — 2-layer) ---

export interface Verdict {
  citation_id: string;
  citation_raw: string;
  // Integrity layer (linking/)
  mapping_status: CitationMappingStatus;
  mapping_confidence: number;
  citation_link?: CitationLink;
  style_penalty?: number;
  domain_exception?: boolean;
  // Source layer (retrieval/)
  label: ValidationLabel;
  confidence: number;
  reasoning: string;
  triggered_rules: string[];
  mismatched_fields: string[];
  matched_sources: MatchedSource[];
  // Override / audit
  is_overridden: boolean;
  override_record?: OverrideRecord;
}

// --- CIS ---

export interface CIS {
  score: number;
  components: Record<string, number>;
  weights_used: Record<string, number>;
  num_citations: number;
  num_unresolved: number;
  disclaimer: string;
}

// --- Full Report ---

export interface AnalysisReport {
  essay_id: number;
  filename: string;
  num_pages: number;
  num_citations: number;
  // v1.2 new fields
  style_profile: StyleProfile;
  linking_summary: MappingStatusSummary;
  // Existing
  verdicts: Verdict[];
  cis: CIS;
  disclaimer: string;
}

// --- Upload ---

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

// --- Citation (from extraction) ---

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

// --- Override request ---

export interface OverrideRequest {
  verdict_id: string;
  new_label: ValidationLabel;
  new_mapping_status?: CitationMappingStatus;
  reason?: string;
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

  downloadReport: (id: number, format: 'json' | 'csv' | 'pdf' = 'json') =>
    `${BASE_URL}/essays/${id}/report?format=${format}`,

  overrideVerdict: (id: number, body: OverrideRequest) =>
    request<Verdict>(`/essays/${id}/verdicts/${body.verdict_id}/override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
};
