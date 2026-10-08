import { test, expect } from '@playwright/test';

/**
 * Playwright tests for Essay Integrity Checker frontend
 * Tests new features: Help Modal, DOCX Export button
 */

test.describe('Help Modal', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
  });

  test('should open help modal with Ctrl+/ shortcut', async ({ page }) => {
    // Press Ctrl+/ to open help
    await page.keyboard.press('Control+/');

    // Check modal is visible
    await expect(page.locator('text=Welcome to Essay Integrity Checker')).toBeVisible();
  });

  test('should close help modal with Escape', async ({ page }) => {
    // Open help modal
    await page.keyboard.press('Control+/');
    await expect(page.locator('text=Welcome to Essay Integrity Checker')).toBeVisible();

    // Press Escape to close
    await page.keyboard.press('Escape');
    await expect(page.locator('text=Welcome to Essay Integrity Checker')).not.toBeVisible();
  });

  test('should show all help sections', async ({ page }) => {
    await page.keyboard.press('Control+/');

    // Check sidebar sections exist
    await expect(page.locator('text=Overview')).toBeVisible();
    await expect(page.locator('text=Getting Started')).toBeVisible();
    await expect(page.locator('text=Understanding Verdicts')).toBeVisible();
    await expect(page.locator('text=Keyboard Shortcuts')).toBeVisible();
  });

  test('should navigate between help sections', async ({ page }) => {
    await page.keyboard.press('Control+/');

    // Click on Getting Started
    await page.click('button:has-text("Getting Started")');
    await expect(page.locator('text=Upload Your Essay')).toBeVisible();

    // Click on Understanding Verdicts
    await page.click('button:has-text("Understanding Verdicts")');
    await expect(page.locator('text=VERIFIED')).toBeVisible();

    // Click on Keyboard Shortcuts
    await page.click('button:has-text("Keyboard Shortcuts")');
    await expect(page.locator('text=Keyboard Shortcuts').first()).toBeVisible();
  });

  test('should show verdict explanations', async ({ page }) => {
    await page.keyboard.press('Control+/');
    await page.click('button:has-text("Understanding Verdicts")');

    // Check all verdict types are explained
    await expect(page.locator('text=VERIFIED').first()).toBeVisible();
    await expect(page.locator('text=METADATA_ERROR')).toBeVisible();
    await expect(page.locator('text=SUSPECTED_HALLUCINATION')).toBeVisible();
    await expect(page.locator('text=UNRESOLVED')).toBeVisible();
    await expect(page.locator('text=RESOURCE')).toBeVisible();
  });
});

test.describe('DOCX Export Button', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/dashboard');
  });

  test('should have DOCX button on essay page', async ({ page }) => {
    // Go to history
    await page.click('text=History');
    await page.waitForURL('/history');

    // Check if there are any essays
    const essays = await page.locator('[data-testid="essay-item"], a[href^="/essays/"]').count();

    if (essays > 0) {
      // Click on first essay
      await page.locator('a[href^="/essays/"]').first().click();
      await page.waitForURL(/\/essays\/\d+/);

      // Check DOCX button exists
      await expect(page.locator('a:has-text("DOCX")')).toBeVisible();
    }
  });

  test('should have export buttons visible', async ({ page }) => {
    // Go to history
    await page.click('text=History');
    await page.waitForURL('/history');

    const essays = await page.locator('a[href^="/essays/"]').count();

    if (essays > 0) {
      await page.locator('a[href^="/essays/"]').first().click();
      await page.waitForURL(/\/essays\/\d+/);

      // All export formats should be visible
      await expect(page.locator('a:has-text("JSON")')).toBeVisible();
      await expect(page.locator('a:has-text("CSV")')).toBeVisible();
      await expect(page.locator('a:has-text("PDF")')).toBeVisible();
      await expect(page.locator('a:has-text("DOCX")')).toBeVisible();
    }
  });
});
