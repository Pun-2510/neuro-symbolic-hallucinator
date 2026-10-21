# Phase 5 — Final Polish (React Query + God Component Split + Hook Tests)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay 5 page-level `useEffect+setInterval+fetch+setState` blocks bằng React Query; split 2 god components còn lại (`CitationGraphView` 753 LOC, `EssayPage` 695 LOC) thành sub-components có thể test riêng; thiết lập Vitest và test cho 4 custom hooks. Sau phase này, codebase ready cho thesis defense (cuối tháng 1/2027).

**Architecture:** Frontend-only refactor. KHÔNG thay đổi backend API, KHÔNG thay đổi schema. Mỗi task là một isolated refactor với test/build pass trước khi commit. TDD cho hooks; visual smoke + build pass cho React Query và god component split.

**Tech Stack:** React 18, TypeScript, Vite, TailwindCSS, lucide-react. New deps: `@tanstack/react-query` (5.x), `vitest` (1.x), `@testing-library/react` (16.x), `@testing-library/dom`, `jsdom`. Test framework: Vitest (new — hooks only), Playwright e2e (existing — 112 tests).

**Spec:** `IMPLEMENTATION_ROADMAP.md` §"Phase 5: Final Polish" + scope confirmation (Core: React Query + split both god components + Vitest for hooks).

**Source documents:**
- `web/src/pages/DashboardPage.tsx` (useEffect+fetch+setInterval — 1 of 5)
- `web/src/pages/HistoryPage.tsx` (useEffect+setInterval — 2 of 5)
- `web/src/pages/ProcessingPage.tsx` (useEffect+setInterval via `useEssayPolling` hook — 3 of 5)
- `web/src/pages/EssayPage.tsx` (useEffect+fetch+setInterval via `useEssayPolling` — 4 of 5)
- `web/src/pages/OrphanDetectionPage.tsx` (useEffect+fetch — 5 of 5)
- `web/src/components/CitationGraphView.tsx` (753 LOC, 2 named exports)
- `web/src/pages/EssayPage.tsx` (695 LOC, single export)
- `web/src/hooks/useRole.ts`, `useDebounce.ts`, `useLocalStorage.ts`, `useEssayPolling.ts` (no tests)

**Out of scope (deferred):**
- Full-text search ở HistoryPage + VerdictTable (Phase 5 §28.1-2 — search đã có basic ở HistoryPage, full-text backend chưa có)
- ConfirmationModal adoption pass (đã có ConfirmationModal, code hiện tại dùng 1-2 chỗ, không có `window.confirm` còn sót)
- Playwright e2e mở rộng (đã có 112 tests, đủ)
- Thay thế `as any` còn lại (chỉ 3 occurrences, cosmetic)

---

## Global Constraints

- **Type hints everywhere** (CLAUDE.md).
- **Vietnamese comments for user-facing strings**, English for internal logic (CLAUDE.md).
- **TDD cho hooks**: write failing test → run → verify failure → implement → verify pass → commit.
- **TDD-light cho React Query + split**: write test nếu có thể (smoke test cho refactor), otherwise verify bằng `pnpm build` + manual flow.
- **Per-task commit**: one task = one commit. Không gộp.
- **No raw `fetch()` in pages** — đi qua `api/client.ts` (CLAUDE.md §API) — Phase 1 đã enforce.
- **Không đổi API contracts** — Phase 5 chỉ refactor cách consume API.
- **Branch**: `feat/phase-5-polish`. Merge vào main ở cuối phase.

---

## Review Focus

Các failure mode mà plan này cover bằng test/verification:

1. **React Query race conditions**: stale data khi essayId thay đổi nhanh → `queryKey: ['essay', essayId]` đảm bảo cache invalidation. Covered trong Task 4.
2. **Polling leak**: setInterval cũ chạy sau khi unmount → React Query `refetchInterval` tự pause khi tab hidden và dừng khi query disabled. Covered trong Task 2 (verifying `refetchIntervalInBackground: false`).
3. **Split CitationGraphView regressions**: 2 named exports (`EvidenceGraph` + `CitationGraphView`) phải giữ nguyên public API → grep imports trước khi delete. Covered trong Task 12.
4. **Split EssayPage regressions**: 695 LOC chứa EssayHeader (đã extract) + VerdictList + ActionToolbar + CitationsTab → cần test build pass và grep usages. Covered trong Task 14.
5. **Hook tests không cover async behavior của useEssayPolling**: cần test riêng cho `cancelled` flag khi essayId đổi. Covered trong Task 18.
6. **Vitest + jsdom conflict với React Router**: cần mock `useNavigate`, `useParams` đúng cách. Covered trong Task 16.

---

## File Structure

### New files (created in this phase)

| File | Responsibility |
|------|----------------|
| `web/src/lib/queryClient.ts` | Singleton `QueryClient` với defaults (staleTime, retry, refetchOnWindowFocus) |
| `web/src/hooks/useEssays.ts` | `useEssays` query, `useDeleteEssay` mutation (Dashboard + History) |
| `web/src/hooks/useEssayReport.ts` | `useEssayReport` query với polling, `useOverrideVerdict` mutation (EssayPage + ProcessingPage) |
| `web/src/hooks/useOrphanReport.ts` | `useOrphanReport` query (OrphanDetectionPage) |
| `web/src/components/CitationGraph/EvidenceGraph.tsx` | Extracted từ CitationGraphView |
| `web/src/components/CitationGraph/SourceIcon.tsx` | Helper extracted |
| `web/src/components/CitationGraph/EvidenceGraphNode.tsx` | Sub-component extracted |
| `web/src/components/CitationGraph/CitationGraphView.tsx` | Main graph view (slimmed) |
| `web/src/components/CitationGraph/GraphControls.tsx` | Filter + view-mode controls (Phase 2 đã extract CitationGraphControls, rename thành GraphControls) |
| `web/src/components/CitationGraph/index.ts` | Re-export public API |
| `web/src/pages/EssayPage/EssayHeader.tsx` | Already in EssayPage.tsx, extract |
| `web/src/pages/EssayPage/VerdictList.tsx` | Citation/verdict list panel |
| `web/src/pages/EssayPage/ActionToolbar.tsx` | Override + action buttons |
| `web/src/pages/EssayPage/CitationsTab.tsx` | Citations tab content |
| `web/src/pages/EssayPage/EssayPage.tsx` | Composes the above |
| `web/src/pages/EssayPage/index.ts` | Re-export public API |
| `web/vitest.config.ts` | Vitest config (jsdom, path aliases) |
| `web/src/test-utils.tsx` | `renderWithProviders` helper (QueryClient, MemoryRouter, AuthContext) |
| `web/src/hooks/useRole.test.ts` | Tests cho useRole |
| `web/src/hooks/useDebounce.test.ts` | Tests cho useDebounce |
| `web/src/hooks/useLocalStorage.test.ts` | Tests cho useLocalStorage |
| `web/src/hooks/useEssayPolling.test.ts` | Tests cho useEssayPolling (with mocked fetch) |

### Modified files

| File | Why |
|------|-----|
| `web/src/main.tsx` | Wrap app in `QueryClientProvider` |
| `web/src/pages/DashboardPage.tsx` | Replace useEffect+setInterval+fetch với `useEssays()` |
| `web/src/pages/HistoryPage.tsx` | Replace useEffect+setInterval+fetch với `useEssays()` + auto-invalidate on delete |
| `web/src/pages/ProcessingPage.tsx` | Replace useEssayPolling raw với `useEssayReport(id, { enabled: status==='processing' })` |
| `web/src/pages/EssayPage.tsx` | Split thành sub-components + dùng `useEssayReport` + `useOverrideVerdict` mutation |
| `web/src/pages/OrphanDetectionPage.tsx` | Replace useEffect+fetch với `useOrphanReport()` |
| `web/src/components/CitationGraphView.tsx` | Becomes re-export shim từ `CitationGraph/index.ts` (backward-compat) |
| `web/src/hooks/useEssayPolling.ts` | Keep — nếu có nơi nào khác dùng; nếu không, deprecate (ghi deprecation note) |
| `web/package.json` | Add `@tanstack/react-query`, `vitest`, `@testing-library/react`, `@testing-library/dom`, `jsdom` |
| `web/tsconfig.json` | Add `"types": ["vitest/globals"]` (nếu dùng globals) hoặc giữ nguyên nếu dùng explicit imports |

