/**
 * E2E tests for Web UI v1.2 — Essay Integrity Checker.
 * Run with: npx playwright test
 */

import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Mock Data — v1.2 schema with 2-layer output
// ---------------------------------------------------------------------------

const MOCK_REPORT = {
  essay_id: 1,
  filename: 'essay_01_real_only.pdf',
  num_pages: 5,
  num_citations: 3,
  style_profile: {
    style: 'APA_LIKE',
    confidence: 0.85,
    apa_count: 3,
    ieee_count: 0,
    mixed_count: 0,
    features: { uses_ampersand: true, uses_italic: true },
    ratios: { author_parens: 1.0 },
    explanation: 'Tat ca citation su dung (Author, Year) format.',
  },
  linking_summary: {
    matched: 2,
    missing_reference: 0,
    uncited_reference: 0,
    in_text_mismatch: 0,
    duplicate_reference: 1,
    ambiguous_mapping: 0,
    style_inconsistent: 0,
    unresolved: 0,
  },
  cis: {
    score: 82.3,
    components: {
      verified_ratio: 0.67,
      metadata_accuracy: 0.83,
      in_text_bib_consistency: 0.90,
      format_consistency: 0.85,
      identifier_validity: 0.95,
    },
    weights_used: {
      verified_ratio: 0.35,
      metadata_accuracy: 0.25,
      in_text_bib_consistency: 0.25,
      format_consistency: 0.10,
      identifier_validity: 0.05,
    },
    num_citations: 3,
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
        { source: 'openalex', matched_fields: ['title', 'year'], checked_at: '2026-08-11T10:00:01Z', url: 'https://openalex.org/W1' },
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
      mapping_confidence: 0.60,
      label: 'suspected_hallucination',
      confidence: 0.35,
      reasoning: 'Not found in any source (4 sources queried).',
      triggered_rules: ['R-HALLUCINATION-NOT-FOUND'],
      mismatched_fields: ['title', 'authors', 'year'],
      matched_sources: [],
      is_overridden: false,
    },
  ],
  disclaimer: 'Demo report.',
};

// ---------------------------------------------------------------------------
// Route mocks
// ---------------------------------------------------------------------------

function mockReport(page: Page) {
  void page.route('**/api/essays/1/report', (route) => {
    void route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_REPORT),
    });
  });
}

function mockHealth(page: Page) {
  void page.route('**/api/health', (route) => {
    void route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', version: '1.2.0', disclaimer: '' }),
    });
  });
}

function mockOverride(page: Page) {
  void page.route('**/api/essays/*/verdicts/*/override', (route) => {
    void route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ...MOCK_REPORT.verdicts[0], is_overridden: true }),
    });
  });
}

// ---------------------------------------------------------------------------
// Upload Page
// ---------------------------------------------------------------------------

test('UploadPage: page loads with heading and 4-label legend', async ({ page }) => {
  await mockHealth(page);
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Upload Essay PDF' })).toBeVisible();
  await expect(page.getByText('4 nhãn citation:')).toBeVisible();
  await expect(page.getByText('Verified').first()).toBeVisible();
  await expect(page.getByText('Metadata error').first()).toBeVisible();
  await expect(page.getByText('Suspected hallucination').first()).toBeVisible();
  await expect(page.getByText('Unresolved').first()).toBeVisible();
});

// ---------------------------------------------------------------------------
// Essay Page — CIS Card
// ---------------------------------------------------------------------------

test('EssayPage: CIS score card shows score + 5 components', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await expect(page.getByText('essay_01_real_only.pdf')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Citation Integrity Score' })).toBeVisible();
  await expect(page.locator('.text-4xl.font-bold').first()).toContainText('82');
  await expect(page.getByText('verified_ratio')).toBeVisible();
});

test('EssayPage: export buttons JSON, CSV, PDF visible', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await expect(page.getByRole('link', { name: 'Export JSON' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Export CSV' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Export PDF' })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Essay Page — Style Profile Card
// ---------------------------------------------------------------------------

test('EssayPage: style profile shows style badge + confidence', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await expect(page.getByText('Style: APA-Like')).toBeVisible();
  // Confidence text visible
  await expect(page.locator('text=85%').first()).toBeVisible();
  // Explanation visible
  await expect(page.getByText(/Tat ca citation/)).toBeVisible();
});

// ---------------------------------------------------------------------------
// Essay Page — Citation Graph View
// ---------------------------------------------------------------------------

test('CitationGraphView: citations + mapping status badges visible', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await expect(page.getByText('LeCun, Bengio, & Hinton, 2015')).toBeVisible();
  await expect(page.getByText('He, Zhang, Ren, & Sun, 2016')).toBeVisible();
  await expect(page.getByText('Smith & Doe, 2024')).toBeVisible();
  // Status badges
  await expect(page.getByText('✓Matched').first()).toBeVisible();
  await expect(page.getByText('≡Duplicate').first()).toBeVisible();
  await expect(page.getByText('✗Missing Ref').first()).toBeVisible();
});

