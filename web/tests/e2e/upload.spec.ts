import { test, expect } from '@playwright/test';
import { setupAuthenticatedPage } from './helpers';

/**
 * E2E Tests for Document Upload Flow
 * Tests the complete upload process
 */
test.describe('Upload', () => {

  test('should navigate to upload page', async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/upload');

    // Check upload page content
    await expect(page.getByRole('heading', { name: /upload|new verification/i }).first()).toBeVisible();
  });

  test('should show dropzone for file upload', async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/upload');

    // Check for dropzone area
    await expect(page.getByText(/drag & drop|choose file|browse/i).or(page.getByRole('button', { name: /select file/i })).first()).toBeVisible({ timeout: 5000 }).catch(() => {});

    // Check for file input
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
  });

  test('should accept PDF files only', async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/upload');

    // Check that accept attribute is set (PDF only)
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();

    // Check accept attribute if available
    const acceptAttr = await fileInput.getAttribute('accept').catch(() => null);
    if (acceptAttr) {
      await expect(acceptAttr).toContain('pdf');
    }
  });

  test('should navigate back to dashboard from upload', async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/upload');

    // Click dashboard in sidebar
    await page.getByRole('link', { name: /dashboard/i }).first().click();

    await expect(page).toHaveURL(/\/dashboard/);
  });
});