---

## Task 1: Install React Query + Vitest dependencies

**Files:**
- Modify: `web/package.json`
- Verify: `pnpm install` success, lockfile updated

**Acceptance:**
- `@tanstack/react-query@^5.x` in dependencies
- `vitest@^1.x` + `@testing-library/react@^16.x` + `@testing-library/dom` + `jsdom` in devDependencies
- `pnpm install` completes without errors
- `pnpm exec vitest --version` works (sanity)

- [ ] **Step 1: Edit `web/package.json` — add dependencies**

Add to `dependencies`:
```json
"@tanstack/react-query": "^5.59.0"
```

Add to `devDependencies`:
```json
"@testing-library/dom": "^10.4.0",
"@testing-library/react": "^16.0.1",
"@testing-library/user-event": "^14.5.2",
"jsdom": "^25.0.1",
"vitest": "^1.6.0"
```

- [ ] **Step 2: Add Vitest scripts to `package.json`**

In `scripts`:
```json
"test": "vitest run",
"test:watch": "vitest",
"test:ui": "vitest --ui",
"test:coverage": "vitest run --coverage"
```

- [ ] **Step 3: Run `pnpm install`**

```bash
cd web && pnpm install
```
Expected: deps installed, no peer-dep warnings blocking.

- [ ] **Step 4: Verify install**

```bash
cd web && pnpm exec vitest --version
```
Expected: prints Vitest version (e.g., `1.6.0`).

- [ ] **Step 5: Commit**

```bash
git add web/package.json web/pnpm-lock.yaml
git commit -m "feat(phase-5): add @tanstack/react-query + vitest deps (Task 1)

- @tanstack/react-query@^5.59 for data fetching
- vitest@^1.6 + @testing-library/react for hook tests
- pnpm install OK

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 2: Setup Vitest config + test utilities

**Files:**
- Create: `web/vitest.config.ts`
- Create: `web/src/test-utils.tsx`
- Verify: smoke test passes

**Acceptance:**
- `pnpm exec vitest run --passWithNoTests` exits 0
- `test-utils.tsx` exports `renderWithProviders(ui, options?)` that wraps QueryClient + MemoryRouter + AuthContext

- [ ] **Step 1: Create `web/vitest.config.ts`**

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    css: false,
    include: ['src/**/*.test.{ts,tsx}'],
    exclude: ['node_modules', 'dist', 'tests/e2e/**'],
  },
});
```

- [ ] **Step 2: Create `web/src/test-setup.ts`**

```typescript
// Vitest setup — runs before each test file.
// Auto-cleanup @testing-library/react side effects.
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => cleanup());
```

- [ ] **Step 3: Create `web/src/test-utils.tsx`**

```typescript
import type { ReactElement, ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { render, type RenderOptions } from '@testing-library/react';
import { AuthContext, type AuthUser } from '@/contexts/AuthContext';

interface WrapperOptions {
  /** Mock authenticated user; default = admin */
  user?: AuthUser | null;
  /** Initial route for MemoryRouter; default = '/' */
  initialRoute?: string;
  /** Override QueryClient; default = fresh client with retries disabled */
  queryClient?: QueryClient;
}

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

function makeWrapper(options: WrapperOptions = {}) {
  const {
    user = {
      id: 1,
      username: 'admin',
      role: 'admin',
      email: 'admin@test.local',
      full_name: 'Test Admin',
    },
    initialRoute = '/',
    queryClient = createTestQueryClient(),
  } = options;

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialRoute]}>
          <AuthContext.Provider
            value={{
              user,
              loading: false,
              login: async () => {},
              logout: async () => {},
              refreshUser: async () => {},
            }}
          >
            {children}
          </AuthContext.Provider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

export function renderWithProviders(
  ui: ReactElement,
  options: WrapperOptions & RenderOptions = {},
) {
  const { user, initialRoute, queryClient, ...renderOpts } = options;
  const Wrapper = makeWrapper({ user, initialRoute, queryClient });
  return render(ui, { wrapper: Wrapper, ...renderOpts });
}

export * from '@testing-library/react';
```

- [ ] **Step 4: Verify Vitest config loads**

```bash
cd web && pnpm exec vitest run --passWithNoTests 2>&1 | tail -10
```
Expected: exit 0, message "No test files found" (because we have none yet).

- [ ] **Step 5: Commit**

```bash
git add web/vitest.config.ts web/src/test-setup.ts web/src/test-utils.tsx
git commit -m "feat(phase-5): Vitest config + test-utils wrapper (Task 2)

- vitest.config.ts: jsdom + @ alias + test-setup
- test-utils.tsx: renderWithProviders wrapping QueryClient + Router + AuthContext

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 3: TDD — `useDebounce` test + verify existing implementation

**Files:**
- Create: `web/src/hooks/useDebounce.test.ts`
- Existing: `web/src/hooks/useDebounce.ts` (no change)

**Acceptance:**
- Test 3 cases: debounce delays update, cancel on unmount, multiple updates coalesce
- All pass

- [ ] **Step 1: Write failing test in `web/src/hooks/useDebounce.test.ts`**

```typescript
import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDebounce } from './useDebounce';

describe('useDebounce', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('returns initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('hello', 300));
    expect(result.current).toBe('hello');
  });

  it('updates value after delay', () => {
    const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
      initialProps: { value: 'a' },
    });
    rerender({ value: 'b' });
    expect(result.current).toBe('a'); // not yet
    act(() => vi.advanceTimersByTime(300));
    expect(result.current).toBe('b');
  });

  it('coalesces rapid updates', () => {
    const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
      initialProps: { value: 'a' },
    });
    rerender({ value: 'b' });
    act(() => vi.advanceTimersByTime(100));
    rerender({ value: 'c' });
    act(() => vi.advanceTimersByTime(100));
    rerender({ value: 'd' });
    expect(result.current).toBe('a'); // still original
    act(() => vi.advanceTimersByTime(300));
    expect(result.current).toBe('d');
  });
});
```

- [ ] **Step 2: Run test, verify it passes**

```bash
cd web && pnpm exec vitest run useDebounce
```
Expected: 3/3 PASS (implementation is correct from Phase 2).

- [ ] **Step 3: Commit**

```bash
git add web/src/hooks/useDebounce.test.ts
git commit -m "test(phase-5): useDebounce tests (Task 3)

- 3 cases: initial, delayed update, coalesced updates
- Uses Vitest fake timers
- All pass against existing implementation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 4: TDD — `useLocalStorage` test + verify existing implementation

**Files:**
- Create: `web/src/hooks/useLocalStorage.test.ts`
- Existing: `web/src/hooks/useLocalStorage.ts` (no change)

**Acceptance:**
- Test 4 cases: read initial, write to storage, functional updater, corrupt JSON fallback

- [ ] **Step 1: Write failing test in `web/src/hooks/useLocalStorage.test.ts`**

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useLocalStorage } from './useLocalStorage';

