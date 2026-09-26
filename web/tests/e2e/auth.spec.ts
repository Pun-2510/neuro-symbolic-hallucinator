import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Authentication Flow
 * Tests login, logout, and protected route behavior
 */
test.describe('Authentication', () => {

  test.beforeEach(async ({ page }) => {
    // Clear local storage before each test
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should show login page for unauthenticated users', async ({ page }) => {
    await page.goto('/');

    // Click sign in button on landing page
    await page.getByRole('link', { name: /sign in/i }).first().click();

    // Should be on login page
    await expect(page).toHaveURL(/\/login/);

    // Should show login form
    await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible();
    await expect(page.getByLabel(/username/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
  });

  test('should login with valid credentials', async ({ page }) => {
    await page.goto('/login');

    // Fill login form with demo credentials
    await page.getByLabel(/username/i).fill('admin');
    await page.getByLabel(/password/i).fill('admin123');

    // Submit form
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Should show dashboard content
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    // Fill with invalid credentials
    await page.getByLabel(/username/i).fill('invalid');
    await page.getByLabel(/password/i).fill('wrongpassword');

    // Submit form
    await page.getByRole('button', { name: /sign in/i }).click();

    // Should show error message (check for invalid credentials text)
    await expect(page.getByText(/invalid username or password/i)).toBeVisible();

    // Should stay on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test('should redirect to dashboard when accessing login while authenticated', async ({ page }) => {
    // First login
    await page.goto('/login');
    await page.getByLabel(/username/i).fill('admin');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Now try to access login page directly
    await page.goto('/login');

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should logout and redirect to login', async ({ page }) => {
    // First login
    await page.goto('/login');
    await page.getByLabel(/username/i).fill('admin');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Click logout button in sidebar
    await page.getByRole('button', { name: /sign out/i }).click();

    // Wait for logout to complete
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    // Should be on login page
    await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible();
  });

  test('should block access to protected routes for unauthenticated users', async ({ page }) => {
    // Try to access dashboard directly
    await page.goto('/dashboard');

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);

    // Try to access upload page
    await page.goto('/upload');
    await expect(page).toHaveURL(/\/login/);

    // Try to access history page
    await page.goto('/history');
    await expect(page).toHaveURL(/\/login/);
  });

  test('should show user info in sidebar after login', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.getByLabel(/username/i).fill('admin');
    await page.getByLabel(/password/i).fill('admin123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Should show username in sidebar (use first() to avoid strict mode violation)
    await expect(page.getByText('admin').first()).toBeVisible();

    // Should show role label
    await expect(page.getByText(/admin/i).first()).toBeVisible();
  });
});
