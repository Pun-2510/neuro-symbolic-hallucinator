import { useState, useEffect, useCallback } from 'react';

/**
 * Hook đọc/ghi localStorage với type safety.
 * Tự động JSON.stringify khi ghi, JSON.parse khi đọc.
 * Fallback về `initial` nếu parse lỗi hoặc localStorage không khả dụng.
 *
 * Lưu ý: hook này KHÔNG đồng bộ giữa các tab/window.
 * Nếu cần sync across tabs, dùng `storage` event listener.
 *
 * @example
 *   const [theme, setTheme] = useLocalStorage<'light' | 'dark'>('theme', 'light');
 */
export function useLocalStorage<T>(
  key: string,
  initial: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  const [value, setValue] = useState<T>(() => {
    // Lazy init — chỉ đọc localStorage 1 lần khi mount
    if (typeof window === 'undefined') return initial;
    try {
      const raw = window.localStorage.getItem(key);
      return raw !== null ? (JSON.parse(raw) as T) : initial;
    } catch {
      // Parse lỗi (corrupt data) hoặc storage không khả dụng (private mode)
      return initial;
    }
  });

  // Ghi vào localStorage mỗi khi value thay đổi
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // QuotaExceededError hoặc storage không khả dụng — silently ignore
    }
  }, [key, value]);

  // Wrap setValue để tương thích với functional updater như useState
  const setStoredValue = useCallback(
    (next: T | ((prev: T) => T)) => {
      setValue((prev) => {
        const resolved =
          typeof next === 'function' ? (next as (p: T) => T)(prev) : next;
        return resolved;
      });
    },
    [],
  );

  return [value, setStoredValue];
}
