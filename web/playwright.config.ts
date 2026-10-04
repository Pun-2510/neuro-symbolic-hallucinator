import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for Essay Integrity Checker E2E Tests
 * Uses REAL backend - no mocking
 * 
 * IMPORTANT: Start backend (port 8000) and frontend (port 5173) BEFORE running tests.
 */

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    expect: {
      timeout: 10000,
    },
  },
  timeout: 60000,
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  outputDir: 'test-results/',
});
