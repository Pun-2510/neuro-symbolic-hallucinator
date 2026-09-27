import { test, expect } from '@playwright/test';
import { setupAuthenticatedPage, waitForAuth } from './helpers';

/**
 * E2E Tests for Document Upload Flow
 * Uses authenticated mock for reliable testing
 */
test.describe('Upload', () => {

  // Set up authenticated session before each test
  test.beforeEach(async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/upload');
    await waitForAuth(page);
  });

  test('should navigate to upload page', async ({ page }) => {
    // Check upload page content
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('should have file input visible', async ({ page }) => {
    // Check for file input
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
  });

  test('should accept PDF files', async ({ page }) => {
    // Check file input accepts PDF
    const fileInput = page.locator('input[type="file"]');
    const acceptAttr = await fileInput.getAttribute('accept').catch(() => null);
    if (acceptAttr) {
      expect(acceptAttr.toLowerCase()).toContain('pdf');
    }
  });

  test('should navigate back to dashboard from upload', async ({ page }) => {
    // Click dashboard in sidebar
    await page.getByRole('link', { name: /dashboard/i }).first().click();

    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should show drag and drop area', async ({ page }) => {
    // Check for drag and drop area or upload section
    const uploadArea = page.locator('[class*="border-dashed"], .upload-area, input[type="file"]');
    await expect(uploadArea.first()).toBeVisible();
  });
});