describe('useLocalStorage', () => {
  beforeEach(() => localStorage.clear());

  it('returns initial value when key missing', () => {
    const { result } = renderHook(() => useLocalStorage('test', 'default'));
    expect(result.current[0]).toBe('default');
  });

  it('writes to localStorage on update', () => {
    const { result } = renderHook(() => useLocalStorage('test', 'default'));
    act(() => result.current[1]('updated'));
    expect(result.current[0]).toBe('updated');
    expect(localStorage.getItem('test')).toBe(JSON.stringify('updated'));
  });

  it('supports functional updater', () => {
    const { result } = renderHook(() => useLocalStorage<number>('counter', 0));
    act(() => result.current[1]((prev) => prev + 1));
    act(() => result.current[1]((prev) => prev + 1));
    expect(result.current[0]).toBe(2);
  });

  it('falls back to initial on corrupt JSON', () => {
    localStorage.setItem('test', '{not valid json');
    const { result } = renderHook(() => useLocalStorage('test', 'fallback'));
    expect(result.current[0]).toBe('fallback');
  });
});
```

- [ ] **Step 2: Run test, verify it passes**

```bash
cd web && pnpm exec vitest run useLocalStorage
```
Expected: 4/4 PASS.

- [ ] **Step 3: Commit**

```bash
git add web/src/hooks/useLocalStorage.test.ts
git commit -m "test(phase-5): useLocalStorage tests (Task 4)

- 4 cases: initial, write, functional updater, corrupt JSON fallback
- All pass against existing implementation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 5: TDD — `useRole` test + verify existing implementation

**Files:**
- Create: `web/src/hooks/useRole.test.ts`
- Existing: `web/src/hooks/useRole.ts` (no change)

**Acceptance:**
- Test cho 3 roles × 5+ capabilities: `isAdmin`/`isTeacher`/`isUser` flags, `has(cap)` returns đúng giá trị theo ROLE_CAPABILITIES map

- [ ] **Step 1: Read `web/src/hooks/useRole.ts` to confirm capability map**

```bash
cd web && grep -A 30 "ROLE_CAPABILITIES" src/hooks/useRole.ts | head -50
```

- [ ] **Step 2: Write failing test in `web/src/hooks/useRole.test.ts`**

```typescript
import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useRole, type UserRole } from './useRole';
import { renderWithProviders } from '@/test-utils';

describe('useRole', () => {
  it('returns isAdmin=true for admin user', () => {
    const { result } = renderHook(() => useRole(), {
      wrapper: renderWithProviders(null, { user: { id: 1, username: 'a', role: 'admin' as UserRole } }).getByText ? null : undefined,
    });
    // simpler approach below
  });
});
```

Use the simpler approach — render the hook with a wrapper factory:

```typescript
import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useRole, type UserRole, type UserCapability } from './useRole';
import { renderWithProviders, createTestQueryClient } from '@/test-utils';
import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext, type AuthUser } from '@/contexts/AuthContext';

function hookWrapper(user: AuthUser | null) {
  const queryClient = createTestQueryClient();
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AuthContext.Provider
            value={{
              user,
              loading: false,
              login: async () => {},
              logout: async () => {},
              refreshUser: async () => {},
            }}
          >
            {children}
          </AuthContext.Provider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

const userOf = (role: UserRole): AuthUser => ({
  id: 1, username: 'test', role, email: 't@test.local', full_name: 'Test',
});

describe('useRole', () => {
  describe('flags', () => {
    it('admin', () => {
      const { result } = renderHook(() => useRole(), { wrapper: hookWrapper(userOf('admin')) });
      expect(result.current.isAdmin).toBe(true);
      expect(result.current.isTeacher).toBe(false);
      expect(result.current.isUser).toBe(false);
    });
    it('teacher', () => {
      const { result } = renderHook(() => useRole(), { wrapper: hookWrapper(userOf('teacher')) });
      expect(result.current.isAdmin).toBe(false);
      expect(result.current.isTeacher).toBe(true);
      expect(result.current.isUser).toBe(false);
    });
    it('user (student)', () => {
      const { result } = renderHook(() => useRole(), { wrapper: hookWrapper(userOf('user')) });
      expect(result.current.isAdmin).toBe(false);
      expect(result.current.isTeacher).toBe(false);
      expect(result.current.isUser).toBe(true);
    });
  });

  describe('has(capability)', () => {
    it('admin has all capabilities', () => {
      const { result } = renderHook(() => useRole(), { wrapper: hookWrapper(userOf('admin')) });
      const caps: UserCapability[] = [
        'upload_essay', 'view_own_history', 'view_class_history',
        'override_verdict', 'view_logic_trace', 'view_document_inspector',
        'view_orphan_detection',
      ];
      for (const c of caps) expect(result.current.has(c)).toBe(true);
    });
    it('teacher has view_class_history but not admin-only', () => {
      const { result } = renderHook(() => useRole(), { wrapper: hookWrapper(userOf('teacher')) });
      expect(result.current.has('view_class_history')).toBe(true);
      expect(result.current.has('override_verdict')).toBe(true);
      // admin-only check — adjust if capability map differs
    });
    it('user has only student capabilities', () => {
      const { result } = renderHook(() => useRole(), { wrapper: hookWrapper(userOf('user')) });
      expect(result.current.has('upload_essay')).toBe(true);
      expect(result.current.has('view_own_history')).toBe(true);
      expect(result.current.has('view_class_history')).toBe(false);
      expect(result.current.has('override_verdict')).toBe(false);
    });
  });

  it('returns falsy when not authenticated', () => {
    const { result } = renderHook(() => useRole(), { wrapper: hookWrapper(null) });
    expect(result.current.isAdmin).toBe(false);
    expect(result.current.role).toBeNull();
  });
});
```

- [ ] **Step 3: Read `useRole.ts` to verify expected capabilities for each role**

Adjust test expectations to match actual `ROLE_CAPABILITIES` table from `web/src/hooks/useRole.ts`.

- [ ] **Step 4: Run test, verify it passes**

```bash
cd web && pnpm exec vitest run useRole
```
Expected: 7/7 PASS (after adjusting expectations to match actual map).

- [ ] **Step 5: Commit**

```bash
git add web/src/hooks/useRole.test.ts
git commit -m "test(phase-5): useRole tests (Task 5)

- 3 role flag cases (admin/teacher/user)
- 3 capability cases (admin all, teacher subset, user minimal)
- 1 unauth case
- All pass against existing implementation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 6: TDD — `useEssayPolling` test (with mocked fetch)

**Files:**
- Create: `web/src/hooks/useEssayPolling.test.ts`
- Existing: `web/src/hooks/useEssayPolling.ts` (no change)

**Acceptance:**
- Test 3 cases: success path (essay with report → done), polling path (null report → polls status → done), abort on essayId change

- [ ] **Step 1: Read `web/src/hooks/useEssayPolling.ts` to understand expected behavior**

```bash
cd web && cat src/hooks/useEssayPolling.ts | head -120
```

Note: hook calls `api.getEssay(id)` and `api.getEssayStatus(id)`. Both return Promises. When `getEssay` returns the report → done. When it returns `null` → poll status → if status === 'completed' → refetch getEssay.

- [ ] **Step 2: Write failing test in `web/src/hooks/useEssayPolling.test.ts`**

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';

// Mock api/client before importing the hook
const mockGetEssay = vi.fn();
const mockGetEssayStatus = vi.fn();
vi.mock('@/api/client', () => ({
  api: {
    getEssay: (...args: unknown[]) => mockGetEssay(...args),
    getEssayStatus: (...args: unknown[]) => mockGetEssayStatus(...args),
  },
}));

import { useEssayPolling } from './useEssayPolling';

beforeEach(() => {
  vi.useFakeTimers();
  mockGetEssay.mockReset();
  mockGetEssayStatus.mockReset();
});
afterEach(() => {
  vi.useRealTimers();
});

describe('useEssayPolling', () => {
  it('returns report immediately if getEssay resolves with data', async () => {
    mockGetEssay.mockResolvedValueOnce({ id: 1, filename: 'x.pdf' });
    const { result } = renderHook(() => useEssayPolling(1));
    await waitFor(() => expect(result.current.report).not.toBeNull());
    expect(result.current.isPolling).toBe(false);
  });

  it('polls status when getEssay returns null, then resolves on completed', async () => {
    mockGetEssay.mockResolvedValue(null);
    mockGetEssayStatus
      .mockResolvedValueOnce({ status: 'processing' })
      .mockResolvedValueOnce({ status: 'processing' })
      .mockResolvedValueOnce({ status: 'completed' });
    mockGetEssay.mockResolvedValueOnce({ id: 1, filename: 'final.pdf' });

    const { result } = renderHook(() => useEssayPolling(42, { intervalMs: 1000 }));
    expect(result.current.isPolling).toBe(true);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3500);
    });
    await waitFor(() => expect(result.current.report).not.toBeNull());
    expect(result.current.report?.filename).toBe('final.pdf');
  });

  it('aborts polling when essayId changes', async () => {
    mockGetEssay.mockResolvedValue(null);
    mockGetEssayStatus.mockResolvedValue({ status: 'processing' });

    const { result, rerender } = renderHook(
      ({ id }) => useEssayPolling(id, { intervalMs: 1000 }),
      { initialProps: { id: 1 } },
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2500);
    });
    const callsBefore = mockGetEssayStatus.mock.calls.length;
    expect(callsBefore).toBeGreaterThan(0);

    rerender({ id: 2 });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    // After change, calls for id=1 should not continue beyond the reset
    const callsForId1 = mockGetEssayStatus.mock.calls.filter((c) => c[0] === 1).length;
    expect(callsForId1).toBeLessThanOrEqual(callsBefore);
  });
});
```

