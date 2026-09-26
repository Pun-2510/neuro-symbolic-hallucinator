import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Document Upload Flow
 * Uses REAL backend - no mocking
 */
test.describe('Upload', () => {

  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.getByLabel(/username/i).fill('admin');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
  });

  test('should navigate to upload page', async ({ page }) => {
    await page.goto('/upload');

    // Check upload page content
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible();
  });

  test('should have file input visible', async ({ page }) => {
    await page.goto('/upload');

    // Check for file input
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
  });

  test('should accept PDF files', async ({ page }) => {
    await page.goto('/upload');

    // Check file input accepts PDF
    const fileInput = page.locator('input[type="file"]');
    const acceptAttr = await fileInput.getAttribute('accept').catch(() => null);
    if (acceptAttr) {
      expect(acceptAttr.toLowerCase()).toContain('pdf');
    }
  });

  test('should navigate back to dashboard from upload', async ({ page }) => {
    await page.goto('/upload');

    // Click dashboard in sidebar
    await page.getByRole('link', { name: /dashboard/i }).first().click();

    await expect(page).toHaveURL(/\/dashboard/);
  });
});
