import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: number;
  username: string;
  role: 'admin' | 'user';
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAdmin: boolean;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = '/api';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
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
      if (res.ok) {
        const userData = await res.json();
        setToken(tokenToValidate);
        setUser(userData);
      } else {
        localStorage.removeItem('token');
      }
    } catch {
      localStorage.removeItem('token');
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
    localStorage.setItem('token', data.token);
    setToken(data.token);
    setUser(data.user);
  };

  const logout = async () => {
    if (token) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // Ignore logout errors
      }
    }
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    logout,
    isAdmin: user?.role === 'admin',
    isLoading,
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
