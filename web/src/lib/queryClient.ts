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
