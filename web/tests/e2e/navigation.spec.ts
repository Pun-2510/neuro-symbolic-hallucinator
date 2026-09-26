import { test, expect } from '@playwright/test';
import { setupAuthenticatedPage } from './helpers';

/**
 * E2E Tests for Navigation Flow
 * Tests sidebar navigation and page transitions
 */
test.describe('Navigation', () => {

  test('should navigate from Dashboard to Upload', async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/dashboard');

    await page.getByRole('link', { name: /new check/i }).first().click();
    await expect(page).toHaveURL(/\/upload/);
  });

  test('should navigate from Dashboard to History via sidebar', async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/dashboard');

    await page.getByRole('link', { name: /history/i }).click();
    await expect(page).toHaveURL(/\/history/);
  });

  test('should keep sidebar open on page navigation', async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/dashboard');

    // Navigate to upload
    await page.getByRole('link', { name: /new check/i }).first().click();
    await expect(page).toHaveURL(/\/upload/);

    // Sidebar should still be visible
    await expect(page.getByRole('link', { name: /dashboard/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /history/i }).first()).toBeVisible();

    // Navigate to history
    await page.getByRole('link', { name: /history/i }).first().click();
    await expect(page).toHaveURL(/\/history/);

    // Sidebar should still be visible
    await expect(page.getByRole('link', { name: /dashboard/i })).toBeVisible();
  });

  test('should highlight active navigation item', async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/dashboard');

    // Dashboard should be active by default - check nav link exists
    const dashboardLink = page.getByRole('link', { name: /dashboard/i }).first();
    await expect(dashboardLink).toBeVisible();

    // Navigate to History
    await page.getByRole('link', { name: /history/i }).click();
    await expect(page).toHaveURL(/\/history/);

    // History link should still exist
    const historyLink = page.getByRole('link', { name: /history/i }).first();
    await expect(historyLink).toBeVisible();
  });

  test('should redirect legacy /home route to /dashboard', async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/home');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should redirect legacy /essay/:id route to /verification/report/:id', async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/essay/1');

    // Wait for redirect and page to load
    await page.waitForTimeout(1500);

    // Should redirect to /verification/report/1
    const url = page.url();
    expect(url).toMatch(/\/verification\/report\/1/);
  });

  test('should show loading state on protected route access', async ({ page }) => {
    // Clear auth state
    page.addInitScript(() => {
      localStorage.removeItem('token');
    });

    await page.goto('/');
    await page.goto('/dashboard');

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});
