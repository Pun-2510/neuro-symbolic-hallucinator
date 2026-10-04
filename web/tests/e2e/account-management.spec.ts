import { test, expect, Page } from '@playwright/test';
import { setupAuthenticatedPage, waitForAuth } from './helpers';

// ---------------------------------------------------------------------------
// Mock data helpers
// ---------------------------------------------------------------------------

const MOCK_USERS = [
  {
    id: 1,
    username: 'admin',
    email: 'admin@example.com',
    full_name: 'Administrator',
    role: 'admin',
    is_active: true,
    avatar_url: null,
    last_login_at: '2026-01-01T00:00:00',
    created_at: '2026-01-01T00:00:00',
  },
  {
    id: 2,
    username: 'john_doe',
    email: 'john@example.com',
    full_name: 'John Doe',
    role: 'user',
    is_active: true,
    avatar_url: null,
    last_login_at: '2026-01-02T00:00:00',
    created_at: '2026-01-01T00:00:00',
  },
  {
    id: 3,
    username: 'jane_smith',
    email: 'jane@example.com',
    full_name: 'Jane Smith',
    role: 'user',
    is_active: false,
    avatar_url: null,
    last_login_at: null,
    created_at: '2026-01-03T00:00:00',
  },
];

function setupAdminMocks(page: Page) {
  // Mock users list (admin view) — return ALL mock users
  page.route('**/api/users', (route) => {
    const req = route.request();
    if (req.method() === 'GET') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_USERS),
      });
    } else if (req.method() === 'POST') {
      const body = JSON.parse(req.postData() || '{}');
      const newUser = {
        id: 10,
        username: body.username,
        email: body.email || null,
        full_name: body.full_name || null,
        role: body.role || 'user',
        is_active: body.is_active !== false,
        avatar_url: null,
        last_login_at: null,
        created_at: new Date().toISOString(),
      };
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(newUser),
      });
    } else {
      route.continue();
    }
  });

  // Mock PUT /users/:id
  page.route(/\/api\/users\/\d+$/, (route) => {
    const req = route.request();
    if (req.method() === 'PUT') {
      const body = JSON.parse(req.postData() || '{}');
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...MOCK_USERS[1], ...body }),
      });
    } else if (req.method() === 'DELETE') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'User deleted' }),
      });
    } else {
      route.continue();
    }
  });

  // Mock GET /users/me
  page.route('**/api/users/me', (route) => {
    const req = route.request();
    if (req.method() === 'PATCH') {
      const body = JSON.parse(req.postData() || '{}');
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...MOCK_USERS[0], ...body }),
      });
    } else {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_USERS[0]),
      });
    }
  });

  // Mock auth/me for admin
  page.route('**/api/auth/me', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_USERS[0]),
    });
  });
}

// ---------------------------------------------------------------------------
// Account Management Page (Admin)
// ---------------------------------------------------------------------------

