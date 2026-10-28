import type { ReactElement, ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { render, type RenderOptions } from '@testing-library/react';
import { AuthContext } from '@/contexts/AuthContext';
import type { User } from '@/api/client';

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

interface WrapperOptions {
  /** Mock authenticated user; default = admin */
  user?: User | null;
  /** Initial route for MemoryRouter; default = '/' */
  initialRoute?: string;
  /** Override QueryClient; default = fresh client with retries disabled */
  queryClient?: QueryClient;
}

function makeWrapper(options: WrapperOptions = {}) {
  const {
    user = {
      id: 1,
      username: 'admin',
      role: 'admin',
      email: 'admin@test.local',
      full_name: 'Test Admin',
      is_active: true,
      avatar_url: null,
      last_login_at: null,
      created_at: '2026-01-01T00:00:00Z',
      institution: null,
      can_override_verdicts: true,
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
              token: 'test-token',
              isAdmin: user?.role === 'admin',
              isLoading: false,
              login: async () => {},
              loginWithGoogle: async () => {},
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