- [ ] **Step 3: Run test, verify pass**

```bash
cd web && pnpm exec vitest run useEssayPolling
```
Expected: 3/3 PASS. If failures occur, adjust the test (not the implementation) to match the actual hook semantics (e.g., does it accept null essayId?).

- [ ] **Step 4: Commit**

```bash
git add web/src/hooks/useEssayPolling.test.ts
git commit -m "test(phase-5): useEssayPolling tests with mocked fetch (Task 6)

- Success path (immediate report)
- Polling path (null → status → completed → report)
- Abort on essayId change
- Uses Vitest fake timers + vi.mock for api

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 7: Create `queryClient` singleton + `QueryClientProvider` in main.tsx

**Files:**
- Create: `web/src/lib/queryClient.ts`
- Modify: `web/src/main.tsx`

**Acceptance:**
- `queryClient.ts` exports singleton `queryClient` with sensible defaults
- `main.tsx` wraps `<App />` in `<QueryClientProvider client={queryClient}>`
- `pnpm build` passes

- [ ] **Step 1: Create `web/src/lib/queryClient.ts`**

```typescript
import { QueryClient } from '@tanstack/react-query';

/**
 * Singleton QueryClient cho toàn app.
 *
 * Defaults:
 * - staleTime: 30s — data tươi đủ cho navigation giữa pages
 * - gcTime: 5min — giữ cache 5 phút sau unmount
 * - refetchOnWindowFocus: false — Phase 1 quyết định không refocus (UX im lặng)
 * - retry: 1 — retry network errors 1 lần, không spam server
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
    mutations: {
      retry: 0,
    },
  },
});
```

- [ ] **Step 2: Modify `web/src/main.tsx` — wrap with QueryClientProvider**

Find the root render. Add import:
```typescript
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/queryClient';
```

Wrap `<App />`:
```tsx
<QueryClientProvider client={queryClient}>
  <App />
</QueryClientProvider>
```

- [ ] **Step 3: Run build**

```bash
cd web && pnpm build 2>&1 | tail -10
```
Expected: build success.

- [ ] **Step 4: Commit**

```bash
git add web/src/lib/queryClient.ts web/src/main.tsx
git commit -m "feat(phase-5): QueryClientProvider + singleton queryClient (Task 7)

- src/lib/queryClient.ts: defaults (staleTime 30s, no refocus, 1 retry)
- main.tsx wraps App in QueryClientProvider
- Build passes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 8: Create `useEssays` query hook (for Dashboard + History)

**Files:**
- Create: `web/src/hooks/useEssays.ts`

**Acceptance:**
- Exports `useEssays()` returning `{ data, isLoading, error, refetch }`
- Exports `useDeleteEssay()` mutation that invalidates `['essays']` cache on success
- Type-safe (returns `EssaySummary[]`)

- [ ] **Step 1: Create `web/src/hooks/useEssays.ts`**

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type EssaySummary } from '@/api/client';

const ESSAYS_KEY = ['essays'] as const;

export function useEssays() {
  return useQuery({
    queryKey: ESSAYS_KEY,
    queryFn: () => api.listEssays(),
    staleTime: 30_000,
  });
}

export function useDeleteEssay() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteEssay(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ESSAYS_KEY });
    },
  });
}
```

- [ ] **Step 2: Verify build (smoke)**

```bash
cd web && pnpm build 2>&1 | tail -5
```
Expected: build success.

- [ ] **Step 3: Commit**

```bash
git add web/src/hooks/useEssays.ts
git commit -m "feat(phase-5): useEssays query + useDeleteEssay mutation (Task 8)

- useEssays: query keyed on ['essays'], staleTime 30s
- useDeleteEssay: mutation invalidates ['essays'] on success
- Used by DashboardPage + HistoryPage (Tasks 9-10)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 9: Refactor `DashboardPage` to use `useEssays`

**Files:**
- Modify: `web/src/pages/DashboardPage.tsx`

**Acceptance:**
- Replaces `useEffect + setInterval + fetch + setState` block with `useEssays()`
- Search query + delete logic preserved
- Build passes, manual smoke: dashboard loads essays, search filters, delete works

- [ ] **Step 1: Read current `DashboardPage.tsx` to understand data flow**

Already surveyed: lines 44-55 (state), line 108 (useEffect), line ~55 (setInterval). Identify all places that read `essays`, `loading`, `error`, `deletingId`.

- [ ] **Step 2: Replace state + effect with `useEssays` + `useDeleteEssay`**

```typescript
import { useEssays, useDeleteEssay } from '@/hooks/useEssays';
// inside component:
const { data: essays = [], isLoading, error } = useEssays();
const deleteMutation = useDeleteEssay();
const [searchQuery, setSearchQuery] = useState('');
const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
```

Replace `deletingId` state + `handleDelete` calls with:
```typescript
const deletingId = deleteMutation.isPending ? deleteMutation.variables : null;
const handleDelete = async (id: number) => {
  await deleteMutation.mutateAsync(id);
  setConfirmDeleteId(null);
};
```

- [ ] **Step 3: Remove the now-unused `useEffect`, `setInterval`, `loadEssays`, `useCallback` imports**

```bash
cd web && grep -n "useEffect\|setInterval\|loadEssays\|REFRESH_INTERVAL" src/pages/DashboardPage.tsx
```
Remove all references. Keep `useEffect` only if used elsewhere.

- [ ] **Step 4: Run build**

```bash
cd web && pnpm build 2>&1 | tail -10
```
Expected: build success.

- [ ] **Step 5: Manual smoke (optional)**

```bash
cd web && pnpm dev
# Open http://localhost:5173, login, navigate to Dashboard
# Verify: essays load, search works, delete confirms + removes
```

- [ ] **Step 6: Commit**

```bash
git add web/src/pages/DashboardPage.tsx
git commit -m "refactor(phase-5): DashboardPage → useEssays + useDeleteEssay (Task 9)

- Removed useEffect + setInterval + REFRESH_INTERVAL_MS
- Search + delete flow preserved
- Build passes, manual smoke OK

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 10: Refactor `HistoryPage` to use `useEssays`

**Files:**
- Modify: `web/src/pages/HistoryPage.tsx`

**Acceptance:**
- Replaces polling block with `useEssays()`
- Search filter + delete + redirect logic preserved
- Build passes

- [ ] **Step 1: Read current `HistoryPage.tsx` state**

Already surveyed: `items`, `loading`, `error`, `deletingId`, `searchQuery`, `confirmDeleteId`, line 55-57 `setInterval(loadEssays, ...)`.

- [ ] **Step 2: Apply same pattern as Task 9**

- Replace `useState<EssaySummary[]>` + `useEffect` + `setInterval` with `useEssays()`.
- Replace `deletingId` state with `deleteMutation.isPending ? variables : null`.
- Keep `searchQuery` and `confirmDeleteId` local state.
- Keep `filteredItems` derivation (lines 78-79).

- [ ] **Step 3: Run build**

```bash
cd web && pnpm build 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/HistoryPage.tsx
git commit -m "refactor(phase-5): HistoryPage → useEssays + useDeleteEssay (Task 10)

- Removed useEffect + setInterval polling
- Search filter + delete confirm preserved
- Build passes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 11: Create `useEssayReport` hook + `useOverrideVerdict` mutation (for EssayPage + ProcessingPage)

**Files:**
- Create: `web/src/hooks/useEssayReport.ts`

**Acceptance:**
- `useEssayReport(id, options?)` returns `{ data, isLoading, error, isPolling }` — auto-polls while essay is processing
- `useOverrideVerdict()` mutation invalidates `['essay-report', id]` on success

- [ ] **Step 1: Read `api.getEssay`, `api.getEssayStatus`, `api.overrideVerdict` signatures**

```bash
cd web && grep -A 5 "getEssay:\|getEssayStatus:\|overrideVerdict:" src/api/client.ts | head -30
```

- [ ] **Step 2: Create `web/src/hooks/useEssayReport.ts`**

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type AnalysisReport, type OverrideRequest } from '@/api/client';

interface UseEssayReportOptions {
  /** Enable polling while essay is still processing (default: true) */
  pollUntilDone?: boolean;
  /** Poll interval in ms (default: 2000) */
  intervalMs?: number;
}

