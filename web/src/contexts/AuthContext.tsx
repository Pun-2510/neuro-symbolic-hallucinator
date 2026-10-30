import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { GoogleLoginPayload, User } from '@/api/client';
import { queryClient } from '@/lib/queryClient';

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  loginWithGoogle?: (payload: GoogleLoginPayload) => Promise<void>;
  logout: () => Promise<void>;
  isAdmin: boolean;
  isLoading: boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Exported for test utilities (renderWithProviders). Production code should use useAuth().
export { AuthContext };

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(() => {
    try {
      return typeof window !== 'undefined' && Boolean(localStorage.getItem('token'));
    } catch {
      return false;
    }
  });

  // Check for existing session on mount
  useEffect(() => {
    let storedToken: string | null = null;
    try {
      storedToken = localStorage.getItem('token');
    } catch {
      storedToken = null;
    }
    if (storedToken) {
      validateToken(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const validateToken = async (tokenToValidate: string) => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${tokenToValidate}` },
      });
      // 401/403 = token expired or revoked — drop it silently. Other
      // statuses (5xx, network) keep the token so a transient backend
      // outage doesn't sign the user out.
      if (res.ok) {
        const userData: User = await res.json();
        setToken(tokenToValidate);
        setUser(userData);
      } else if (res.status === 401 || res.status === 403) {
        localStorage.removeItem('token');
      }
    } catch {
      // Network error — keep the token; the next mount retries validation.
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
    } catch (networkErr) {
      throw new Error(
        networkErr instanceof Error
          ? `Cannot reach server: ${networkErr.message}`
          : 'Cannot reach server'
      );
    }

    if (!res.ok) {
      // Parse error body safely — backend may return JSON or plain text/empty
      let detail = `Login failed (HTTP ${res.status})`;
      try {
        const contentType = res.headers.get('content-type') ?? '';
        if (contentType.includes('application/json')) {
          const error = await res.json();
          if (typeof error?.detail === 'string') {
            detail = error.detail;
          } else if (Array.isArray(error?.detail)) {
            // FastAPI validation errors: [{loc, msg, type}, ...]
            detail = error.detail
              .map((d: { msg?: string }) => d?.msg)
              .filter(Boolean)
              .join('; ') || detail;
          } else if (typeof error?.message === 'string') {
            detail = error.message;
          }
        } else {
          const text = (await res.text()).trim();
          if (text) detail = text;
        }
      } catch {
        // Body wasn't readable as JSON — keep default message
      }
      throw new Error(detail);
    }

    const data = await res.json();
    queryClient.clear();
    localStorage.setItem('token', data.token);
    setToken(data.token);
    setUser(data.user);
  };

  const loginWithGoogle = async (payload: GoogleLoginPayload) => {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } catch (networkErr) {
      throw new Error(
        networkErr instanceof Error
          ? `Cannot reach server: ${networkErr.message}`
          : 'Cannot reach server'
      );
    }

    if (!res.ok) {
      let detail = `Google login failed (HTTP ${res.status})`;
      try {
        const contentType = res.headers.get('content-type') ?? '';
        if (contentType.includes('application/json')) {
          const error = await res.json();
          if (typeof error?.detail === 'string') {
            detail = error.detail;
          } else if (Array.isArray(error?.detail)) {
            detail =
              error.detail
                .map((d: { msg?: string }) => d?.msg)
                .filter(Boolean)
                .join('; ') || detail;
          } else if (typeof error?.message === 'string') {
            detail = error.message;
          }
        } else {
          const text = (await res.text()).trim();
          if (text) detail = text;
        }
      } catch {
        // Keep default message
      }
      throw new Error(detail);
    }

    const data = await res.json();
    queryClient.clear();
    localStorage.setItem('token', data.token);
    setToken(data.token);
    setUser(data.user);
  };

  const logout = async () => {
    const currentToken = localStorage.getItem('token');
    if (currentToken) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${currentToken}` },
        });
      } catch {
        // Ignore logout errors - local state still cleared
      }
    }
    localStorage.removeItem('token');
    queryClient.clear();
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    const activeToken = localStorage.getItem('token') || token;
    if (!activeToken) return;
    try {
      const res = await fetch(`${API_BASE}/users/me`, {
        headers: { Authorization: `Bearer ${activeToken}` },
      });
      if (res.ok) {
        const userData: User = await res.json();
        setToken(activeToken);
        setUser(userData);
      }
    } catch {
      // Silently ignore refresh errors
    }
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    loginWithGoogle,
    logout,
    isAdmin: user?.role === 'admin',
    isLoading,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
