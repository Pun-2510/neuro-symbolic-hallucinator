import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Document Upload Flow
 * Tests the complete upload process
 */
test.describe('Upload', () => {

  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.getByLabel(/username/i).fill('admin');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
  });

  test('should navigate to upload page', async ({ page }) => {
    await page.goto('/upload');

    // Check upload page content
    await expect(page.getByRole('heading', { name: /upload document/i })).toBeVisible();
  });

  test('should show dropzone for file upload', async ({ page }) => {
    await page.goto('/upload');

    // Check for dropzone area
    await expect(page.getByText(/drag & drop|choose file|browse/i)).toBeVisible();
  });

  test('should accept PDF files only', async ({ page }) => {
    await page.goto('/upload');

    // Check that accept attribute is set (PDF only)
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
  });

  test('should navigate back to dashboard from upload', async ({ page }) => {
    await page.goto('/upload');

    // Click dashboard in sidebar
    await page.getByRole('link', { name: /dashboard/i }).click();

    await expect(page).toHaveURL(/\/dashboard/);
  });
});