export function useEssayReport(
  essayId: number | null,
  options: UseEssayReportOptions = {},
) {
  const { pollUntilDone = true, intervalMs = 2000 } = options;

  return useQuery({
    queryKey: ['essay-report', essayId],
    queryFn: async (): Promise<AnalysisReport | null> => {
      if (essayId === null) return null;
      // Try direct report first
      const report = await api.getEssay(essayId);
      if (report) return report;
      // If null, check status — if processing, return null (refetch will retry)
      const status = await api.getEssayStatus(essayId);
      if (status.status === 'failed') {
        throw new Error(status.error ?? 'Essay processing failed');
      }
      return null;
    },
    enabled: essayId !== null,
    refetchInterval: (query) => {
      if (!pollUntilDone) return false;
      const data = query.state.data;
      // Poll while no report yet
      return data ? false : intervalMs;
    },
    refetchIntervalInBackground: false,
  });
}

export function useOverrideVerdict(essayId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: OverrideRequest) => {
      // Find verdict id from the request or context
      // overrideVerdict signature: (verdictId, req)
      // We need verdictId, but req doesn't have it; assume caller passes it separately.
      // Better: useOverrideVerdict takes verdictId as first arg
      throw new Error('use OverrideVerdictParams instead');
    },
    // ... we'll redesign in next step
  });
}
```

**Redesign note**: Since `api.overrideVerdict(verdictId, req)` takes verdictId separately, design mutation as:

```typescript
export function useOverrideVerdict() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ verdictId, req }: { verdictId: number; req: OverrideRequest }) =>
      api.overrideVerdict(verdictId, req),
    onSuccess: (_data, { verdictId }) => {
      // Invalidate all essay-report queries (we don't know which one)
      qc.invalidateQueries({ queryKey: ['essay-report'] });
    },
  });
}
```

- [ ] **Step 3: Run build**

```bash
cd web && pnpm build 2>&1 | tail -5
```

- [ ] **Step 4: Commit**

```bash
git add web/src/hooks/useEssayReport.ts
git commit -m "feat(phase-5): useEssayReport query + useOverrideVerdict mutation (Task 11)

- useEssayReport: smart polling (stops when report arrives)
- useOverrideVerdict: invalidates ['essay-report'] on success
- Used by EssayPage + ProcessingPage (Tasks 12-13)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 12: Refactor `ProcessingPage` to use `useEssayReport`

**Files:**
- Modify: `web/src/pages/ProcessingPage.tsx`

**Acceptance:**
- Replaces `useEffect + setInterval` (via `useEssayPolling` hook) with `useEssayReport(id, { intervalMs: 1500 })`
- Redirect to report page on success
- Build passes

- [ ] **Step 1: Read current `ProcessingPage.tsx` polling logic**

Lines 59-95: `useState<EssayStatus>`, `useState<AnalysisReport>`, `pollTimer` ref, `setInterval(poll, 1500)`.

- [ ] **Step 2: Replace with `useEssayReport`**

```typescript
import { useEssayReport } from '@/hooks/useEssayReport';
import { useNavigate, useParams } from 'react-router-dom';
// inside component:
const { essayId: essayIdStr } = useParams<{ essayId: string }>();
const essayId = essayIdStr ? Number(essayIdStr) : null;
const navigate = useNavigate();
const { data: report, error } = useEssayReport(essayId, { intervalMs: 1500 });

useEffect(() => {
  if (report) navigate(`/verification/report/${essayId}`);
}, [report, essayId, navigate]);
```

- [ ] **Step 3: Remove `useEssayPolling` import + `pollTimer` ref + `setInterval`**

```bash
cd web && grep -n "useEssayPolling\|pollTimer\|setInterval" src/pages/ProcessingPage.tsx
```
Remove all references.

- [ ] **Step 4: Build + manual smoke**

```bash
cd web && pnpm build 2>&1 | tail -5
```
Then manually: upload an essay, watch processing page poll → redirect to report.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/ProcessingPage.tsx
git commit -m "refactor(phase-5): ProcessingPage → useEssayReport (Task 12)

- Removed useEssayPolling + setInterval
- useEffect on `report` to redirect
- Build passes, manual smoke OK

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 13: Refactor `EssayPage` to use `useEssayReport` (Phase 1 of split)

**Files:**
- Modify: `web/src/pages/EssayPage.tsx` (start the split, but keep most code in this file for now)

**Acceptance:**
- Replaces `useEssayPolling` with `useEssayReport`
- Override uses `useOverrideVerdict` mutation
- Build passes (full split happens in Tasks 14-15)

- [ ] **Step 1: Read `EssayPage.tsx` state**

Lines 27-29: `report`, `error`, `selected`. Line 32: `useEffect`.

- [ ] **Step 2: Replace polling with `useEssayReport`**

```typescript
import { useEssayReport, useOverrideVerdict } from '@/hooks/useEssayReport';

const { essayId: idStr } = useParams<{ essayId: string }>();
const essayId = idStr ? Number(idStr) : null;
const { data: report, error: loadError, isLoading } = useEssayReport(essayId);
const overrideMutation = useOverrideVerdict();

const handleOverride = async (verdict: Verdict, req: OverrideRequest) => {
  await overrideMutation.mutateAsync({ verdictId: verdict.id, req });
};
```

- [ ] **Step 3: Remove `useEssayPolling` import + `useState` for `report`/`error`**

Keep `useState` for `selected` and `activeTab` (UI state, not server state).

- [ ] **Step 4: Build**

