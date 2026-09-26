import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Navigation Flow
 * Uses REAL backend - no mocking
 */
test.describe('Navigation', () => {

  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.getByLabel(/username/i).fill('admin');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
  });

  test('should navigate from Dashboard to Upload', async ({ page }) => {
    await page.getByRole('link', { name: /new check/i }).first().click();
    await expect(page).toHaveURL(/\/upload/);
  });

  test('should navigate from Dashboard to History via sidebar', async ({ page }) => {
    await page.getByRole('link', { name: /history/i }).click();
    await expect(page).toHaveURL(/\/history/);
  });

  test('should keep sidebar open on page navigation', async ({ page }) => {
    // Navigate to upload
    await page.getByRole('link', { name: /new check/i }).first().click();
    await expect(page).toHaveURL(/\/upload/);

    // Sidebar should still be visible
    await expect(page.getByRole('link', { name: /dashboard/i }).first()).toBeVisible();

    // Navigate to history
    await page.getByRole('link', { name: /history/i }).first().click();
    await expect(page).toHaveURL(/\/history/);

    // Sidebar should still be visible
    await expect(page.getByRole('link', { name: /dashboard/i }).first()).toBeVisible();
  });

  test('should show loading state on protected route access', async ({ page }) => {
    // Clear auth state
    await page.evaluate(() => localStorage.removeItem('token'));

    // Access protected route
    await page.goto('/dashboard');

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });

  test('should redirect legacy /home route to /dashboard', async ({ page }) => {
    await page.goto('/home');
    await expect(page).toHaveURL(/\/dashboard/);
  });
});
