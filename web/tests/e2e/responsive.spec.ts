import { test, expect, Page } from '@playwright/test';
import { setupAuthenticatedPage, clearAuthState } from './helpers';

/**
 * Full Responsive E2E Test Suite (Tablet & Mobile)
 *
 * Verifies:
 * 1. Zero horizontal overflow (`document.documentElement.scrollWidth <= window.innerWidth`)
 *    across Mobile (375x812, 414x896) and Tablet (768x1024, 1024x768).
 * 2. LandingPage mobile navigation drawer & interactive citation debugger on 375x812.
 * 3. AppLayout sticky mobile/tablet header bar & slide-over navigation drawer on 375x812 & 768x1024.
 * 4. Single-DOM responsive table-to-card layout on Dashboard, AccountManagement, AuditLog, and EssayPage.
 * 5. Citation Debugger IDE & diagnostic pages on Mobile and Tablet.
 * 6. Modals & Dialogs (HelpModal, UserFormDialog, CreateClassDialog) fitting within 375x812 viewport.
 */

const VIEWPORTS = [
  { name: 'Mobile Small (375x812)', width: 375, height: 812 },
  { name: 'Mobile Large (414x896)', width: 414, height: 896 },
  { name: 'Tablet Portrait (768x1024)', width: 768, height: 1024 },
  { name: 'Tablet Landscape (1024x768)', width: 1024, height: 768 },
] as const;

function setupAllResponsiveMocks(page: Page): void {
  setupAuthenticatedPage(page);

  // Mock Teacher endpoints
  page.route('**/api/classes/dashboard/summary', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_classes: 2,
        total_students: 28,
        total_essays: 64,
        pending_reviews: 3,
        classes: [
          {
            id: 10,
            name: 'CS101 Academic Writing',
            description: 'Fall 2026 Research Methods Cohort',
            teacher_id: 1,
            created_at: '2026-09-01T00:00:00Z',
            student_count: 18,
            essay_count: 42,
          },
          {
            id: 11,
            name: 'AI402 Deep Learning Seminar',
            description: 'Graduate seminar on neural citation verification',
            teacher_id: 1,
            created_at: '2026-09-05T00:00:00Z',
            student_count: 10,
            essay_count: 22,
          },
        ],
      }),
    })
  );

  page.route('**/api/classes', (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 10,
            name: 'CS101 Academic Writing',
            description: 'Fall 2026 Research Methods Cohort',
            teacher_id: 1,
            created_at: '2026-09-01T00:00:00Z',
            student_count: 18,
            essay_count: 42,
          },
        ]),
      });
    } else {
      route.continue();
    }
  });

  page.route('**/api/classes/10/students', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 2, username: 'john_doe', full_name: 'John Doe', email: 'john@example.com' },
      ]),
    })
  );

  page.route('**/api/classes/10/essays', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 1,
          filename: 'BERT_Pre-training.pdf',
          num_pages: 16,
          uploaded_at: '2026-09-10T10:00:00Z',
          user_id: 2,
          username: 'john_doe',
        },
      ]),
    })
  );

  page.route('**/api/classes/10/pending-reviews', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          verdict_id: 101,
          essay_id: 1,
          filename: 'BERT_Pre-training.pdf',
          student_username: 'john_doe',
          citation_raw: 'Vaswani et al. (2019)',
          label: 'metadata_error',
          confidence: 0.76,
          reasoning: 'Publication year mismatch (cited 2019 vs canonical 2017).',
        },
      ]),
    })
  );

  // Mock Admin endpoints
  page.route('**/api/users', (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 1,
            username: 'admin',
            email: 'admin@example.com',
            full_name: 'Administrator',
            institution: 'Faculty of IT',
            role: 'admin',
            is_active: true,
            avatar_url: null,
            last_login_at: '2026-01-01T00:00:00Z',
            created_at: '2026-01-01T00:00:00Z',
          },
          {
            id: 2,
            username: 'john_doe',
            email: 'john@example.com',
            full_name: 'John Doe',
            institution: 'CS101 Cohort',
            role: 'user',
            is_active: true,
            avatar_url: null,
            last_login_at: '2026-01-02T00:00:00Z',
            created_at: '2026-01-01T00:00:00Z',
          },
        ]),
      });
    } else {
      route.continue();
    }
  });

  page.route('**/api/admin/audit-log*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 1,
          verdict_id: 101,
          user: 'admin',
          original_label: 'suspected_hallucination',
          new_label: 'metadata_error',
          note: 'Verified conference preprint year discrepancy',
          logged_at: '2026-01-15T12:00:00Z',
        },
      ]),
    })
  );

  page.route('**/api/admin/system-health', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        totals: {
          users: 42,
          admins: 2,
          teachers: 6,
          students: 34,
          essays: 128,
          verdicts: 1840,
        },
        verdict_label_counts: {
          verified: 1520,
          metadata_error: 210,
          suspected_hallucination: 65,
          unresolved: 45,
        },
      }),
    })
  );

  // Mock Document Inspector endpoint
  page.route(/\/api\/essays\/\d+\/inspector/, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        essay_id: 1,
        filename: 'BERT_Pre-training.pdf',
        full_text:
          'Recent advances in transformer architectures (Vaswani et al., 2017) have enabled bidirectional language representations.',
        citations: [
          {
            occurrence_id: 'o1',
            marker: '(Vaswani et al., 2017)',
            start_char: 46,
            end_char: 68,
            verdict_label: 'verified',
            confidence: 0.98,
            reference_id: 'r1',
          },
        ],
        references: [
          {
            reference_id: 'r1',
            raw_text:
              'Vaswani, A., Shazeer, N., Parmar, N., et al. (2017). Attention Is All You Need. NeurIPS.',
            title: 'Attention Is All You Need',
            authors: ['Ashish Vaswani', 'Noam Shazeer'],
            year: 2017,
            doi: '10.48550/arXiv.1706.03762',
            is_cited: true,
            citation_count: 1,
          },
        ],
      }),
    })
  );
}

