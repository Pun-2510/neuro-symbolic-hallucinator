import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

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
    // The hook is async, give it a tick to resolve
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.report).not.toBeNull();
    expect(result.current.report?.filename).toBe('x.pdf');
    expect(result.current.isPolling).toBe(false);
  });

  it('polls status when getEssay returns null, then resolves on completed', async () => {
    // First 2 calls return null (processing), 3rd returns final report
    mockGetEssay
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ id: 42, filename: 'final.pdf' });
    mockGetEssayStatus
      .mockResolvedValueOnce({ status: 'processing' })
      .mockResolvedValueOnce({ status: 'completed' });

    const { result } = renderHook(() => useEssayPolling(42, { intervalMs: 1000 }));

    // First fetch: getEssay=null, status=processing, starts poll timer
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.isPolling).toBe(true);
    expect(result.current.report).toBeNull();

    // Second fetch (from poll timer): getEssay=null, status=completed, then getEssay=final
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(result.current.report?.filename).toBe('final.pdf');
    expect(result.current.isPolling).toBe(false);
  });

  it('aborts polling when essayId changes', async () => {
    mockGetEssay.mockResolvedValue(null);
    mockGetEssayStatus.mockResolvedValue({ status: 'processing' });

    const { rerender } = renderHook(
      ({ id }) => useEssayPolling(id, { intervalMs: 1000 }),
      { initialProps: { id: 1 } },
    );
    // First fetch
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    // Advance past one poll interval
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1100);
    });
    const callsBefore = mockGetEssayStatus.mock.calls.length;

    // Change essayId — old effect should abort
    mockGetEssay.mockReset();
    mockGetEssayStatus.mockReset();
    mockGetEssay.mockResolvedValue({ id: 2, filename: 'new.pdf' });
    rerender({ id: 2 });

    // Advance time — should only make calls for id=2
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });
    const callsForId1 = mockGetEssayStatus.mock.calls.filter(
      (c) => c[0] === 1,
    ).length;
    // No more status calls for id=1 after the switch
    expect(callsForId1).toBe(0);
  });

  it('sets error when status is failed', async () => {
    mockGetEssay.mockResolvedValue(null);
    mockGetEssayStatus.mockResolvedValueOnce({
      status: 'failed',
      error: 'Pipeline crashed',
    });

    const { result } = renderHook(() => useEssayPolling(99));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.error).toBe('Pipeline crashed');
    expect(result.current.isPolling).toBe(false);
  });
});
