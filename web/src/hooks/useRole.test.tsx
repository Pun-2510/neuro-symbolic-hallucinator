import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useRole, type UserRole, type UserCapability } from './useRole';
import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AuthContext } from '@/contexts/AuthContext';
import type { User } from '@/api/client';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

function hookWrapper(user: User | null) {
  const queryClient = createTestQueryClient();
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AuthContext.Provider
            value={{
              user,
              token: user ? 'mock-token' : null,
              isLoading: false,
              isAdmin: user?.role === 'admin',
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

const userOf = (role: UserRole): User => ({
  id: 1,
  username: 'test',
  role,
  email: 't@test.local',
  full_name: 'Test',
  is_active: true,
  avatar_url: null,
  last_login_at: null,
  created_at: null,
  institution: null,
  can_override_verdicts: role !== 'user',
});

describe('useRole', () => {
  describe('flags', () => {
    it('admin', () => {
      const { result } = renderHook(() => useRole(), {
        wrapper: hookWrapper(userOf('admin')),
      });
      expect(result.current.isAdmin).toBe(true);
      expect(result.current.isTeacher).toBe(false);
      expect(result.current.isUser).toBe(false);
    });

    it('teacher', () => {
      const { result } = renderHook(() => useRole(), {
        wrapper: hookWrapper(userOf('teacher')),
      });
      expect(result.current.isAdmin).toBe(false);
      expect(result.current.isTeacher).toBe(true);
      expect(result.current.isUser).toBe(false);
    });

    it('user (student)', () => {
      const { result } = renderHook(() => useRole(), {
        wrapper: hookWrapper(userOf('user')),
      });
      expect(result.current.isAdmin).toBe(false);
      expect(result.current.isTeacher).toBe(false);
      expect(result.current.isUser).toBe(true);
    });
  });

  describe('has(capability)', () => {
    it('admin has all capabilities', () => {
      const { result } = renderHook(() => useRole(), {
        wrapper: hookWrapper(userOf('admin')),
      });
      const caps: UserCapability[] = [
        'upload_essay',
        'view_own_history',
        'view_class_history',
        'override_verdict',
        'view_logic_trace',
        'view_document_inspector',
        'view_orphan_detection',
        'create_class',
        'manage_users',
        'system_settings',
        'view_audit_log',
        'view_system_health',
      ];
      for (const c of caps) {
        expect(result.current.has(c)).toBe(true);
      }
    });

    it('teacher has class capabilities but not admin-only', () => {
      const { result } = renderHook(() => useRole(), {
        wrapper: hookWrapper(userOf('teacher')),
      });
      // Teacher capabilities
      expect(result.current.has('view_class_history')).toBe(true);
      expect(result.current.has('override_verdict')).toBe(true);
      expect(result.current.has('view_logic_trace')).toBe(true);
      expect(result.current.has('view_document_inspector')).toBe(true);
      expect(result.current.has('view_orphan_detection')).toBe(true);
      expect(result.current.has('create_class')).toBe(true);
      // Admin-only
      expect(result.current.has('manage_users')).toBe(false);
      expect(result.current.has('system_settings')).toBe(false);
      expect(result.current.has('view_audit_log')).toBe(false);
      expect(result.current.has('view_system_health')).toBe(false);
    });

    it('user has only student capabilities', () => {
      const { result } = renderHook(() => useRole(), {
        wrapper: hookWrapper(userOf('user')),
      });
      expect(result.current.has('upload_essay')).toBe(true);
      expect(result.current.has('view_own_history')).toBe(true);
      expect(result.current.has('view_class_history')).toBe(false);
      expect(result.current.has('override_verdict')).toBe(false);
      expect(result.current.has('view_logic_trace')).toBe(false);
      expect(result.current.has('view_document_inspector')).toBe(false);
      expect(result.current.has('view_orphan_detection')).toBe(false);
      expect(result.current.has('create_class')).toBe(false);
      expect(result.current.has('manage_users')).toBe(false);
    });

    it('hasAny returns true if user has any of the caps', () => {
      const { result } = renderHook(() => useRole(), {
        wrapper: hookWrapper(userOf('teacher')),
      });
      expect(result.current.hasAny(['manage_users', 'view_class_history'])).toBe(
        true,
      );
      expect(result.current.hasAny(['manage_users'])).toBe(false);
    });

    it('hasAll returns true only if user has all caps', () => {
      const { result } = renderHook(() => useRole(), {
        wrapper: hookWrapper(userOf('teacher')),
      });
      expect(
        result.current.hasAll(['view_class_history', 'override_verdict']),
      ).toBe(true);
      expect(
        result.current.hasAll(['view_class_history', 'manage_users']),
      ).toBe(false);
    });
  });

  it('defaults to user role when not authenticated', () => {
    const { result } = renderHook(() => useRole(), {
      wrapper: hookWrapper(null),
    });
    expect(result.current.isAdmin).toBe(false);
    expect(result.current.isTeacher).toBe(false);
    expect(result.current.isUser).toBe(true);
    expect(result.current.role).toBe('user');
  });
});
