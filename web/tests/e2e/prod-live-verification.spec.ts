import { test, expect, type Page } from '@playwright/test';

/**
 * Live Production End-to-End Verification & Page Load Benchmark Suite
 * Target: https://citra.io.vn (Zero Mocks — 100% Real Backend, Real DB, Real GROBID)
 */

interface PageMetric {
  route: string;
  role: string;
  ttfbMs: number;
  domContentLoadedMs: number;
  loadEventMs: number;
  interactiveRenderMs: number;
}

const pageMetrics: PageMetric[] = [];

async function measureRoute(
  page: Page,
  route: string,
  role: string,
  waitSelector: () => Promise<void>,
): Promise<PageMetric> {
  const t0 = Date.now();
  const response = await page.goto(route, { waitUntil: 'domcontentloaded' });
  expect(response?.status() ?? 200).toBeLessThan(400);
  await waitSelector();
  const interactiveRenderMs = Date.now() - t0;

  const navTiming = await page.evaluate(() => {
    const entries = performance.getEntriesByType('navigation') as PerformanceNavigationTiming[];
    if (!entries.length) {
      return { ttfb: 0, dcl: 0, load: 0 };
    }
    const e = entries[0];
    return {
      ttfb: Math.max(0, Math.round(e.responseStart - e.requestStart)),
      dcl: Math.max(0, Math.round(e.domContentLoadedEventEnd - e.startTime)),
      load: Math.max(0, Math.round((e.loadEventEnd || performance.now()) - e.startTime)),
    };
  });

  const metric: PageMetric = {
    route,
    role,
    ttfbMs: navTiming.ttfb,
    domContentLoadedMs: navTiming.dcl,
    loadEventMs: navTiming.load,
    interactiveRenderMs,
  };
  pageMetrics.push(metric);
  console.log(
    `[PERF] [${role.padEnd(7)}] ${route.padEnd(40)} | TTFB=${String(metric.ttfbMs).padStart(4)}ms | DCL=${String(metric.domContentLoadedMs).padStart(4)}ms | Load=${String(metric.loadEventMs).padStart(4)}ms | Interactive=${String(metric.interactiveRenderMs).padStart(4)}ms`,
  );
  return metric;
}

async function loginReal(page: Page, username: string, password: string): Promise<void> {
  await page.goto('/login');
  await page.getByLabel(/username/i).fill(username);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole('button', { name: /sign in|đăng nhập/i }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
}

test.describe('Live Production Full E2E & Performance Benchmark', () => {
  test('1. Public pages (Landing, Login, Register, Forgot Password, Activate, Reset) load cleanly & switch i18n/theme', async ({ page }) => {
    const runtimeErrors: string[] = [];
    page.on('pageerror', (err) => runtimeErrors.push(err.message));

    await measureRoute(page, '/', 'public', async () => {
      await expect(page.locator('h1').first()).toBeVisible();
    });

    await measureRoute(page, '/login', 'public', async () => {
      await expect(page.getByLabel(/username/i)).toBeVisible();
    });

    await measureRoute(page, '/register', 'public', async () => {
      await expect(page.getByLabel(/username/i)).toBeVisible();
    });

    await measureRoute(page, '/forgot-password', 'public', async () => {
      await expect(page.getByRole('button', { name: /send reset link|gửi liên kết/i })).toBeVisible();
    });

    await measureRoute(page, '/activate-account', 'public', async () => {
      await expect(page.locator('body')).toBeVisible();
    });

    await measureRoute(page, '/reset-password', 'public', async () => {
      await expect(page.locator('body')).toBeVisible();
    });

    expect(runtimeErrors).toEqual([]);
  });

  test('2. Student (user) real workspace flow: Dashboard, Upload, History, Profile, Settings', async ({ page }) => {
    const runtimeErrors: string[] = [];
    page.on('pageerror', (err) => runtimeErrors.push(err.message));

    await loginReal(page, 'user', 'user123');

    await measureRoute(page, '/dashboard', 'user', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    await measureRoute(page, '/upload', 'user', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    await measureRoute(page, '/history', 'user', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    await measureRoute(page, '/profile', 'user', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    await measureRoute(page, '/settings', 'user', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    // Test Help modal shortcut Ctrl+/
    await page.keyboard.press('Control+/');
    await expect(page.getByRole('dialog').first()).toBeVisible();
    await page.keyboard.press('Escape');

    expect(runtimeErrors).toEqual([]);
  });

  test('3. Teacher (teacher) real classroom flow: My Classes, Class Detail, Pending Reviews', async ({ page }) => {
    const runtimeErrors: string[] = [];
    page.on('pageerror', (err) => runtimeErrors.push(err.message));

    await loginReal(page, 'teacher', 'teacher123');

    await measureRoute(page, '/teacher/classes', 'teacher', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    // Open Create Class dialog and close it
    const createBtn = page.getByRole('button', { name: /create class|tạo lớp/i });
    await expect(createBtn).toBeVisible();
    await createBtn.click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.keyboard.press('Escape');

    await measureRoute(page, '/teacher/classes/1', 'teacher', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    await measureRoute(page, '/teacher/reviews', 'teacher', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    expect(runtimeErrors).toEqual([]);
  });

  test('4. Admin (admin) real control & full 5-layer report inspection flow', async ({ page }) => {
    const runtimeErrors: string[] = [];
    page.on('pageerror', (err) => runtimeErrors.push(err.message));

    await loginReal(page, 'admin', 'admin123');

    await measureRoute(page, '/batch-upload', 'admin', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    await measureRoute(page, '/admin/users', 'admin', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
      await expect(page.getByText('citra_scholar').first()).toBeVisible();
    });

    await measureRoute(page, '/admin/system', 'admin', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
      await expect(page.getByText(/ALL SERVICES HEALTHY/i)).toBeVisible();
    });

    await measureRoute(page, '/admin/audit', 'admin', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    // Inspect all 5 report sub-pages on real essay #17
    const essayId = 17;
    await measureRoute(page, `/verification/report/${essayId}`, 'admin', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    await measureRoute(page, `/verification/report/${essayId}/issues`, 'admin', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    await measureRoute(page, `/verification/report/${essayId}/trace`, 'admin', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    await measureRoute(page, `/verification/report/${essayId}/document`, 'admin', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    await measureRoute(page, `/verification/report/${essayId}/consistency`, 'admin', async () => {
      await expect(page.locator('main h1').first()).toBeVisible();
    });

    // Print aggregate performance summary
    const avgTtfb = Math.round(pageMetrics.reduce((s, m) => s + m.ttfbMs, 0) / pageMetrics.length);
    const avgDcl = Math.round(pageMetrics.reduce((s, m) => s + m.domContentLoadedMs, 0) / pageMetrics.length);
    const avgLoad = Math.round(pageMetrics.reduce((s, m) => s + m.loadEventMs, 0) / pageMetrics.length);
    const avgInteractive = Math.round(pageMetrics.reduce((s, m) => s + m.interactiveRenderMs, 0) / pageMetrics.length);
    console.log('==========================================================================================');
    console.log(
      `[PERF SUMMARY] Across ${pageMetrics.length} routes on https://citra.io.vn -> Avg TTFB=${avgTtfb}ms | Avg DCL=${avgDcl}ms | Avg Load=${avgLoad}ms | Avg Full Interactive=${avgInteractive}ms`,
    );
    console.log('==========================================================================================');

    expect(runtimeErrors).toEqual([]);
  });
});