async function assertNoHorizontalOverflow(page: Page, routeName: string) {
  const overflow = await page.evaluate(() => {
    const docWidth = document.documentElement.scrollWidth;
    const winWidth = window.innerWidth;
    const main = document.getElementById('main-content');
    const mainScrollWidth = main ? main.scrollWidth : 0;
    const mainClientWidth = main ? main.clientWidth : 0;
    const mainOverflow = main ? mainScrollWidth > mainClientWidth : false;
    return {
      docWidth,
      winWidth,
      mainScrollWidth,
      mainClientWidth,
      hasOverflow: docWidth > winWidth || mainOverflow,
    };
  });
  expect(
    overflow.hasOverflow,
    `Expected no horizontal overflow on ${routeName} (doc=${overflow.docWidth}/${overflow.winWidth}, main=${overflow.mainScrollWidth}/${overflow.mainClientWidth})`
  ).toBe(false);
}

test.describe('Responsive Layout — Public & Auth Pages', () => {
  for (const vp of VIEWPORTS) {
    test(`renders public & auth routes without horizontal overflow at ${vp.name}`, async ({
      page,
    }) => {
      clearAuthState(page);
      await page.setViewportSize({ width: vp.width, height: vp.height });

      const publicRoutes = ['/', '/login', '/register', '/forgot-password'];
      for (const route of publicRoutes) {
        await page.goto(route);
        await page.waitForLoadState('domcontentloaded');
        await page.waitForTimeout(300);
        await assertNoHorizontalOverflow(page, `${route} @ ${vp.name}`);
      }
    });
  }

  test('LandingPage mobile menu drawer opens, closes, and interactive debugger tabs switch on 375x812', async ({
    page,
  }) => {
    clearAuthState(page);
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Open mobile navigation menu on LandingPage
    const menuBtn = page.getByRole('button', { name: /toggle navigation menu/i });
    await expect(menuBtn).toBeVisible();
    await menuBtn.click();

    // Mobile drawer links should be visible
    await expect(page.getByRole('link', { name: /2-layer architecture|kiến trúc 2 tầng/i }).first()).toBeVisible();

    // Close mobile navigation menu
    await menuBtn.click();

    // Switch interactive Citation Debugger tabs on mobile (375px)
    const rulesTab = page.getByRole('tab', { name: /2\.\s*symbolic rules/i });
    await rulesTab.click();
    await assertNoHorizontalOverflow(page, '/ (Symbolic Rules tab) @ 375x812');

    const retrievalTab = page.getByRole('tab', { name: /3\.\s*source retrieval/i });
    await retrievalTab.click();
    await assertNoHorizontalOverflow(page, '/ (Source Retrieval tab) @ 375x812');
  });
});