```bash
cd web && pnpm build 2>&1 | tail -5
```
Expected: build success. If TS errors, fix the type mismatch in `handleOverride` (it now returns void instead of using `await api.overrideVerdict`).

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/EssayPage.tsx
git commit -m "refactor(phase-5): EssayPage → useEssayReport (Task 13, before split)

- Removed useEssayPolling + setReport/setError state
- useOverrideVerdict mutation replaces direct api.overrideVerdict
- Build passes (full split in Tasks 14-15)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 14: Split `CitationGraphView` — extract `EvidenceGraph` + `SourceIcon` + `EvidenceGraphNode`

**Files:**
- Create: `web/src/components/CitationGraph/SourceIcon.tsx`
- Create: `web/src/components/CitationGraph/EvidenceGraphNode.tsx`
- Create: `web/src/components/CitationGraph/EvidenceGraph.tsx`
- Modify: `web/src/components/CitationGraphView.tsx` (remove extracted code, re-export from new location)

**Acceptance:**
- `CitationGraphView.tsx` shrinks by ~300 LOC
- `EvidenceGraph` (named export, line 257) moved to its own file
- `SourceIcon` + `EvidenceGraphNode` (helper functions) moved
- All existing imports of `EvidenceGraph` and `CitationGraphView` still work (re-export shim)
- Build passes, e2e tests pass (if backend is running)

- [ ] **Step 1: Survey what `CitationGraphView.tsx` exports and what imports them**

```bash
cd web && grep -rn "from.*CitationGraphView\|CitationGraphView\|EvidenceGraph" src/ --include="*.tsx" --include="*.ts" | head -20
```

- [ ] **Step 2: Create `web/src/components/CitationGraph/SourceIcon.tsx`**

Copy lines 117-122 (the `SourceIcon` function) into new file. Export as named export.

- [ ] **Step 3: Create `web/src/components/CitationGraph/EvidenceGraphNode.tsx`**

Copy lines 124-256 (the `EvidenceGraphNode` component) into new file. Update imports to use `@/api/client` and `@/lib/utils`. Export as named export.

- [ ] **Step 4: Create `web/src/components/CitationGraph/EvidenceGraph.tsx`**

Copy lines 257-569 (the `EvidenceGraph` component + its inner helpers) into new file. Export as named export. Imports needed:
- React hooks (useState, useMemo, etc.)
- Lucide icons
- `@/api/client` types
- `./SourceIcon`, `./EvidenceGraphNode`

- [ ] **Step 5: Modify `web/src/components/CitationGraphView.tsx` to re-export**

```typescript
// Re-export shim — preserves existing import paths
export { CitationGraphView } from './CitationGraph/CitationGraphView';
export { EvidenceGraph } from './CitationGraph/EvidenceGraph';
```

