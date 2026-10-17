import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright override config — for Phase 4 teacher-flow tests only.
 *
 * Uses `vite preview` (port 4173) for the static dist. Backend API is mocked
 * via `page.route()` in the test itself; no FastAPI server required.
 *
 * Run:  pnpm exec playwright test tests/e2e/teacher-flow.spec.ts --config=playwright.config.override.ts
 */
export default defineConfig({
  testDir: './tests/e2e',
  testMatch: /teacher-flow\.spec\.ts/,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    expect: { timeout: 10000 },
  },
  timeout: 60000,
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  outputDir: 'test-results/',
});