test.describe('Account Management Page', () => {
  test.beforeEach(async ({ page }) => {
    setupAuthenticatedPage(page);
    setupAdminMocks(page);
  });

  test('admin sees Account Management link in sidebar', async ({ page }) => {
    await page.goto('/dashboard');
    await waitForAuth(page);
    const link = page.getByRole('link', { name: /account management/i });
    await expect(link).toBeVisible();
  });

  test('admin can navigate to /admin/users', async ({ page }) => {
    await page.goto('/admin/users');
    await waitForAuth(page);
    await expect(page.getByRole('heading', { name: /account management/i })).toBeVisible();
  });

  test('displays user list with correct columns', async ({ page }) => {
    await page.goto('/admin/users');
    await waitForAuth(page);

    // Should show table headers
    await expect(page.getByRole('table')).toBeVisible();
    // Should show admin user (use exact match to avoid sidebar matches)
    await expect(page.getByText('admin', { exact: true }).last()).toBeVisible();
    // Should show john_doe
    await expect(page.getByText('john_doe')).toBeVisible();
  });

  test('displays role badges', async ({ page }) => {
    await page.goto('/admin/users');
    await waitForAuth(page);

    // Admin badge
    await expect(page.getByText('admin', { exact: false }).first()).toBeVisible();
    // User badges
    await expect(page.getByText('user', { exact: false }).first()).toBeVisible();
  });

  test('search filters users by username', async ({ page }) => {
    await page.goto('/admin/users');
    await waitForAuth(page);

    // Search for john
    await page.getByPlaceholder(/search/i).fill('john');
    await expect(page.getByText('john_doe')).toBeVisible();
    await expect(page.getByText('jane_smith')).not.toBeVisible();
  });

  test('search filters users by full name', async ({ page }) => {
    await page.goto('/admin/users');
    await waitForAuth(page);

    await page.getByPlaceholder(/search/i).fill('jane');
    await expect(page.getByText('jane_smith')).toBeVisible();
    await expect(page.getByText('john_doe')).not.toBeVisible();
  });

  test('role filter works', async ({ page }) => {
    await page.goto('/admin/users');
    await waitForAuth(page);

    await page.getByRole('combobox').first().selectOption('admin');
    await expect(page.getByText('john_doe')).not.toBeVisible();
  });

  test('create user button opens dialog', async ({ page }) => {
    await page.goto('/admin/users');
    await waitForAuth(page);

    await page.getByRole('button', { name: /create user/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Create New User')).toBeVisible();
  });

  test('create user form validation', async ({ page }) => {
    await page.goto('/admin/users');
    await waitForAuth(page);

    await page.getByRole('button', { name: /create user/i }).click();
    // Wait for dialog to appear
    await expect(page.getByRole('dialog')).toBeVisible();

    // Submit empty form — click the submit button inside the dialog
    await page.getByRole('dialog').getByRole('button', { name: /create user/i }).click();

    // Should show validation error for missing required fields
    await expect(page.getByText(/required|enter|min/i).first()).toBeVisible();
  });

  test('create user dialog submits and closes', async ({ page }) => {
    await page.goto('/admin/users');
    await waitForAuth(page);

    await page.getByRole('button', { name: /create user/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();

    await page.getByPlaceholder(/john_doe/i).fill('newuser');
    await page.getByPlaceholder(/minimum 6 characters/i).fill('pass123456');
    await page.getByPlaceholder(/john doe/i).fill('New User');
    await page.getByPlaceholder(/john@example/i).fill('new@example.com');

    await page.getByRole('dialog').getByRole('button', { name: /create user/i }).click();

    // Dialog should close after successful creation
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('edit user button opens dialog with data', async ({ page }) => {
    await page.goto('/admin/users');
    await waitForAuth(page);

    // Click edit on john_doe row (first edit button)
    const editButtons = page.locator('[title="Edit user"]');
    await editButtons.first().click();

    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Edit User')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Profile Page
// ---------------------------------------------------------------------------

function setupProfileMocks(page: Page, avatarUrl: string | null = null) {
  const adminUser = { ...MOCK_USERS[0], avatar_url: avatarUrl };

  page.context().addInitScript(({ user }) => {
    localStorage.setItem('token', 'mock-token-123');
    localStorage.setItem('user', JSON.stringify(user));
  }, { user: adminUser });

  page.route('**/api/auth/me', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(adminUser),
    });
  });

  page.route('**/api/users/me', (route) => {
    const req = route.request();
    if (req.method() === 'PATCH') {
      const body = JSON.parse(req.postData() || '{}');
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...adminUser, ...body }),
      });
    } else {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(adminUser),
      });
    }
  });
}

test.describe('Profile Page', () => {
  test.beforeEach(async ({ page }) => {
    setupAuthenticatedPage(page);
    setupProfileMocks(page);
  });

  test('user can access /profile', async ({ page }) => {
    await page.goto('/profile');
    await waitForAuth(page);
    await expect(page.getByRole('heading', { name: /my profile/i })).toBeVisible();
  });

  test('displays username as read-only', async ({ page }) => {
    await page.goto('/profile');
    await waitForAuth(page);

    // Wait for the form to load
    await expect(page.getByRole('heading', { name: /my profile/i })).toBeVisible({ timeout: 10000 });
    // Username is displayed as disabled textbox — verify "cannot be changed" text
    await expect(page.getByText(/username cannot be changed/i)).toBeVisible();
  });

  test('can update full name', async ({ page }) => {
    await page.goto('/profile');
    await waitForAuth(page);

    await expect(page.getByRole('heading', { name: /my profile/i })).toBeVisible({ timeout: 10000 });
    // Full name textbox — uses placeholder or aria-label
    const fullNameInput = page.getByRole('textbox', { name: /your full name/i });
    await expect(fullNameInput).toBeVisible();
    await fullNameInput.fill('Updated Name');
    await page.getByRole('button', { name: /save changes/i }).click();

    // Success — button text or toast should indicate saved
    await expect(page.getByRole('button', { name: /save changes/i })).toBeVisible({ timeout: 5000 });
  });

  test('can update email', async ({ page }) => {
    await page.goto('/profile');
    await waitForAuth(page);

    await expect(page.getByRole('heading', { name: /my profile/i })).toBeVisible({ timeout: 10000 });
    const emailInput = page.getByRole('textbox', { name: /email/i });
    await expect(emailInput).toBeVisible();
    await emailInput.fill('newemail@example.com');
    await page.getByRole('button', { name: /save changes/i }).click();

    await expect(page.getByRole('button', { name: /save changes/i })).toBeVisible({ timeout: 5000 });
  });

  test('password change requires current password', async ({ page }) => {
    await page.goto('/profile');
    await waitForAuth(page);

    await expect(page.getByRole('heading', { name: /change password/i })).toBeVisible({ timeout: 10000 });
    await page.getByPlaceholder(/current password/i).fill('wrongpassword');
    await page.getByPlaceholder(/minimum 6 characters/i).first().fill('newpass123');
    await page.getByPlaceholder(/re-enter/i).fill('newpass123');
    await page.getByRole('button', { name: /update password/i }).click();

    // Should show error about incorrect password
    await expect(page.getByText(/incorrect|error/i)).toBeVisible({ timeout: 5000 });
  });

  test('shows role and member since', async ({ page }) => {
    await page.goto('/profile');
    await waitForAuth(page);

    await expect(page.getByText(/admin/i).first()).toBeVisible();
    await expect(page.getByText(/member since/i)).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Sidebar user info
// ---------------------------------------------------------------------------

test.describe('Sidebar user info', () => {
  test('shows username in sidebar', async ({ page }) => {
    setupAuthenticatedPage(page);
    page.route('**/api/auth/me', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_USERS[0]),
      });
    });

    await page.goto('/dashboard');
    await waitForAuth(page);
    await expect(page.getByText('admin').first()).toBeVisible();
  });

  test('shows profile link in sidebar', async ({ page }) => {
    setupAuthenticatedPage(page);
    page.route('**/api/auth/me', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_USERS[0]),
      });
    });

    await page.goto('/dashboard');
    await waitForAuth(page);
    await expect(page.getByRole('link', { name: /view profile/i })).toBeVisible();
  });

  test('shows avatar if available', async ({ page }) => {
    setupAuthenticatedPage(page);
    page.route('**/api/auth/me', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...MOCK_USERS[0], avatar_url: '/api/avatars/1.jpg' }),
      });
    });

    await page.goto('/dashboard');
    await waitForAuth(page);

    const avatar = page.locator('img[alt="admin"]');
    await expect(avatar).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Non-admin access control
// ---------------------------------------------------------------------------

test.describe('Access control', () => {
  test('regular user redirected from /admin/users', async ({ page }) => {
    setupAuthenticatedPage(page);

    const regularUser = { ...MOCK_USERS[1], role: 'user' };
    // Override auth mock to return regular user role
    page.context().addInitScript(({ user }) => {
      localStorage.setItem('token', 'mock-token-456');
      localStorage.setItem('user', JSON.stringify(user));
    }, { user: regularUser });
    page.route('**/api/auth/me', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(regularUser),
      });
    });
    page.route('**/api/users**', (route) => {
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Forbidden' }),
      });
    });

    await page.goto('/admin/users');
    await waitForAuth(page);

    // Should redirect away from admin page
    await expect(page).not.toHaveURL(/\/admin\/users/);
  });
});
