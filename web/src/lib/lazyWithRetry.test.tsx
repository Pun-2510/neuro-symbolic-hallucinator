import { Suspense } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  attemptChunkReload,
  clearChunkReloadState,
  installChunkErrorHandlers,
  isChunkLoadError,
  lazyWithRetry,
} from './lazyWithRetry';

describe('lazyWithRetry & chunk error recovery', () => {
  const originalLocation = window.location;
  let reloadSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    window.sessionStorage.clear();
    reloadSpy = vi.fn();
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: {
        ...originalLocation,
        pathname: '/dashboard',
        reload: reloadSpy,
      },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    });
    vi.restoreAllMocks();
  });

  it('detects dynamic import chunk load errors across Chromium, Firefox, Safari, and Vite', () => {
    expect(
      isChunkLoadError(
        new TypeError(
          'Failed to fetch dynamically imported module: https://citra.io.vn/assets/DashboardPage-B2UYH6O7.js',
        ),
      ),
    ).toBe(true);

    expect(
      isChunkLoadError(
        new TypeError('error loading dynamically imported module: https://citra.io.vn/assets/EssayPage.js'),
      ),
    ).toBe(true);

    expect(
      isChunkLoadError(new TypeError('Importing a module script failed.')),
    ).toBe(true);

    expect(
      isChunkLoadError(new Error('Unable to preload CSS for /assets/index.css')),
    ).toBe(true);

    expect(isChunkLoadError(new Error('Regular application logic error'))).toBe(false);
    expect(isChunkLoadError(null)).toBe(false);
  });

  it('initiates a single reload per path within cooldown window to prevent infinite loops', () => {
    const t0 = 1_700_000_000_000;
    expect(attemptChunkReload(t0)).toBe(true);
    expect(reloadSpy).toHaveBeenCalledTimes(1);

    // Second attempt 2 seconds later on same path is blocked
    expect(attemptChunkReload(t0 + 2_000)).toBe(false);
    expect(reloadSpy).toHaveBeenCalledTimes(1);

    // Attempt after 16 seconds (>15s cooldown) is allowed
    expect(attemptChunkReload(t0 + 16_000)).toBe(true);
    expect(reloadSpy).toHaveBeenCalledTimes(2);

    // Clearing state resets the guard immediately
    clearChunkReloadState();
    expect(attemptChunkReload(t0 + 16_500)).toBe(true);
    expect(reloadSpy).toHaveBeenCalledTimes(3);
  });

  it('retries transient failure and renders component without reloading when retry succeeds', async () => {
    let attempts = 0;
    const LazyDummy = lazyWithRetry(
      async () => {
        attempts += 1;
        if (attempts === 1) {
          throw new TypeError(
            'Failed to fetch dynamically imported module: https://citra.io.vn/assets/DashboardPage-B2UYH6O7.js',
          );
        }
        return {
          default: () => <div data-testid="recovered-view">Recovered Dashboard</div>,
        };
      },
      1,
      10,
    );

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <LazyDummy />
      </Suspense>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('recovered-view')).toBeDefined();
    });
    expect(attempts).toBe(2);
    expect(reloadSpy).not.toHaveBeenCalled();
  });

  it('triggers window.location.reload() when chunk permanently 404s after a new deploy', async () => {
    let attempts = 0;
    const LazyStaleChunk = lazyWithRetry(
      async () => {
        attempts += 1;
        throw new TypeError(
          'Failed to fetch dynamically imported module: https://citra.io.vn/assets/DashboardPage-B2UYH6O7.js',
        );
      },
      1,
      5,
    );

    render(
      <Suspense fallback={<div data-testid="skeleton-fallback">Loading Workspace...</div>}>
        <LazyStaleChunk />
      </Suspense>,
    );

    await waitFor(() => {
      expect(reloadSpy).toHaveBeenCalledTimes(1);
    });
    expect(attempts).toBe(2);
    // Keeps Suspense skeleton visible while browser reloads so error boundary never flashes
    expect(screen.getByTestId('skeleton-fallback')).toBeDefined();
  });

  it('handles vite:preloadError events by preventing default and triggering guarded reload', () => {
    installChunkErrorHandlers();
    const event = new Event('vite:preloadError', { cancelable: true });
    window.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(reloadSpy).toHaveBeenCalledTimes(1);
  });
});
