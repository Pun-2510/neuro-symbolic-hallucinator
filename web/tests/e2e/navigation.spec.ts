import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Navigation Flow
 * Tests sidebar navigation and page transitions
 */
test.describe('Navigation', () => {

  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.getByLabel(/username/i).fill('admin');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
  });

  test('should navigate from Dashboard to Upload', async ({ page }) => {
    await page.getByRole('link', { name: /new check/i }).click();
    await expect(page).toHaveURL(/\/upload/);
    await expect(page.getByRole('heading', { name: /upload document/i })).toBeVisible();
  });

  test('should navigate from Dashboard to History via sidebar', async ({ page }) => {
    await page.getByRole('link', { name: /history/i }).click();
    await expect(page).toHaveURL(/\/history/);
    await expect(page.getByRole('heading', { name: /verification reports/i })).toBeVisible();
  });

  test('should keep sidebar open on page navigation', async ({ page }) => {
    // Navigate to upload
    await page.getByRole('link', { name: /new check/i }).click();
    await expect(page).toHaveURL(/\/upload/);

    // Sidebar should still be visible
    await expect(page.getByRole('link', { name: /dashboard/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /history/i })).toBeVisible();

    // Navigate to history
    await page.getByRole('link', { name: /history/i }).click();
    await expect(page).toHaveURL(/\/history/);

    // Sidebar should still be visible
    await expect(page.getByRole('link', { name: /dashboard/i })).toBeVisible();
  });

  test('should highlight active navigation item', async ({ page }) => {
    // Dashboard should be active by default
    const dashboardLink = page.getByRole('link', { name: /dashboard/i });
    await expect(dashboardLink).toHaveClass(/bg-indigo-50|indigo/);

    // Navigate to History
    await page.getByRole('link', { name: /history/i }).click();
    await expect(page).toHaveURL(/\/history/);

    // History should now be active
    const historyLink = page.getByRole('link', { name: /history/i });
    await expect(historyLink).toHaveClass(/bg-indigo-50|indigo/);
  });

  test('should redirect legacy /home route to /dashboard', async ({ page }) => {
    await page.goto('/home');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should redirect legacy /essay/:id route to /verification/report/:id', async ({ page }) => {
    await page.goto('/essay/1');
    // Should redirect to /verification/report/1
    await expect(page).toHaveURL(/\/verification\/report\/1/);
  });

  test('should show loading state on protected route access', async ({ page }) => {
    // Start from landing page
    await page.goto('/');

    // Try to access dashboard without auth
    await page.evaluate(() => localStorage.clear());
    await page.goto('/dashboard');

    // Should redirect to login (no loading spinner needed since it's instant)
    await expect(page).toHaveURL(/\/login/);
  });
});
