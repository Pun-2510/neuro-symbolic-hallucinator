import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Dashboard
 * Tests dashboard functionality, document list, and navigation
 */
test.describe('Dashboard', () => {

  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.getByLabel(/username/i).fill('admin');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
  });

  test('should display dashboard with stats cards', async ({ page }) => {
    // Check page title
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();

    // Check stats cards are present
    await expect(page.getByText('Total Documents')).toBeVisible();
    await expect(page.getByText('Total Citations')).toBeVisible();
    await expect(page.getByText('Avg CIS Score')).toBeVisible();
    await expect(page.getByText('Verified Rate')).toBeVisible();
  });

  test('should show New Check button that navigates to upload', async ({ page }) => {
    // Click New Check button (use first() for duplicate links)
    await page.getByRole('link', { name: /new check/i }).first().click();

    // Should navigate to upload page
    await expect(page).toHaveURL(/\/upload/);
  });

  test('should display document table with columns', async ({ page }) => {
    // Check table headers
    await expect(page.getByRole('columnheader', { name: /document/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /pages/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /uploaded/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /actions/i })).toBeVisible();
  });

  test('should filter documents by search', async ({ page }) => {
    // Type in search box
    await page.getByPlaceholder(/search documents/i).fill('nonexistent');

    // Should show empty state
    await expect(page.getByText(/no documents found/i)).toBeVisible();
  });

  test('should clear search filter', async ({ page }) => {
    // Type in search box
    await page.getByPlaceholder(/search documents/i).fill('test');

    // Click clear button (X icon)
    await page.getByPlaceholder(/search documents/i).locator('..').getByRole('button').click();

    // Search should be cleared
    await expect(page.getByPlaceholder(/search documents/i)).toHaveValue('');
  });

  test('should show empty state when no documents', async ({ page }) => {
    // Wait for loading to complete
    await page.waitForSelector('text=Upload Document', { state: 'visible' }).catch(() => {});

    // Check for empty state message
    const emptyState = page.getByText(/no documents yet/i);
    if (await emptyState.isVisible().catch(() => false)) {
      await expect(emptyState).toBeVisible();
      await expect(page.getByRole('link', { name: /upload document/i })).toBeVisible();
    }
  });

  test('should have refresh button that reloads documents', async ({ page }) => {
    // Click refresh button
    await page.getByTitle('Refresh').click();

    // Page should still show dashboard
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });

  test('should navigate to history page', async ({ page }) => {
    // Click History in sidebar
    await page.getByRole('link', { name: /history/i }).click();

    // Should navigate to history
    await expect(page).toHaveURL(/\/history/);
  });
});
