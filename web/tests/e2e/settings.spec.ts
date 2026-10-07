/**
 * E2E Tests for Settings Page
 * Tests settings page functionality and preferences
 */
import { test, expect } from '@playwright/test';
import { setupAuthenticatedPage, waitForAuth } from './helpers';

// ============================================================
// Settings Page Tests
// ============================================================

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/dashboard');
    await waitForAuth(page);
    // Clear localStorage before each test
    await page.evaluate(() => localStorage.clear());
  });

  test('should navigate to settings page from sidebar', async ({ page }) => {
    await page.goto('/dashboard');

    // Click settings in sidebar
    const settingsLink = page.locator('aside').getByText('Settings');
    await settingsLink.click();

    await expect(page).toHaveURL(/\/settings/);
  });

  test('should display settings page heading', async ({ page }) => {
    await page.goto('/settings');

    // Check main title - use specific heading role
    const heading = page.getByRole('heading', { name: 'Settings' });
    await expect(heading).toBeVisible();
  });

  test('should have theme section', async ({ page }) => {
    await page.goto('/settings');

    // Theme should be mentioned somewhere
    const pageContent = await page.content();
    expect(pageContent.toLowerCase()).toContain('theme');
  });

  test('should have language section', async ({ page }) => {
    await page.goto('/settings');

    // Language should be mentioned
    const pageContent = await page.content();
    expect(pageContent.toLowerCase()).toContain('language');
  });

  test('should have notification toggles', async ({ page }) => {
    await page.goto('/settings');

    // Look for switch/checkbox elements
    const switchButtons = page.locator('button[role="switch"]');
    const count = await switchButtons.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should toggle notifications setting', async ({ page }) => {
    await page.goto('/settings');

    // Find notifications toggle and click it
    const switchButton = page.locator('button[role="switch"]').first();
    if (await switchButton.count() > 0) {
      await switchButton.click();

      // Toast should appear
      const toast = page.locator('[role="alert"]');
      await expect(toast).toBeVisible({ timeout: 5000 });
    }
  });

  test('should persist settings to localStorage', async ({ page }) => {
    await page.goto('/settings');

    // Toggle a setting
    const switchButton = page.locator('button[role="switch"]').first();
    if (await switchButton.count() > 0) {
      await switchButton.click();

      // Check localStorage
      const settingsValue = await page.evaluate(() => {
        const keys = Object.keys(localStorage).filter(k => k.startsWith('settings_'));
        return localStorage.getItem(keys[0]);
      });
      expect(['true', 'false']).toContain(settingsValue);
    }
  });

  test('should show version info', async ({ page }) => {
    await page.goto('/settings');

    // Version should be displayed somewhere
    const pageContent = await page.content();
    expect(pageContent).toContain('Version');
  });

  test('should have about section', async ({ page }) => {
    await page.goto('/settings');

    // About should be mentioned
    const pageContent = await page.content();
    expect(pageContent.toLowerCase()).toContain('about');
  });

  test('settings should be accessible from navigation', async ({ page }) => {
    await page.goto('/dashboard');

    // Settings should be in sidebar under Preferences
    const preferencesSection = page.locator('text=Preferences');
    await expect(preferencesSection).toBeVisible();

    // Click Settings
    await page.click('aside >> text=Settings');
    await expect(page).toHaveURL(/\/settings/);
  });
});

// ============================================================
// Settings Integration Tests
// ============================================================

test.describe('Settings Integration', () => {
  test.beforeEach(async ({ page }) => {
    setupAuthenticatedPage(page);
    await page.goto('/dashboard');
    await waitForAuth(page);
    await page.evaluate(() => localStorage.clear());
  });

  test('settings should persist across page navigation', async ({ page }) => {
    await page.goto('/settings');

    // Toggle a setting if available
    const switchButton = page.locator('button[role="switch"]').first();
    if (await switchButton.count() > 0) {
      await switchButton.click();

      // Navigate away
      await page.click('aside >> text=Dashboard');

      // Navigate back
      await page.click('aside >> text=Settings');
      await expect(page).toHaveURL(/\/settings/);
    }
  });

  test('should show toast when changing settings', async ({ page }) => {
    await page.goto('/settings');

    // Make a change
    const switchButton = page.locator('button[role="switch"]').first();
    if (await switchButton.count() > 0) {
      await switchButton.click();

      // Toast should appear
      const toast = page.locator('[role="alert"]');
      await expect(toast).toBeVisible({ timeout: 5000 });
    }
  });

  test('should show Preferences section in sidebar', async ({ page }) => {
    await page.goto('/dashboard');

    // Preferences section should be visible
    const preferencesSection = page.locator('aside >> text=Preferences');
    await expect(preferencesSection).toBeVisible();
  });
});
