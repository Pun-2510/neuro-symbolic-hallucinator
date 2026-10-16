import { useEffect, useState } from 'react';

/**
 * Hook debounce giá trị — dùng cho search input, filter input, etc.
 * Trả về giá trị đã được "ổn định" sau `delay` ms không thay đổi.
 *
 * @example
 *   const [query, setQuery] = useState('');
 *   const debouncedQuery = useDebounce(query, 300);
 *   useEffect(() => { fetch(debouncedQuery); }, [debouncedQuery]);
 */
export function useDebounce<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState<T>(value);

  useEffect(() => {
    // Reset timer mỗi khi value thay đổi
    const timer = setTimeout(() => setDebounced(value), delay);
    // Cleanup: cancel timer nếu value thay đổi trước khi delay kết thúc
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}