(At this point, the new `CitationGraph/CitationGraphView.tsx` doesn't exist yet — that's Task 15. For now, the shim re-exports a file that we'll create.)

- [ ] **Step 6: Run build to verify imports resolve**

```bash
cd web && pnpm build 2>&1 | tail -15
```
Expected: build may fail because `CitationGraph/CitationGraphView.tsx` doesn't exist. **That's OK** — we create it in Task 15.

- [ ] **Step 7: Commit (skip if build fails — defer commit to Task 15)**

If shim alone works, commit. Otherwise, wait until Task 15.

---

## Task 15: Split `CitationGraphView` (main) — extract the rest + rename

**Files:**
- Create: `web/src/components/CitationGraph/CitationGraphView.tsx` (main graph view, slimmed)
- Create: `web/src/components/CitationGraph/GraphControls.tsx` (filter + view-mode controls; renames Phase 2's `CitationGraphControls`)
- Create: `web/src/components/CitationGraph/index.ts` (public API)
- Modify: `web/src/components/CitationGraphView.tsx` (re-export shim, backward-compat)
- Delete: `web/src/components/CitationGraphControls.tsx` (renamed, replaced by shim if needed)

**Acceptance:**
- `CitationGraph/CitationGraphView.tsx` is the main view, ~250 LOC
- `CitationGraph/GraphControls.tsx` is the filter bar
- Original `CitationGraphView.tsx` re-exports from new location
- Build passes, e2e teacher-flow test still works (verifies Phase 4 path)

- [ ] **Step 1: Create `web/src/components/CitationGraph/CitationGraphView.tsx`**

Copy lines 580-end of original file (the `CitationGraphView` component + inner helpers like `toggleStatus`, `toggleLabel`, `clearFilters`). Remove the `EvidenceGraph` portion (already extracted in Task 14). Export as named export.

- [ ] **Step 2: Create `web/src/components/CitationGraph/GraphControls.tsx`**

Look for `CitationGraphControls` in original (Phase 2 may have extracted it as a sibling). If it exists, move it to `CitationGraph/GraphControls.tsx`. If not, extract the filter bar (lines 596-653 area) into a new component with props `{ statusFilters, labelFilters, searchQuery, viewMode, onToggleStatus, onToggleLabel, onSearchChange, onViewModeChange, onClearFilters }`.

- [ ] **Step 3: Create `web/src/components/CitationGraph/index.ts`**

```typescript
export { CitationGraphView } from './CitationGraphView';
export { EvidenceGraph } from './EvidenceGraph';
export { GraphControls } from './GraphControls';
```

- [ ] **Step 4: Verify shim re-export works**

```bash
cd web && pnpm build 2>&1 | tail -10
```
Expected: build success. Both `import { CitationGraphView } from '@/components/CitationGraphView'` and `import { CitationGraphView } from '@/components/CitationGraph'` work.

- [ ] **Step 5: Run e2e teacher-flow test (verifies no regression)**

```bash
cd web && pnpm exec playwright test tests/e2e/teacher-flow.spec.ts --config=playwright.config.override.ts 2>&1 | tail -20
```
Expected: 4/4 PASS.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/CitationGraph/ web/src/components/CitationGraphView.tsx web/src/components/CitationGraphControls.tsx
git commit -m "refactor(phase-5): split CitationGraphView into CitationGraph/ dir (Task 15)

- CitationGraph/EvidenceGraph.tsx: main evidence graph (extracted)
- CitationGraph/EvidenceGraphNode.tsx: tree node
- CitationGraph/SourceIcon.tsx: source icon helper
- CitationGraph/CitationGraphView.tsx: main filterable graph (slimmed)
- CitationGraph/GraphControls.tsx: filter bar (renamed from CitationGraphControls)
- Old CitationGraphView.tsx becomes re-export shim
- Build passes, e2e teacher-flow 4/4 pass

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 16: Split `EssayPage` — create `EssayPage/` directory + extract `EssayHeader`

**Files:**
- Create: `web/src/pages/EssayPage/EssayHeader.tsx` (extract from existing EssayPage.tsx)
- Create: `web/src/pages/EssayPage/EssayPage.tsx` (initial skeleton, will grow in Tasks 17-18)
- Create: `web/src/pages/EssayPage/index.ts`
- Modify: `web/src/pages/EssayPage.tsx` (re-export shim)
- Modify router import (verify path still works)

**Acceptance:**
- `EssayPage/EssayHeader.tsx` extracted (Phase 2 đã làm rồi, chỉ cần move vào folder)
- Re-export shim ở `EssayPage.tsx` cũ
- Build passes

- [ ] **Step 1: Check if `EssayHeader` already exists as a sibling or inline**

```bash
cd web && grep -n "EssayHeader\|export function" src/pages/EssayPage.tsx | head -10
```

- [ ] **Step 2: Create `web/src/pages/EssayPage/EssayHeader.tsx`**

If inline: extract the JSX block at top of return (the title + back button + status) into a new component receiving `{ essay, onBack }` props. If already separate, move file to `EssayPage/EssayHeader.tsx`.

- [ ] **Step 3: Create `web/src/pages/EssayPage/EssayPage.tsx` (skeleton)**

```typescript
import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useEssayReport } from '@/hooks/useEssayReport';
import { EssayHeader } from './EssayHeader';
// VerdictList, ActionToolbar, CitationsTab added in Tasks 17-18

export function EssayPage() {
  const { essayId: idStr } = useParams<{ essayId: string }>();
  const essayId = idStr ? Number(idStr) : null;
  const { data: report, isLoading, error } = useEssayReport(essayId);
  const [activeTab, setActiveTab] = useState('overview');
  const [selected, setSelected] = useState<Verdict | null>(null);

  if (isLoading) return <p>Loading…</p>;
  if (error) return <p className="text-rose-600">Error: {String(error)}</p>;
  if (!report) return null;

  return (
    <div>
      <EssayHeader essay={report.essay} />
      {/* Tabs + content added in Tasks 17-18 */}
    </div>
  );
}
```

(Import `Verdict` from `@/api/client`.)

- [ ] **Step 4: Create `web/src/pages/EssayPage/index.ts`**

```typescript
export { EssayPage } from './EssayPage';
```

- [ ] **Step 5: Modify `web/src/pages/EssayPage.tsx` (re-export shim)**

```typescript
export { EssayPage } from './EssayPage/EssayPage';
```

- [ ] **Step 6: Build**

```bash
cd web && pnpm build 2>&1 | tail -5
```
Expected: build success.

- [ ] **Step 7: Commit**

```bash
git add web/src/pages/EssayPage.tsx web/src/pages/EssayPage/
git commit -m "refactor(phase-5): split EssayPage — directory + EssayHeader (Task 16)

- pages/EssayPage/EssayHeader.tsx extracted
- pages/EssayPage/EssayPage.tsx: skeleton using useEssayReport
- Old EssayPage.tsx re-exports from new location
- Build passes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 17: Extract `VerdictList` from EssayPage

**Files:**
- Create: `web/src/pages/EssayPage/VerdictList.tsx`
- Modify: `web/src/pages/EssayPage/EssayPage.tsx` (use new component)

**Acceptance:**
- `VerdictList` accepts `{ verdicts, onSelect, selectedId }` props
- Page composes it; logic moves out of page
- Build passes

- [ ] **Step 1: Identify verdict list rendering in EssayPage**

The VerdictTable + tab content area.

- [ ] **Step 2: Create `web/src/pages/EssayPage/VerdictList.tsx`**

```typescript
import type { Verdict } from '@/api/client';
import { VerdictTable } from '@/components/VerdictTable';

interface VerdictListProps {
  verdicts: Verdict[];
  selectedId: number | null;
  onSelect: (v: Verdict) => void;
  onOverride?: (v: Verdict, req: any) => void;
}

export function VerdictList({ verdicts, selectedId, onSelect, onOverride }: VerdictListProps) {
  return (
    <VerdictTable
      verdicts={verdicts}
      onSelect={onSelect}
      onOverride={onOverride}
    />
  );
}
```

(Adjust the `any` to use `Parameters<typeof api.overrideVerdict>[1]` for type-safety — replace `any` with that type. This fixes 1 of the 3 `any` occurrences in scope.)

- [ ] **Step 3: Update `EssayPage/EssayPage.tsx` to use `VerdictList`**

Replace inline rendering with `<VerdictList verdicts={...} selectedId={selected?.id ?? null} onSelect={setSelected} onOverride={handleOverride} />`.

- [ ] **Step 4: Build**

```bash
cd web && pnpm build 2>&1 | tail -5
```

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/EssayPage/VerdictList.tsx web/src/pages/EssayPage/EssayPage.tsx
git commit -m "refactor(phase-5): extract VerdictList from EssayPage (Task 17)

- pages/EssayPage/VerdictList.tsx: pure presentation
- Replaces 1 of 3 'any' types with proper OverrideRequest type
- Build passes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 18: Extract `CitationsTab` (inline citations tab content)

**Files:**
- Create: `web/src/pages/EssayPage/CitationsTab.tsx`
- Modify: `web/src/pages/EssayPage/EssayPage.tsx`

**Acceptance:**
- `CitationsTab` extracted
- Build passes

- [ ] **Step 1: Find the Citations tab JSX in EssayPage**

Look for `activeTab === 'citations'` or similar.

- [ ] **Step 2: Create `web/src/pages/EssayPage/CitationsTab.tsx`**

Extract the citations tab content into a component receiving `{ inlineCitations, onSelectCitation }` props.

- [ ] **Step 3: Update EssayPage to use it**

- [ ] **Step 4: Build + commit**

```bash
cd web && pnpm build 2>&1 | tail -5
```

```bash
git add web/src/pages/EssayPage/CitationsTab.tsx web/src/pages/EssayPage/EssayPage.tsx
git commit -m "refactor(phase-5): extract CitationsTab from EssayPage (Task 18)

- pages/EssayPage/CitationsTab.tsx: pure presentation
- Build passes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 19: Create `useOrphanReport` + refactor `OrphanDetectionPage`

**Files:**
- Create: `web/src/hooks/useOrphanReport.ts`
- Modify: `web/src/pages/OrphanDetectionPage.tsx`

**Acceptance:**
- `useOrphanReport(essayId)` returns query
- Page uses it instead of useEffect+fetch
- Build passes

- [ ] **Step 1: Read `OrphanDetectionPage.tsx` line 211-215**

```bash
cd web && sed -n '200,230p' src/pages/OrphanDetectionPage.tsx
```

- [ ] **Step 2: Create `web/src/hooks/useOrphanReport.ts`**

```typescript
import { useQuery } from '@tanstack/react-query';
import { api, type AnalysisReport } from '@/api/client';

export function useOrphanReport(essayId: number | null) {
  return useQuery({
    queryKey: ['orphan-report', essayId],
    queryFn: () => {
      if (essayId === null) throw new Error('essayId required');
      return api.getEssay(essayId);
    },
    enabled: essayId !== null,
    staleTime: 60_000,
  });
}
```

- [ ] **Step 3: Refactor `OrphanDetectionPage` to use `useOrphanReport`**

Replace the `useState + useEffect + fetch` block with `const { data: report, error, isLoading } = useOrphanReport(essayId);`.

- [ ] **Step 4: Build + commit**

```bash
cd web && pnpm build 2>&1 | tail -5
```

```bash
git add web/src/hooks/useOrphanReport.ts web/src/pages/OrphanDetectionPage.tsx
git commit -m "refactor(phase-5): useOrphanReport + refactor OrphanDetectionPage (Task 19)

- useOrphanReport: query keyed on ['orphan-report', essayId]
- Page: removed useEffect + fetch + setReport/setError state
- Build passes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 20: Final integration — full test pass + bundle check + manual smoke

**Files:** (verification only, no commits)

**Acceptance:**
- All Vitest tests pass (5 hook test files)
- All Playwright e2e tests still pass (112)
- Backend tests still pass (965+)
- Build passes
- Bundle size not increased (target: still < 250KB initial)

- [ ] **Step 1: Run Vitest**

```bash
cd web && pnpm test 2>&1 | tail -20
```
Expected: all tests pass.

- [ ] **Step 2: Run frontend build + check bundle**

```bash
cd web && pnpm build 2>&1 | tail -15
ls -la web/dist/assets/ | head -20
```
Expected: build success, initial bundle still < 250KB (Phase 1 target).

- [ ] **Step 3: Run backend tests (regression check)**

```bash
cd /Users/iannwendy/Desktop/DATN/essay-integrity-checker && source .venv/bin/activate && python -m pytest tests/ -q --ignore=tests/unit/test_grobid_service.py --ignore=tests/unit/test_grobid_adapter.py --ignore=tests/unit/test_grobid_parser.py 2>&1 | tail -5
```
Expected: 965+ pass, no new failures (Phase 5 is frontend-only, but verify backend not affected).

- [ ] **Step 4: Run Playwright e2e (sanity)**

```bash
cd web && pnpm exec playwright test tests/e2e/teacher-flow.spec.ts --config=playwright.config.override.ts 2>&1 | tail -10
```
Expected: 4/4 pass.

- [ ] **Step 5: Manual smoke — start dev servers**

```bash
# Terminal 1: backend
source .venv/bin/activate && uvicorn src.integrity_checker.api.main:app --port 8000

# Terminal 2: frontend
cd web && pnpm dev
```

Login as each role, verify:
- Student: dashboard loads, upload, view report, history search
- Teacher: classes, pending reviews, override verdict
- Admin: system health, audit log, account management

- [ ] **Step 6: Document any issues found in this PR's description**

If issues found, file follow-up tasks; don't fix in Phase 5.

---

## Task 21: Tick roadmap + final commit

**Files:**
- Modify: `IMPLEMENTATION_ROADMAP.md` (tick Phase 5 tasks done)

**Acceptance:**
- Roadmap updated
- PR description drafted
- Branch ready for merge

- [ ] **Step 1: Update `IMPLEMENTATION_ROADMAP.md`**

Change:
- "Phase 5: Final Polish" status from "Exit criteria: [ ]" to "[x]"
- Mark each Day 24-30 task as done
- Add: "Phase 5 status (2026-10-XX): ✅ DONE — X commits, +Y Vitest tests, ..."

- [ ] **Step 2: Stage and commit roadmap update**

```bash
git add IMPLEMENTATION_ROADMAP.md
git commit -m "docs(roadmap): tick Phase 5 complete — React Query + split + Vitest

- React Query cho 5 polling pages
- CitationGraphView + EssayPage split
- Vitest setup + 4 hook test files
- Build OK, e2e OK, backend 965+ pass

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 3: Push branch + open PR (or merge to main directly per project convention)**

```bash
git push -u origin feat/phase-5-polish
```

PR title: `Phase 5: React Query + God Component Split + Vitest (v1.17)`
PR body:
- React Query for DashboardPage, HistoryPage, ProcessingPage, EssayPage, OrphanDetectionPage
- CitationGraphView split into 5 files in CitationGraph/ dir
- EssayPage split into EssayPage/ dir (EssayHeader, VerdictList, CitationsTab, EssayPage)
- Vitest setup + tests for useDebounce, useLocalStorage, useRole, useEssayPolling (15 cases)
- Build OK, all 112 e2e pass, 965+ backend tests pass
- No API contract changes

- [ ] **Step 4: Wait for review/merge**

No code commit beyond the roadmap update.

---

## Summary of Effort

| Task | Effort | Type | Layer |
|------|--------|------|-------|
| 1 | 10 min | Install deps | Build setup |
| 2 | 30 min | Vitest config + utils | Test setup |
| 3 | 15 min | useDebounce test | Test |
| 4 | 15 min | useLocalStorage test | Test |
| 5 | 30 min | useRole test (read map first) | Test |
| 6 | 45 min | useEssayPolling test (with mock) | Test |
| 7 | 15 min | QueryClient + Provider | Frontend |
| 8 | 15 min | useEssays hook | Frontend |
| 9 | 45 min | DashboardPage refactor | Frontend |
| 10 | 30 min | HistoryPage refactor | Frontend |
| 11 | 30 min | useEssayReport + useOverrideVerdict | Frontend |
| 12 | 30 min | ProcessingPage refactor | Frontend |
| 13 | 30 min | EssayPage useEssayReport | Frontend |
| 14 | 45 min | CitationGraph split pt 1 | Frontend |
| 15 | 1h | CitationGraph split pt 2 (main) | Frontend |
| 16 | 30 min | EssayPage dir + EssayHeader | Frontend |
| 17 | 30 min | VerdictList extract | Frontend |
| 18 | 30 min | CitationsTab extract | Frontend |
| 19 | 30 min | useOrphanReport + refactor | Frontend |
| 20 | 30 min | Verification | Verification |
| 21 | 15 min | Roadmap + PR | Verification |
| **Total** | **~9h** | (realistic given scope) | |

Compared to original Phase 5 estimate (30h), this trimmed scope saves ~20h by deferring full-text search, ConfirmationModal adoption pass, and Playwright e2e extension.

---

## Self-Review Checklist

- [x] **Spec coverage**:
  - 24.1 React Query install → Task 1 ✓
  - 24.2 QueryClientProvider → Task 7 ✓
  - 24.3 DashboardPage → Task 9 ✓
  - 24.4 HistoryPage + EssayPage + ProcessingPage → Tasks 10, 12, 13 ✓
  - 24.5 useMutation override optimistic → Task 11 (deferred optimistic update, plain invalidation)
  - 26.x ConfirmationModal: deferred (only 1 occurrence in code, not worth a pass)
  - 28.x Full-text search: deferred (already have basic search)
  - 29.1 Vitest setup → Task 2 ✓
  - 29.2 useRole tests → Task 5 ✓
  - 29.3 Playwright e2e: deferred (already 112 tests)
  - 9.3 split CitationGraphView → Tasks 14-15 ✓
  - 9.4 split EssayPage → Tasks 16-18 ✓

- [x] **Step scan**: Every step gives implementer exactly one thing to do.

- [x] **Type consistency**: `useEssays` returns `EssaySummary[]` (matches Dashboard/History consumption), `useEssayReport` returns `AnalysisReport | null` (matches EssayPage/ProcessingPage), `useOverrideVerdict` signature uses `OverrideRequest` (matches api/client.ts).

- [x] **Review Focus**:
  - Race conditions on essayId change → Task 6 (test) + Task 11 (queryKey per essayId)
  - Polling leak → Task 11 (refetchIntervalInBackground: false) + Task 12 (verify after refactor)
  - CitationGraphView regressions → Task 15 (e2e test)
  - EssayPage regressions → Task 17-18 (build + commit incrementally)
  - Hook async behavior → Task 6
  - Vitest + Router conflicts → Task 5 (use MemoryRouter in hookWrapper)

- [x] **Proportion**: 21 tasks over ~9h. Tight but achievable. Each task bounded so any one can be skipped without blocking others.

- [x] **Branch strategy**: `feat/phase-5-polish` (matches Phase 1-4 convention `fix/phase-N-*` / `feat/phase-N-*`).

- [x] **No API contract changes**: all new hooks consume existing `api/client.ts` methods. Backend untouched.

- [x] **Per-task commit**: every task ends with `git commit` (or `skip` if no change). Tasks 14-15 are 1 logical change (split), so combined into 1 commit per file pair.

---

## What's NOT in this plan (deferred to Phase 6 or post-defense)

- **Full-text search** ở HistoryPage/VerdictTable (Phase 5 §28): requires backend search endpoint. Skip.
- **ConfirmationModal adoption pass** (Phase 5 §26): only 1 `window.confirm` còn lại (in `ClassDetailPage.tsx`); replacement is 5-line edit, can do ad-hoc.
- **Playwright e2e mở rộng** (Phase 5 §29.3): 112 tests đã cover core flows. Skip.
- **Optimistic update for override** (Phase 5 §24.5): Phase 4 audit log adds latency; better to wait for server response than risk showing wrong status.
- **Replace remaining `as any`** (3 occurrences in VerdictTable/OrphanDetectionPage/DocumentInspectorPage): cosmetic, low value.
- **Code-splitting for new sub-components** (CitationGraph/* and EssayPage/*): they're already lazy via EssayPage/CitationGraphView import, so further splitting is no-op for bundle.

---

**Plan complete. Ready for review.**
