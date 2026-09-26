/**
 * Mock API Helper for E2E Tests
 * Provides consistent mock setup across all tests
 *
 * IMPORTANT: Mock APIs must be set up BEFORE any navigation happens.
 * Use page.addInitScript for auth/me to ensure it runs before AuthContext validates.
 */

import { Page, expect } from '@playwright/test';
import { MOCK_USER, MOCK_ESSAYS, MOCK_REPORT } from './global-setup';

/**
 * Set up mock API responses for authenticated pages
 * Call this BEFORE any page.goto() in beforeEach
 */
export function setupAuthenticatedMocks(page: Page): void {
  // Auth endpoints
  page.route('**/api/auth/me', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_USER),
    });
  });

  page.route('**/api/auth/login', (route) => {
    const body = route.request().postData();
    const data = JSON.parse(body || '{}');
    if (data.username === 'wrong') {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid username or password' }),
      });
    } else {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ token: 'test-token', user: MOCK_USER }),
      });
    }
  });

  page.route('**/api/auth/logout', (route) => {
    route.fulfill({ status: 200, body: JSON.stringify({ message: 'Logged out successfully' }) });
  });

  // Health endpoint
  page.route('**/api/health', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', version: '2.0.0', disclaimer: '' }),
    });
  });

  // Essays endpoints
  page.route('**/api/essays', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_ESSAYS),
    });
  });

  // Individual essay reports
  page.route('**/api/essays/1/report', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_REPORT),
    });
  });

  // Override endpoint
  page.route('**/api/essays/*/verdicts/*/override', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ...MOCK_REPORT.verdicts[0], is_overridden: true }),
    });
  });
}

/**
 * Set up mock with localStorage token BEFORE navigation
 * This also mocks the auth/me endpoint in the browser context
 * to ensure AuthContext validation succeeds
 */
export function setupAuthenticatedPage(page: Page): void {
  // Mock auth/me in the browser context FIRST (before navigation)
  // This ensures AuthContext.validateToken() gets a valid response
  page.addInitScript(() => {
    // Intercept fetch for auth/me in the browser
    const originalFetch = window.fetch;
    window.fetch = function(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
      const url = typeof input === 'string' ? input : (input instanceof URL ? input.href : input.url);
      if (url.includes('/api/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ id: 1, username: 'admin', role: 'admin' }),
        } as Response);
      }
      return originalFetch.apply(window, [input, init] as Parameters<typeof originalFetch>);
    };

    // Set localStorage token
    localStorage.setItem('token', 'test-token');
  });

  // Also setup route mocks for other endpoints
  setupAuthenticatedMocks(page);
}

/**
 * Clear authentication state
 */
export function clearAuthState(page: Page): void {
  page.addInitScript(() => {
    localStorage.removeItem('token');
  });
}

/**
 * Perform login via UI (for tests that need real login flow)
 */
export async function loginViaUI(page: Page, username = 'admin', password = 'admin123'): Promise<void> {
  await page.goto('/login');
  await page.getByLabel(/username/i).fill(username);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 10000 });
}

/**
 * Helper to wait for dashboard content to load
 */
export async function waitForDashboard(page: Page): Promise<void> {
  await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible({ timeout: 10000 });
}

/**
 * Helper to wait for essay page content to load
 */
export async function waitForEssayPage(page: Page): Promise<void> {
  await page.waitForSelector('text=Citation Integrity Score', { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(500); // Allow charts to render
}