test('CitationGraphView: graph <-> table toggle works', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await page.getByRole('button', { name: 'Table' }).click();
  await expect(page.locator('table')).toBeVisible();
  await page.getByRole('button', { name: 'Graph' }).click();
  await expect(page.getByText('✓Matched').first()).toBeVisible();
});

test('CitationGraphView: table shows Integrity + Source columns', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await page.getByRole('button', { name: 'Table' }).click();
  await expect(page.getByRole('columnheader', { name: 'Integrity' })).toBeVisible();
  await expect(page.getByRole('columnheader', { name: 'Source' })).toBeVisible();
});

test('CitationGraphView: filter by mapping status', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  // Filter button for "Duplicate" status
  await page.getByRole('button', { name: 'Duplicate (1)' }).click();
  await expect(page.getByText('He, Zhang, Ren, & Sun, 2016')).toBeVisible();
  await expect(page.getByText('LeCun, Bengio, & Hinton, 2015')).not.toBeVisible();
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await expect(page.getByText('LeCun, Bengio, & Hinton, 2015')).toBeVisible();
});

test('CitationGraphView: filter by source label', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await page.getByRole('button', { name: 'Suspected (1)' }).click();
  await expect(page.getByText('Smith & Doe, 2024')).toBeVisible();
  await expect(page.getByText('LeCun, Bengio, & Hinton, 2015')).not.toBeVisible();
  await page.getByRole('button', { name: 'Clear filters' }).click();
});

test('CitationGraphView: stats bar shows citation count', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await expect(page.getByText(/3 \/ 3 citations/)).toBeVisible();
});

test('Override: opens in table view, shows form with label + status options', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  mockOverride(page);
  await page.goto('/essays/1');
  // Switch to table view for easier override testing
  await page.getByRole('button', { name: 'Table' }).click();
  await page.waitForTimeout(200);
  await expect(page.getByRole('columnheader', { name: 'Override' })).toBeVisible();
  // Click override button in table row
  await page.locator('button:has-text("Ghi đè")').first().click();
  await expect(page.getByText('Override Citation')).toBeVisible({ timeout: 3000 });
  await expect(page.getByText('Source Label')).toBeVisible();
  await expect(page.getByText('Mapping Status')).toBeVisible();
  await page.getByRole('button', { name: 'Hủy' }).click();
  await expect(page.getByText('Override Citation')).not.toBeVisible({ timeout: 3000 });
});

// ---------------------------------------------------------------------------
// Citation Detail Drawer
// ---------------------------------------------------------------------------

test('Drawer: opens on graph row click', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  // Graph view: click the citation row
  await page.getByText('LeCun, Bengio, & Hinton, 2015').click();
  await expect(page.getByRole('heading', { name: 'Citation Detail' })).toBeVisible();
  await page.keyboard.press('Escape');
});

test('Drawer: shows source + integrity badges', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await page.getByText('LeCun, Bengio, & Hinton, 2015').click();
  await expect(page.getByText('Source:').first()).toBeVisible();
  await expect(page.getByText('Integrity:').first()).toBeVisible();
});

test('Drawer: shows evidence source cards', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await page.getByText('LeCun, Bengio, & Hinton, 2015').click();
  await expect(page.getByText('Evidence').first()).toBeVisible();
  await expect(page.locator('text=crossref').first()).toBeVisible();
});

test('Drawer: shows reasoning + rules triggered', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await page.getByText('LeCun, Bengio, & Hinton, 2015').click();
  await expect(page.getByText('Reasoning').first()).toBeVisible();
  await expect(page.getByText('Rules triggered')).toBeVisible();
  await expect(page.getByText('R-VERIFIED-DOI')).toBeVisible();
});

test('Drawer: mismatched fields for suspected citation', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await page.getByText('Smith & Doe, 2024').click();
  await expect(page.getByText('Mismatched fields')).toBeVisible();
  await expect(page.getByText('✗ title')).toBeVisible();
});

test('Drawer: external link to source', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await page.getByText('LeCun, Bengio, & Hinton, 2015').click();
  await expect(page.getByRole('link', { name: 'Open' }).first()).toBeVisible();
});

// ---------------------------------------------------------------------------
// Mapping Summary
// ---------------------------------------------------------------------------

test('MappingSummary: counts per status visible', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.goto('/essays/1');
  await expect(page.getByText('Citation Mapping Summary')).toBeVisible();
  // Should have some matched count visible
  await expect(page.locator('text=matched').first()).toBeVisible();
});

// ---------------------------------------------------------------------------
// History Page
// ---------------------------------------------------------------------------

test('HistoryPage: loads without crash', async ({ page }) => {
  await mockHealth(page);
  await page.goto('/history');
  await expect(page.getByRole('heading', { name: 'History' })).toBeVisible();
});

// ---------------------------------------------------------------------------
// Responsive
// ---------------------------------------------------------------------------

test('Mobile: table view scrolls without breaking', async ({ page }) => {
  await mockHealth(page);
  mockReport(page);
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/essays/1');
  await page.getByRole('button', { name: 'Table' }).click();
  await expect(page.locator('table')).toBeVisible();
});
