import { test } from '@playwright/test';
import { setupAuthenticatedPage, waitForAuth } from './helpers';

test('debug - just visit dashboard', async ({ page }) => {
  setupAuthenticatedPage(page);
  page.on('console', msg => console.log('  [browser]', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('  [PAGEERROR]', err.message));
  page.on('requestfailed', req => console.log('  [REQFAIL]', req.url(), req.failure()?.errorText));
  await page.goto('/dashboard');
  await waitForAuth(page);
  await page.waitForTimeout(3000);
  const title = await page.title();
  console.log('Title:', title);
  const h1 = await page.locator('h1').first().textContent().catch(() => 'NO H1');
  console.log('H1:', h1);
});
