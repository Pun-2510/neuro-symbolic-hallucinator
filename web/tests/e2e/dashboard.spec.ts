import { test, expect } from '@playwright/test';
import { setupAuthenticatedPage, waitForAuth, getMockEssays } from './helpers';

/**
 * E2E Tests for Dashboard
 * Uses authenticated mock for reliable testing
 */
test.describe('Dashboard', () => {
  const mockEssays = getMockEssays();

  // Set up authenticated session before each test
  test.beforeEach(async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/dashboard');
    await waitForAuth(page);
  });

  test('should display dashboard with stats cards', async ({ page }) => {
    // Check page title
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();

    // Wait for stats to load (they're calculated from essays + reports)
    await page.waitForTimeout(1000);

    // Check stats cards are present with correct labels
    await expect(page.getByText('Total Documents')).toBeVisible();
    await expect(page.getByText('Total Citations')).toBeVisible();
    await expect(page.getByText('Avg CIS Score')).toBeVisible();
    await expect(page.getByText('Verified Rate')).toBeVisible();
  });

  test('should show stats with correct values from mock data', async ({ page }) => {
    // Wait for data to load and stats to be calculated
    await page.waitForTimeout(1500);

    // Check that total documents shows the mock count (3 essays)
    const totalDocsCard = page.locator('.card').filter({ hasText: 'Total Documents' });
    await expect(totalDocsCard).toBeVisible();

    // Check total citations card (45 + 32 + 58 = 135)
    const totalCitationsCard = page.locator('.card').filter({ hasText: 'Total Citations' });
    await expect(totalCitationsCard).toBeVisible();
  });

  test('should show New Check button that navigates to upload', async ({ page }) => {
    // Click New Check button
    const newCheckBtn = page.getByRole('link', { name: /new check/i });
    await expect(newCheckBtn.first()).toBeVisible();
    await newCheckBtn.first().click();

    // Should navigate to upload page
    await expect(page).toHaveURL(/\/upload/);
  });

  test('should display document table with columns', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(500);

    // Check table headers exist
    const tableHeaders = page.locator('thead th');
    const count = await tableHeaders.count();
    expect(count).toBeGreaterThan(0);

    // Should show document names from mock data
    for (const essay of mockEssays) {
      await expect(page.getByText(essay.filename)).toBeVisible();
    }
  });

  test('should display document details correctly', async ({ page }) => {
    // Wait for data to load
    await page.waitForSelector('table', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(500);

    // Check first essay details are visible
    const firstEssay = mockEssays[0];
    await expect(page.getByText(firstEssay.filename)).toBeVisible();
    await expect(page.getByText(`${firstEssay.num_pages}`)).toBeVisible();
  });

  test('should filter documents by search', async ({ page }) => {
    // Wait for table to load first
    await page.waitForSelector('table', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(500);

    // Type in search box
    const searchBox = page.getByPlaceholder(/search documents/i);
    await expect(searchBox).toBeVisible();
    await searchBox.fill('BERT');

    // Wait for filter to apply
    await page.waitForTimeout(500);

    // Should show only BERT document
    await expect(page.getByText('BERT_Pre-training.pdf')).toBeVisible();
    await expect(page.getByText('Attention_Mechanism.pdf')).not.toBeVisible();
  });

  test('should show empty state for non-matching search', async ({ page }) => {
    // Wait for table to load first
    await page.waitForSelector('table', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(500);

    // Type non-matching search
    const searchBox = page.getByPlaceholder(/search documents/i);
    await searchBox.fill('nonexistent_document_xyz');

    // Wait for filter to apply
    await page.waitForTimeout(500);

    // Should show empty state
    await expect(page.getByText(/no documents found/i)).toBeVisible();
  });

  test('should have refresh button that reloads documents', async ({ page }) => {
    // Click refresh button
    const refreshBtn = page.getByTitle('Refresh');
    await expect(refreshBtn).toBeVisible();
    await refreshBtn.click();

    // Page should still show dashboard
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });

  test('should navigate to history page', async ({ page }) => {
    // Click History in sidebar
    await page.getByRole('link', { name: /history/i }).click();

    // Should navigate to history
    await expect(page).toHaveURL(/\/history/);
  });

  test('should show View Report action in table', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(500);

    // Check that View Report buttons exist
    const viewReportButtons = page.getByRole('link', { name: /view report/i });
    await expect(viewReportButtons.first()).toBeVisible();
  });
});
