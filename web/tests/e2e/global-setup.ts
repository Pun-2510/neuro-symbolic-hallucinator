/**
 * Global Playwright Setup
 * Provides consistent mock data across all E2E tests
 *
 * Usage: Add to playwright.config.ts:
 *   setup: './tests/e2e/global-setup.ts'
 */

import { test as setup } from '@playwright/test';

// Mock data constants
export const MOCK_USER = { id: 1, username: 'admin', role: 'admin' };

export const MOCK_ESSAYS = [
  { id: 1, filename: 'thesis_ai_citations_2024.pdf', num_pages: 15, uploaded_at: '2026-08-11T10:00:00Z', user_id: 1 },
  { id: 2, filename: 'ml_survey_paper.pdf', num_pages: 22, uploaded_at: '2026-08-12T14:30:00Z', user_id: 1 },
];

export const MOCK_REPORT = {
  essay_id: 1,
  filename: 'thesis_ai_citations_2024.pdf',
  num_pages: 15,
  num_citations: 8,
  style_profile: {
    style: 'APA_LIKE',
    confidence: 0.92,
    apa_count: 6,
    ieee_count: 1,
    mixed_count: 1,
    numeric_count: 0,
    features: { uses_ampersand: true, uses_italic: true, has_year: true },
    ratios: { author_parens: 0.83 },
    explanation: 'Majority of citations use (Author, Year) format typical of APA style.',
  },
  linking_summary: {
    matched: 5,
    missing_reference: 1,
    uncited_reference: 1,
    in_text_mismatch: 0,
    duplicate_reference: 1,
    ambiguous_mapping: 0,
    style_inconsistent: 0,
    unresolved: 0,
  },
  cis: {
    score: 78.5,
    components: {
      verified_ratio: 0.75,
      metadata_accuracy: 0.82,
      in_text_bib_consistency: 0.88,
      format_consistency: 0.90,
      identifier_validity: 0.85,
    },
    weights_used: {
      verified_ratio: 0.35,
      metadata_accuracy: 0.25,
      in_text_bib_consistency: 0.25,
      format_consistency: 0.10,
      identifier_validity: 0.05,
    },
    num_citations: 8,
    num_unresolved: 0,
    disclaimer: 'CIS is NOT an essay score.',
  },
  verdicts: [
    {
      citation_id: 'v1',
      citation_raw: 'LeCun, Bengio, & Hinton, 2015',
      mapping_status: 'matched',
      mapping_confidence: 0.95,
      citation_link: { occurrence_id: 'o1', reference_id: 'r1', method: 'author_year', confidence: 0.95 },
      label: 'verified',
      confidence: 0.92,
      reasoning: 'Found in Crossref + OpenAlex with matching title "Deep Learning".',
      triggered_rules: ['R-VERIFIED-DOI', 'R-AUTHOR-YEAR'],
      mismatched_fields: [],
      matched_sources: [
        { source: 'crossref', matched_fields: ['title', 'authors', 'year'], checked_at: '2026-08-11T10:00:00Z', url: 'https://doi.org/10.1038/nature14539' },
        { source: 'openalex', matched_fields: ['title', 'year'], checked_at: '2026-08-11T10:00:01Z' },
      ],
      is_overridden: false,
    },
    {
      citation_id: 'v2',
      citation_raw: 'He, Zhang, Ren, & Sun, 2016',
      mapping_status: 'duplicate_reference',
      mapping_confidence: 0.70,
      label: 'verified',
      confidence: 0.88,
      reasoning: 'Found in Semantic Scholar. Duplicate entry in reference list.',
      triggered_rules: ['R-VERIFIED-S2', 'R-DUPLICATE'],
      mismatched_fields: [],
      matched_sources: [
        { source: 's2', matched_fields: ['title', 'authors'], checked_at: '2026-08-11T10:00:02Z' },
      ],
      is_overridden: false,
      style_penalty: 0.05,
    },
    {
      citation_id: 'v3',
      citation_raw: 'Smith & Doe, 2024',
      mapping_status: 'missing_reference',
      mapping_confidence: 0.45,
      label: 'suspected_hallucination',
      confidence: 0.25,
      reasoning: 'Not found in any source after querying all 4 databases.',
      triggered_rules: ['R-HALLUCINATION-NOT-FOUND'],
      mismatched_fields: ['title', 'authors', 'year'],
      matched_sources: [],
      is_overridden: false,
    },
    {
      citation_id: 'v4',
      citation_raw: 'Vaswani et al., 2017',
      mapping_status: 'matched',
      mapping_confidence: 0.98,
      label: 'verified',
      confidence: 0.95,
      reasoning: 'Found in all 4 sources. "Attention Is All You Need" - highly cited paper.',
      triggered_rules: ['R-VERIFIED-MULTI', 'R-HIGH-CONFIDENCE'],
      mismatched_fields: [],
      matched_sources: [
        { source: 'crossref', matched_fields: ['title', 'authors', 'year', 'doi'], checked_at: '2026-08-11T10:00:03Z', url: 'https://arxiv.org/abs/1706.03762' },
        { source: 'openalex', matched_fields: ['title', 'authors', 'year'], checked_at: '2026-08-11T10:00:04Z' },
      ],
      is_overridden: false,
    },
    {
      citation_id: 'v5',
      citation_raw: 'Brown et al., 2020',
      mapping_status: 'matched',
      mapping_confidence: 0.94,
      label: 'verified',
      confidence: 0.91,
      reasoning: 'GPT-3 paper found in Crossref and Semantic Scholar.',
      triggered_rules: ['R-VERIFIED-DOI', 'R-AUTHOR-YEAR'],
      mismatched_fields: [],
      matched_sources: [
        { source: 'crossref', matched_fields: ['title', 'authors', 'year'], checked_at: '2026-08-11T10:00:06Z' },
        { source: 's2', matched_fields: ['title', 'authors', 'year'], checked_at: '2026-08-11T10:00:07Z' },
      ],
      is_overridden: false,
    },
    {
      citation_id: 'v6',
      citation_raw: 'Goodfellow et al., 2016',
      mapping_status: 'matched',
      mapping_confidence: 0.97,
      label: 'metadata_error',
      confidence: 0.72,
      reasoning: 'Found in Crossref but year mismatch: cited as 2016, actual is 2015.',
      triggered_rules: ['R-YEAR-MISMATCH', 'R-PARTIAL-VERIFIED'],
      mismatched_fields: ['year'],
      matched_sources: [
        { source: 'crossref', matched_fields: ['title', 'authors'], checked_at: '2026-08-11T10:00:08Z' },
      ],
      is_overridden: false,
    },
    {
      citation_id: 'v7',
      citation_raw: '[7] Johnson & Williams, 2023',
      mapping_status: 'uncited_reference',
      mapping_confidence: 0.60,
      label: 'verified',
      confidence: 0.85,
      reasoning: 'Reference entry exists but no matching in-text citation.',
      triggered_rules: ['R-UNCITED-REF'],
      mismatched_fields: [],
      matched_sources: [
        { source: 'crossref', matched_fields: ['title', 'authors', 'year'], checked_at: '2026-08-11T10:00:09Z' },
      ],
      is_overridden: false,
    },
    {
      citation_id: 'v8',
      citation_raw: 'Unknown Author Paper, 2022',
      mapping_status: 'unresolved',
      mapping_confidence: 0.30,
      label: 'unresolved',
      confidence: 0.40,
      reasoning: 'Insufficient metadata to verify. Missing DOI and full author list.',
      triggered_rules: ['R-INSUFFICIENT-DATA'],
      mismatched_fields: [],
      matched_sources: [],
      is_overridden: false,
    },
  ],
  disclaimer: 'This is a demo report for testing purposes.',
};

// Setup for unauthenticated tests
setup('clear localStorage', async ({ page }) => {
  await page.goto('/');
  await page.evaluate(() => localStorage.removeItem('token'));
});