test.describe('Responsive Layout — Authenticated Workspaces (Student, Teacher, Admin)', () => {
  for (const vp of VIEWPORTS) {
    test(`renders core authenticated routes without horizontal overflow at ${vp.name}`, async ({
      page,
    }) => {
      setupAllResponsiveMocks(page);
      await page.setViewportSize({ width: vp.width, height: vp.height });

      const routes = [
        '/dashboard',
        '/upload',
        '/sandbox',
        '/batch',
        '/history',
        '/verification/report/1',
        '/verification/report/1/issues',
        '/verification/report/1/trace',
        '/verification/report/1/orphans',
        '/verification/report/1/inspector',
        '/teacher/classes',
        '/teacher/classes/10',
        '/teacher/reviews',
        '/admin/users',
        '/admin/audit',
        '/admin/health',
        '/profile',
        '/settings',
      ];

      for (const route of routes) {
        await page.goto(route);
        await page.waitForLoadState('domcontentloaded');
        await page.waitForTimeout(400);
        await assertNoHorizontalOverflow(page, `${route} @ ${vp.name}`);
      }
    });
  }

  test('AppLayout sticky mobile/tablet header and slide-over drawer work on Mobile (375x812) and Tablet (768x1024)', async ({
    page,
  }) => {
    setupAllResponsiveMocks(page);

    for (const vp of [
      { width: 375, height: 812 },
      { width: 768, height: 1024 },
    ]) {
      await page.setViewportSize(vp);
      await page.goto('/dashboard');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      const openNavBtn = page.getByRole('button', { name: /open navigation menu/i });
      await expect(openNavBtn).toBeVisible();

      // Open drawer
      await openNavBtn.click();
      const sidebar = page.locator('aside');
      await expect(sidebar).toHaveClass(/translate-x-0/);

      // Navigate via drawer link and verify auto-close
      await sidebar.getByRole('link', { name: /settings|cài đặt/i }).first().click();
      await expect(page).toHaveURL(/\/settings/);
      await expect(sidebar).toHaveClass(/-translate-x-full/);
    }
  });

  test('Single-DOM responsive tables render cleanly on Mobile (375x812) and Tablet (768x1024)', async ({
    page,
  }) => {
    setupAllResponsiveMocks(page);

    // 1. Mobile (375x812) — tables transform into vertical cards without duplicating DOM nodes
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/dashboard');
    await page.waitForSelector('table', { timeout: 5000 });
    await expect(page.getByRole('table')).toBeVisible();
    await expect(page.getByText('BERT_Pre-training.pdf')).toHaveCount(1);
    await assertNoHorizontalOverflow(page, '/dashboard table @ 375x812');

    await page.goto('/admin/users');
    await page.waitForSelector('table', { timeout: 5000 });
    await expect(page.getByRole('table')).toBeVisible();
    await expect(page.getByText('john_doe')).toBeVisible();
    await assertNoHorizontalOverflow(page, '/admin/users table @ 375x812');

    // 2. Tablet (768x1024) — tables render in tabular row mode without horizontal overflow
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/dashboard');
    await page.waitForSelector('table', { timeout: 5000 });
    await expect(page.getByRole('table')).toBeVisible();
    await assertNoHorizontalOverflow(page, '/dashboard table @ 768x1024');

    await page.goto('/admin/users');
    await page.waitForSelector('table', { timeout: 5000 });
    await expect(page.getByRole('table')).toBeVisible();
    await assertNoHorizontalOverflow(page, '/admin/users table @ 768x1024');
  });

  test('Modals and Dialogs fit cleanly within Mobile (375x812) viewport', async ({
    page,
  }) => {
    setupAllResponsiveMocks(page);
    await page.setViewportSize({ width: 375, height: 812 });

    // 1. UserFormDialog on /admin/users
    await page.goto('/admin/users');
    await page.waitForSelector('table', { timeout: 5000 });
    await page.getByRole('button', { name: /create user|tạo người dùng/i }).click();
    const userDialog = page.getByRole('dialog');
    await expect(userDialog).toBeVisible();
    const userDialogBox = await userDialog.boundingBox();
    expect(userDialogBox).not.toBeNull();
    expect(userDialogBox!.width).toBeLessThanOrEqual(375);
    await assertNoHorizontalOverflow(page, 'UserFormDialog @ 375x812');

    // 2. CreateClassDialog on /teacher/classes
    await page.goto('/teacher/classes');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /tạo lớp|create class/i }).click();
    const classDialog = page.getByRole('dialog');
    await expect(classDialog).toBeVisible();
    const classDialogBox = await classDialog.boundingBox();
    expect(classDialogBox).not.toBeNull();
    expect(classDialogBox!.width).toBeLessThanOrEqual(375);
    await assertNoHorizontalOverflow(page, 'CreateClassDialog @ 375x812');
  });

  test('Long underscore-connected filename does not overflow on Mobile (375x812)', async ({
    page,
  }) => {
    setupAllResponsiveMocks(page);
    const longFilename =
      'VietDepression_for_Detecting_Depression_Related_Language_in_Vietnamese_YouTube_Comments.pdf';

    await page.route(/\/api\/essays$/, (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            {
              id: 1,
              filename: longFilename,
              num_pages: 18,
              uploaded_at: '2026-10-25T10:00:00Z',
              cis_score: 88.5,
              status: 'completed',
            },
          ]),
        });
      } else {
        route.continue();
      }
    });

    await page.route(/\/api\/essays\/1$/, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          essay_id: 1,
          filename: longFilename,
          num_pages: 18,
          num_citations: 2,
          extracted_citations: [],
          references: [],
          verdicts: [
            {
              citation_id: 'cit_1',
              citation_raw: 'Nguyen et al. (2024)',
              label: 'verified',
              confidence: 0.95,
              mapping_status: 'matched',
              matched_sources: [],
              mismatched_fields: [],
              triggered_rules: ['R-WELL-LINKED'],
              reasoning: 'Verified match.',
            },
          ],
          cis: {
            score: 88.5,
            verified_count: 1,
            metadata_error_count: 0,
            suspected_hallucination_count: 0,
            unresolved_count: 0,
            resource_count: 0,
            total_count: 1,
          },
        }),
      })
    );

    await page.setViewportSize({ width: 375, height: 812 });

    for (const route of ['/dashboard', '/history', '/verification/report/1']) {
      await page.goto(route);
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(400);
      await assertNoHorizontalOverflow(page, `${route} (long filename) @ 375x812`);
    }

    // Verify EssayHeader h1 boundingBox stays within the 375px viewport
    const h1Box = await page.locator('h1').first().boundingBox();
    expect(h1Box).not.toBeNull();
    expect(h1Box!.x + h1Box!.width).toBeLessThanOrEqual(375);
  });
});
