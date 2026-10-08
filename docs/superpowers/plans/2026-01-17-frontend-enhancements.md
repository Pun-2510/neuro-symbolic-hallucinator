# Frontend Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add React error boundaries (~30 min), toast notification system (~1 hour), dark mode, internationalization (VI/EN), settings page, API rate limiting awareness, DOCX export, performance optimization, and help/tutorial system to the Essay Integrity Checker frontend.

**Architecture:** 
- **Error Boundaries**: Wrap route-level components with ErrorBoundary HOC, create fallback UI components
- **Toast System**: Create React Context-based toast provider with types (success, error, warning, info), auto-dismiss, and queue management
- **Dark Mode**: Use Tailwind `darkMode: 'class'` with CSS variable mapping, persist preference in localStorage
- **i18n**: Use `react-i18next` with JSON translation files, namespace per feature
- **Settings Page**: Create SettingsContext for preferences, persist in localStorage, integrate with components
- **Rate Limiting**: Create RateLimitContext to track API calls, display warning when approaching limits
- **DOCX Export**: Use `docx` library, create report template with styling
- **Performance**: Add React.memo, useMemo, useCallback where appropriate, lazy loading for routes
- **Help/Tutorial**: Create help modal with feature documentation, keyboard shortcuts

**Tech Stack:** React 18, TypeScript, Tailwind CSS, react-i18next, react-hot-toast (or custom), docx, react-router-dom

**Spec:** Feature backlog from project paste

---

## Global Constraints

- All changes must be backward compatible
- Maintain existing UI/UX patterns
- Use Vietnamese comments for user-facing code, English for internal logic
- TypeScript strict mode
- All new components must be tested

## Review Focus

1. **Toast stacking**: Multiple toasts should not overlap or cause layout shift
2. **Dark mode persistence**: Theme should persist across page reloads and sessions
3. **i18n completeness**: All user-facing strings must be translated
4. **Error boundary isolation**: One component crash should not take down entire app
5. **Settings sync**: Settings changes should reflect immediately across the app

---

## Task 1: React Error Boundary System

**Files:**
- Create: `web/src/components/ErrorBoundary.tsx`
- Create: `web/src/components/ErrorFallback.tsx`
- Create: `web/src/hooks/useErrorBoundary.ts`
- Modify: `web/src/App.tsx:1-16`
- Create: `tests/unit/test_error_boundary.tsx`

**Interfaces:**
- Consumes: `children`, `fallbackComponent`
- Produces: `ErrorBoundary` component, `resetError()` hook

### Task 1: React Error Boundary System

- [ ] **Step 1: Create ErrorBoundary component**

```tsx
// web/src/components/ErrorBoundary.tsx
import { Component, ReactNode, ErrorInfo } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackComponent?: React.ComponentType<{ error: Error; resetError: () => void }>;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  resetError = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallbackComponent) {
        const Fallback = this.props.fallbackComponent;
        return <Fallback error={this.state.error} resetError={this.resetError} />;
      }
      return (
        <div className="p-6 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-xl">
          <h2 className="text-lg font-semibold text-red-700 dark:text-red-300 mb-2">
            Something went wrong
          </h2>
          <p className="text-sm text-red-600 dark:text-red-400 mb-4">
            {this.state.error.message}
          </p>
          <button
            onClick={this.resetError}
            className="btn-primary btn-sm"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 2: Create ErrorFallback component**

```tsx
// web/src/components/ErrorFallback.tsx
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Link } from 'react-router-dom';

interface ErrorFallbackProps {
  error: Error;
  resetError: () => void;
}

export function ErrorFallback({ error, resetError }: ErrorFallbackProps) {
  return (
    <div className="min-h-[400px] flex items-center justify-center p-8">
      <div className="max-w-md w-full">
        <div className="card p-8 text-center bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800">
          <div className="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900 flex items-center justify-center mx-auto mb-6">
            <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />
          </div>
          <h2 className="font-display text-2xl font-bold text-red-700 dark:text-red-300 mb-3">
            Oops! Something went wrong
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mb-6">
            We encountered an unexpected error. The page has been safely isolated.
          </p>
          {error.message && (
            <div className="mb-6 p-4 bg-red-100/50 dark:bg-red-900/50 rounded-lg text-left">
              <p className="text-xs font-mono text-red-600 dark:text-red-400 break-all">
                {error.message}
              </p>
            </div>
          )}
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={resetError}
              className="btn-secondary"
            >
              <RefreshCw className="h-4 w-4" />
              Try Again
            </button>
            <Link to="/dashboard" className="btn-primary">
              <Home className="h-4 w-4" />
              Go Home
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create useErrorBoundary hook**

```tsx
// web/src/hooks/useErrorBoundary.ts
import { useCallback, useState, useEffect } from 'react';

interface UseErrorBoundaryReturn {
  ErrorBoundary: React.ComponentType<{
    children: React.ReactNode;
    fallbackComponent?: React.ComponentType<{ error: Error; resetError: () => void }>;
  }>;
  showError: (error: Error) => void;
  resetError: () => void;
  error: Error | null;
}

// Lazy import to avoid circular dependency
let ErrorBoundaryClass: any = null;

export function useErrorBoundary(): UseErrorBoundaryReturn {
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    import('../components/ErrorBoundary').then((mod) => {
      ErrorBoundaryClass = mod.ErrorBoundary;
    });
  }, []);

  const showError = useCallback((err: Error) => {
    setError(err);
  }, []);

  const resetError = useCallback(() => {
    setError(null);
  }, []);

  const ErrorBoundary = useCallback(
    ({ children, fallbackComponent }: { children: React.ReactNode; fallbackComponent?: any }) => {
      if (!ErrorBoundaryClass) return children;
      return (
        <ErrorBoundaryClass fallbackComponent={fallbackComponent}>
          {children}
        </ErrorBoundaryClass>
      );
    },
    []
  );

  return { ErrorBoundary, showError, resetError, error };
}
```

- [ ] **Step 4: Update App.tsx to wrap with ErrorBoundary**

```tsx
// web/src/App.tsx
import { RouterProvider } from 'react-router-dom';
import { router, AuthProvider } from './router';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ErrorFallback } from './components/ErrorFallback';

export default function App() {
  return (
    <ErrorBoundary fallbackComponent={ErrorFallback}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ErrorBoundary>
  );
}
```

- [ ] **Step 5: Add ErrorBoundary to individual route components**

For pages that make API calls (DashboardPage, EssayPage, etc.), wrap content in ErrorBoundary:

```tsx
// Example: DashboardPage.tsx - wrap content
export function DashboardPage() {
  // ... existing hooks
  
  return (
    <ErrorBoundary fallbackComponent={ErrorFallback}>
      <div className="space-y-6">
        {/* existing content */}
      </div>
    </ErrorBoundary>
  );
}
```

Apply to: DashboardPage, EssayPage, BatchUploadPage, ProcessingPage, IssuesPage, LogicTracePage, DocumentInspectorPage, OrphanDetectionPage

- [ ] **Step 6: Write unit tests**

```tsx
// tests/unit/test_error_boundary.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '@/components/ErrorBoundary';

const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) throw new Error('Test error');
  return <div>Content rendered</div>;
};

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={false} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Content rendered')).toBeInTheDocument();
  });

  it('shows fallback when error occurs', () => {
    const Fallback = ({ resetError }: any) => (
      <div>
        <p>Error occurred</p>
        <button onClick={resetError}>Retry</button>
      </div>
    );

    render(
      <ErrorBoundary fallbackComponent={Fallback}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Error occurred')).toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Commit**

```bash
git add web/src/components/ErrorBoundary.tsx web/src/components/ErrorFallback.tsx web/src/hooks/useErrorBoundary.ts web/src/App.tsx
git commit -m "feat: add React error boundary system for graceful error handling"
```

---

## Task 2: Toast Notification System

**Files:**
- Create: `web/src/components/Toast.tsx`
- Create: `web/src/contexts/ToastContext.tsx`
- Create: `web/src/hooks/useToast.ts`
- Create: `web/src/components/ToastContainer.tsx`
- Modify: `web/src/App.tsx:1-16`
- Create: `tests/unit/test_toast.tsx`

**Interfaces:**
- Consumes: `ToastContext`
- Produces: `toast.success()`, `toast.error()`, `toast.warning()`, `toast.info()`

### Task 2: Toast Notification System

- [ ] **Step 1: Define Toast types and interfaces**

```tsx
// web/src/types/toast.ts
export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  clearAll: () => void;
}
```

- [ ] **Step 2: Create ToastContext**

```tsx
// web/src/contexts/ToastContext.tsx
import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { Toast, ToastContextType, ToastType } from '@/types/toast';

const ToastContext = createContext<ToastContextType | undefined>(undefined);

const DEFAULT_DURATION = 5000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, 'id'>): string => {
    const id = crypto.randomUUID();
    const newToast: Toast = { ...toast, id };
    
    setToasts((prev) => [...prev, newToast]);

    // Auto-remove after duration
    const duration = toast.duration ?? DEFAULT_DURATION;
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setToasts([]);
  }, []);

  const value: ToastContextType = {
    toasts,
    addToast,
    removeToast,
    clearAll,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

// Convenience methods
export function useToastActions() {
  const { addToast } = useToast();

  return {
    success: (title: string, message?: string) =>
      addToast({ type: 'success', title, message }),
    error: (title: string, message?: string) =>
      addToast({ type: 'error', title, message }),
    warning: (title: string, message?: string) =>
      addToast({ type: 'warning', title, message }),
    info: (title: string, message?: string) =>
      addToast({ type: 'info', title, message }),
    custom: (toast: Omit<Toast, 'id'>) => addToast(toast),
  };
}
```

- [ ] **Step 3: Create Toast component**

```tsx
// web/src/components/Toast.tsx
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';
import type { ToastType } from '@/types/toast';
import { cn } from '@/lib/utils';

interface ToastItemProps {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  onDismiss: (id: string) => void;
}

const icons: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 className="h-5 w-5" />,
  error: <AlertCircle className="h-5 w-5" />,
  warning: <AlertTriangle className="h-5 w-5" />,
  info: <Info className="h-5 w-5" />,
};

const styles: Record<ToastType, { bg: string; border: string; icon: string; title: string }> = {
  success: {
    bg: 'bg-emerald-50 dark:bg-emerald-950/80',
    border: 'border-emerald-200 dark:border-emerald-800',
    icon: 'text-emerald-600 dark:text-emerald-400',
    title: 'text-emerald-800 dark:text-emerald-200',
  },
  error: {
    bg: 'bg-red-50 dark:bg-red-950/80',
    border: 'border-red-200 dark:border-red-800',
    icon: 'text-red-600 dark:text-red-400',
    title: 'text-red-800 dark:text-red-200',
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-950/80',
    border: 'border-amber-200 dark:border-amber-800',
    icon: 'text-amber-600 dark:text-amber-400',
    title: 'text-amber-800 dark:text-amber-200',
  },
  info: {
    bg: 'bg-blue-50 dark:bg-blue-950/80',
    border: 'border-blue-200 dark:border-blue-800',
    icon: 'text-blue-600 dark:text-blue-400',
    title: 'text-blue-800 dark:text-blue-200',
  },
};

export function ToastItem({ id, type, title, message, onDismiss }: ToastItemProps) {
  const style = styles[type];

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-xl border shadow-lg animate-slideInRight',
        'w-80 max-w-[calc(100vw-2rem)]',
        style.bg,
        style.border
      )}
      role="alert"
    >
      <div className={cn('shrink-0', style.icon)}>
        {icons[type]}
      </div>
      <div className="flex-1 min-w-0">
        <p className={cn('font-semibold text-sm', style.title)}>
          {title}
        </p>
        {message && (
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
            {message}
          </p>
        )}
      </div>
      <button
        onClick={() => onDismiss(id)}
        className="shrink-0 p-1 hover:bg-slate-200/50 dark:hover:bg-slate-700/50 rounded transition-colors"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4 text-slate-400" />
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Create ToastContainer**

```tsx
// web/src/components/ToastContainer.tsx
import { useToast } from '@/contexts/ToastContext';
import { ToastItem } from './Toast';

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2"
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          id={toast.id}
          type={toast.type}
          title={toast.title}
          message={toast.message}
          onDismiss={removeToast}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Update App.tsx to include ToastProvider and ToastContainer**

```tsx
// web/src/App.tsx
import { RouterProvider } from 'react-router-dom';
import { router, AuthProvider } from './router';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ErrorFallback } from './components/ErrorFallback';
import { ToastProvider } from './contexts/ToastContext';
import { ToastContainer } from './components/ToastContainer';

export default function App() {
  return (
    <ErrorBoundary fallbackComponent={ErrorFallback}>
      <AuthProvider>
        <ToastProvider>
          <RouterProvider router={router} />
          <ToastContainer />
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
```

- [ ] **Step 6: Replace inline error handling with toast in key components**

In DashboardPage.tsx - replace `alert('Delete failed')` with toast:

```tsx
// Add import
import { useToastActions } from '@/contexts/ToastContext';

// Inside component
const toast = useToastActions();

// Replace alert calls
toast.error('Delete failed', 'Could not delete the document. Please try again.');
```

Apply to: DashboardPage, ProfilePage, BatchUploadPage, UploadPage

- [ ] **Step 7: Write unit tests**

```tsx
// tests/unit/test_toast.tsx
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ToastProvider, useToastActions, useToast } from '@/contexts/ToastContext';
import { ToastContainer } from '@/components/ToastContainer';
import { TextDecoder } from 'util';

function TestComponent() {
  const toast = useToastActions();
  const { toasts } = useToast();

  return (
    <div>
      <button onClick={() => toast.success('Test Success', 'Message')}>
        Show Success
      </button>
      <button onClick={() => toast.error('Test Error')}>
        Show Error
      </button>
      <p data-testid="toast-count">{toasts.length}</p>
    </div>
  );
}

describe('Toast System', () => {
  it('renders toast when success is called', async () => {
    render(
      <ToastProvider>
        <TestComponent />
        <ToastContainer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText('Show Success'));
    expect(await screen.findByText('Test Success')).toBeInTheDocument();
  });

  it('auto-dismisses after 5 seconds', async () => {
    jest.useFakeTimers();
    
    render(
      <ToastProvider>
        <TestComponent />
        <ToastContainer />
      </ToastProvider>
    );

    fireEvent.click(screen.getByText('Show Success'));
    expect(screen.getByTestId('toast-count')).toHaveTextContent('1');

    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(screen.getByTestId('toast-count')).toHaveTextContent('0');
    
    jest.useRealTimers();
  });
});
```

- [ ] **Step 8: Commit**

```bash
git add web/src/contexts/ToastContext.tsx web/src/components/Toast.tsx web/src/components/ToastContainer.tsx web/src/types/toast.ts
git commit -m "feat: add toast notification system with auto-dismiss"
```

---

## Task 3: Dark Mode Implementation

**Files:**
- Create: `web/src/contexts/ThemeContext.tsx`
- Create: `web/src/hooks/useTheme.ts`
- Modify: `web/src/index.css:1-886` (add dark mode styles)
- Modify: `web/tailwind.config.js` (enable dark mode)
- Create: `web/src/components/ThemeToggle.tsx`
- Modify: `web/src/components/AppLayout.tsx:1-290` (add toggle to sidebar)

**Interfaces:**
- Consumes: `ThemeContext`
- Produces: `theme: 'light' | 'dark'`, `toggleTheme()`, `setTheme()`

### Task 3: Dark Mode Implementation

- [ ] **Step 1: Update tailwind.config.js to enable dark mode**

```js
// web/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class', // Enable class-based dark mode
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  // ... existing config
};
```

- [ ] **Step 2: Create ThemeContext**

```tsx
// web/src/contexts/ThemeContext.tsx
import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  resolvedTheme: Theme;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const STORAGE_KEY = 'sourcelogic-theme';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Check localStorage first
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'dark' || stored === 'light') return stored;
    }
    // Default to system preference
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  });

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement;
    
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    
    // Store preference
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  // Listen for system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e: MediaQueryListEvent) => {
      // Only auto-switch if user hasn't set explicit preference
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) {
        setThemeState(e.matches ? 'dark' : 'light');
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === 'light' ? 'dark' : 'light'));
  }, []);

  const resolvedTheme = theme;

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextType {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
```

- [ ] **Step 3: Create ThemeToggle component**

```tsx
// web/src/components/ThemeToggle.tsx
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { cn } from '@/lib/utils';

interface ThemeToggleProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function ThemeToggle({ className, size = 'md' }: ThemeToggleProps) {
  const { theme, toggleTheme } = useTheme();

  const sizeClasses = {
    sm: 'p-2',
    md: 'p-2.5',
    lg: 'p-3',
  };

  const iconSizes = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
  };

  return (
    <button
      onClick={toggleTheme}
      className={cn(
        'rounded-xl transition-all duration-200',
        'hover:bg-slate-100 dark:hover:bg-slate-800',
        'text-slate-600 dark:text-slate-400',
        'hover:text-slate-900 dark:hover:text-white',
        sizeClasses[size],
        className
      )}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'light' ? (
        <Moon className={iconSizes[size]} />
      ) : (
        <Sun className={iconSizes[size]} />
      )}
    </button>
  );
}
```

- [ ] **Step 4: Update App.tsx to include ThemeProvider**

```tsx
// web/src/App.tsx
import { RouterProvider } from 'react-router-dom';
import { router, AuthProvider } from './router';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ErrorFallback } from './components/ErrorFallback';
import { ToastProvider } from './contexts/ToastContext';
import { ToastContainer } from './components/ToastContainer';
import { ThemeProvider } from './contexts/ThemeContext';

export default function App() {
  return (
    <ErrorBoundary fallbackComponent={ErrorFallback}>
      <ThemeProvider>
        <AuthProvider>
          <ToastProvider>
            <RouterProvider router={router} />
            <ToastContainer />
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
```

- [ ] **Step 5: Add ThemeToggle to AppLayout sidebar**

In `web/src/components/AppLayout.tsx`, add ThemeToggle after the logo section:

```tsx
// Add imports
import { ThemeToggle } from './ThemeToggle';

// Add in the sidebar, after the logo div:
<div className="flex items-center justify-between">
  {/* Logo */}
  <Link to="/dashboard" className="...">
    {/* ... existing logo code ... */}
  </Link>
  
  {/* Theme Toggle */}
  <ThemeToggle />
</div>
```

- [ ] **Step 6: Update index.css with enhanced dark mode CSS variables**

Add dark mode variable overrides:

```css
/* In index.css, after :root section, add dark mode overrides */
@layer base {
  /* ... existing :root ... */
  
  .dark {
    --bg: 222 47% 11%;           /* #0F172A */
    --text: 210 40% 98%;          /* #F8FAFC */
    --surface: 217 33% 17%;       /* #1E293B */
    --muted: 215 20% 65%;         /* #94A3B8 */
    --border: 217 33% 25%;        /* #334155 */
    --input: 217 33% 25%;
    
    /* Dark mode specific */
    background-color: hsl(222 47% 11%);
    color: hsl(210 40% 98%);
  }
}
```

- [ ] **Step 7: Update components to use dark mode CSS variables**

The existing CSS already has good dark mode support with `dark:` prefixed Tailwind classes. Ensure critical components use these properly.

- [ ] **Step 8: Write tests**

```tsx
// tests/unit/test_theme.tsx
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ThemeProvider, useTheme } from '@/contexts/ThemeContext';

function TestComponent() {
  const { theme, toggleTheme } = useTheme();
  return (
    <div>
      <p data-testid="theme">{theme}</p>
      <button onClick={toggleTheme}>Toggle</button>
    </div>
  );
}

describe('Theme', () => {
  it('defaults to light theme', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    expect(screen.getByTestId('theme')).toHaveTextContent('light');
  });

  it('toggles theme when button clicked', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );
    
    fireEvent.click(screen.getByText('Toggle'));
    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
  });
});
```

- [ ] **Step 9: Commit**

```bash
git add web/src/contexts/ThemeContext.tsx web/src/components/ThemeToggle.tsx web/tailwind.config.js web/src/App.tsx
git commit -m "feat: implement dark mode with system preference detection"
```

---

## Task 4: Internationalization (VI/EN)

**Files:**
- Create: `web/src/i18n/index.ts`
- Create: `web/src/i18n/locales/en.json`
- Create: `web/src/i18n/locales/vi.json`
- Create: `web/src/contexts/I18nContext.tsx`
- Modify: `web/src/App.tsx` (wrap with I18nProvider)
- Modify: Key pages to use translation keys

**Interfaces:**
- Consumes: `I18nContext`
- Produces: `t()`, `language`, `setLanguage()`

### Task 4: Internationalization (VI/EN)

- [ ] **Step 1: Create i18n configuration**

```tsx
// web/src/i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';
import vi from './locales/vi.json';

const STORAGE_KEY = 'sourcelogic-language';

const resources = {
  en: { translation: en },
  vi: { translation: vi },
};

// Get initial language
const getInitialLanguage = (): string => {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && ['en', 'vi'].includes(stored)) return stored;
    // Default to browser language or English
    const browserLang = navigator.language.split('-')[0];
    return ['en', 'vi'].includes(browserLang) ? browserLang : 'en';
  }
  return 'en';
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: getInitialLanguage(),
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });

// Persist language changes
i18n.on('languageChanged', (lng) => {
  localStorage.setItem(STORAGE_KEY, lng);
  document.documentElement.lang = lng;
});

export default i18n;
```

- [ ] **Step 2: Create English translations**

```json
// web/src/i18n/locales/en.json
{
  "common": {
    "appName": "SourceLogic",
    "loading": "Loading...",
    "error": "Error",
    "success": "Success",
    "cancel": "Cancel",
    "save": "Save",
    "delete": "Delete",
    "edit": "Edit",
    "close": "Close",
    "back": "Back",
    "next": "Next",
    "retry": "Retry",
    "signOut": "Sign out",
    "signIn": "Sign in"
  },
  "nav": {
    "dashboard": "Dashboard",
    "newCheck": "New Check",
    "batchCheck": "Batch Check",
    "history": "History",
    "profile": "Profile",
    "accountManagement": "Account Management"
  },
  "auth": {
    "login": "Sign In",
    "logout": "Sign Out",
    "username": "Username",
    "password": "Password",
    "loginSuccess": "Successfully signed in",
    "loginFailed": "Sign in failed"
  },
  "upload": {
    "title": "New Verification",
    "dropzone": "Drop your document here",
    "browseFiles": "or browse file",
    "pdfOnly": "PDF only",
    "startVerification": "Start Verification",
    "uploading": "Uploading...",
    "uploadSuccess": "Document uploaded successfully",
    "uploadError": "Upload failed"
  },
  "dashboard": {
    "title": "Dashboard",
    "subtitle": "Overview of your verification workspace",
    "totalDocuments": "Total Documents",
    "totalCitations": "Total Citations",
    "avgCISScore": "Avg CIS Score",
    "verifiedRate": "Verified Rate",
    "noDocuments": "No documents yet",
    "uploadFirst": "Upload your first document to start verifying citations",
    "searchDocuments": "Search documents..."
  },
  "verdict": {
    "verified": "Verified",
    "metadataError": "Metadata Error",
    "suspectedHallucination": "Suspected Hallucination",
    "unresolved": "Unresolved",
    "resource": "URL Resource",
    "total": "Total",
    "coverage": "Coverage"
  },
  "processing": {
    "title": "Processing",
    "extractingCitations": "Extracting citations and references",
    "linkingCitations": "Linking citations to references",
    "retrievingSources": "Retrieving from academic sources",
    "verifying": "Verifying citations",
    "complete": "Analysis complete"
  },
  "errors": {
    "generic": "Something went wrong",
    "networkError": "Network error. Please check your connection.",
    "notFound": "Not found",
    "unauthorized": "Please sign in to continue"
  },
  "settings": {
    "title": "Settings",
    "language": "Language",
    "theme": "Theme",
    "lightMode": "Light",
    "darkMode": "Dark",
    "systemDefault": "System default"
  }
}
```

- [ ] **Step 3: Create Vietnamese translations**

```json
// web/src/i18n/locales/vi.json
{
  "common": {
    "appName": "SourceLogic",
    "loading": "Đang tải...",
    "error": "Lỗi",
    "success": "Thành công",
    "cancel": "Hủy",
    "save": "Lưu",
    "delete": "Xóa",
    "edit": "Sửa",
    "close": "Đóng",
    "back": "Quay lại",
    "next": "Tiếp theo",
    "retry": "Thử lại",
    "signOut": "Đăng xuất",
    "signIn": "Đăng nhập"
  },
  "nav": {
    "dashboard": "Bảng điều khiển",
    "newCheck": "Kiểm tra mới",
    "batchCheck": "Kiểm tra hàng loạt",
    "history": "Lịch sử",
    "profile": "Hồ sơ",
    "accountManagement": "Quản lý tài khoản"
  },
  "auth": {
    "login": "Đăng nhập",
    "logout": "Đăng xuất",
    "username": "Tên đăng nhập",
    "password": "Mật khẩu",
    "loginSuccess": "Đăng nhập thành công",
    "loginFailed": "Đăng nhập thất bại"
  },
  "upload": {
    "title": "Kiểm tra mới",
    "dropzone": "Kéo tài liệu vào đây",
    "browseFiles": "hoặc chọn tệp",
    "pdfOnly": "Chỉ PDF",
    "startVerification": "Bắt đầu kiểm tra",
    "uploading": "Đang tải lên...",
    "uploadSuccess": "Tài liệu đã được tải lên thành công",
    "uploadError": "Tải lên thất bại"
  },
  "dashboard": {
    "title": "Bảng điều khiển",
    "subtitle": "Tổng quan không gian làm việc của bạn",
    "totalDocuments": "Tổng tài liệu",
    "totalCitations": "Tổng trích dẫn",
    "avgCISScore": "Điểm CIS trung bình",
    "verifiedRate": "Tỷ lệ xác minh",
    "noDocuments": "Chưa có tài liệu",
    "uploadFirst": "Tải lên tài liệu đầu tiên để bắt đầu kiểm tra trích dẫn",
    "searchDocuments": "Tìm kiếm tài liệu..."
  },
  "verdict": {
    "verified": "Đã xác minh",
    "metadataError": "Lỗi siêu dữ liệu",
    "suspectedHallucination": "Nghi ngờ bịa đặt",
    "unresolved": "Chưa xác định",
    "resource": "URL Resource",
    "total": "Tổng cộng",
    "coverage": "Độ phủ"
  },
  "processing": {
    "title": "Đang xử lý",
    "extractingCitations": "Trích xuất trích dẫn và tài liệu tham khảo",
    "linkingCitations": "Liên kết trích dẫn với tài liệu tham khảo",
    "retrievingSources": "Truy hồi từ các nguồn học thuật",
    "verifying": "Đang xác minh trích dẫn",
    "complete": "Phân tích hoàn tất"
  },
  "errors": {
    "generic": "Đã xảy ra lỗi",
    "networkError": "Lỗi mạng. Vui lòng kiểm tra kết nối.",
    "notFound": "Không tìm thấy",
    "unauthorized": "Vui lòng đăng nhập để tiếp tục"
  },
  "settings": {
    "title": "Cài đặt",
    "language": "Ngôn ngữ",
    "theme": "Giao diện",
    "lightMode": "Sáng",
    "darkMode": "Tối",
    "systemDefault": "Mặc định hệ thống"
  }
}
```

- [ ] **Step 4: Create I18nContext for language switching**

```tsx
// web/src/contexts/I18nContext.tsx
import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

type Language = 'en' | 'vi';

interface I18nContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, options?: any) => string;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export function I18nProvider({ children }: { children: ReactNode }) {
  const { t, i18n } = useTranslation();
  const [language, setLanguageState] = useState<Language>(() => {
    const stored = localStorage.getItem('sourcelogic-language');
    return (stored === 'vi' ? 'vi' : 'en') as Language;
  });

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
    i18n.changeLanguage(lang);
  }, [i18n]);

  return (
    <I18nContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextType {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}
```

- [ ] **Step 5: Create LanguageToggle component**

```tsx
// web/src/components/LanguageToggle.tsx
import { Globe } from 'lucide-react';
import { useI18n } from '@/contexts/I18nContext';
import { cn } from '@/lib/utils';

interface LanguageToggleProps {
  className?: string;
}

export function LanguageToggle({ className }: LanguageToggleProps) {
  const { language, setLanguage } = useI18n();

  const toggleLanguage = () => {
    setLanguage(language === 'en' ? 'vi' : 'en');
  };

  return (
    <button
      onClick={toggleLanguage}
      className={cn(
        'flex items-center gap-2 px-3 py-2 rounded-xl',
        'text-sm font-medium',
        'text-slate-600 dark:text-slate-400',
        'hover:bg-slate-100 dark:hover:bg-slate-800',
        'transition-all duration-200',
        className
      )}
      aria-label="Toggle language"
    >
      <Globe className="h-4 w-4" />
      <span className="uppercase font-semibold">{language}</span>
    </button>
  );
}
```

- [ ] **Step 6: Update App.tsx to include i18n initialization**

```tsx
// web/src/App.tsx
import { RouterProvider } from 'react-router-dom';
import { router, AuthProvider } from './router';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ErrorFallback } from './components/ErrorFallback';
import { ToastProvider } from './contexts/ToastContext';
import { ToastContainer } from './components/ToastContainer';
import { ThemeProvider } from './contexts/ThemeContext';
import { I18nProvider } from './contexts/I18nContext';
import './i18n';

export default function App() {
  return (
    <ErrorBoundary fallbackComponent={ErrorFallback}>
      <ThemeProvider>
        <AuthProvider>
          <ToastProvider>
            <I18nProvider>
              <RouterProvider router={router} />
              <ToastContainer />
            </I18nProvider>
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
```

- [ ] **Step 7: Update AppLayout to use LanguageToggle and translations**

```tsx
// In AppLayout.tsx
import { LanguageToggle } from './LanguageToggle';

// Add LanguageToggle near ThemeToggle
<div className="flex items-center justify-between">
  <Link to="/dashboard">...</Link>
  <div className="flex items-center gap-2">
    <LanguageToggle />
    <ThemeToggle />
  </div>
</div>
```

- [ ] **Step 8: Update key pages to use translations**

Example for DashboardPage.tsx:

```tsx
// web/src/pages/DashboardPage.tsx
import { useI18n } from '@/contexts/I18nContext';

export function DashboardPage() {
  const { t } = useI18n();
  
  // Replace hardcoded strings
  // Before: <h1 className="...">Dashboard</h1>
  // After: <h1 className="...">{t('dashboard.title')}</h1>
}
```

- [ ] **Step 9: Commit**

```bash
git add web/src/i18n/ web/src/contexts/I18nContext.tsx web/src/components/LanguageToggle.tsx
git commit -m "feat: add internationalization with VI/EN support"
```

---

## Task 5: Settings Page

**Files:**
- Create: `web/src/contexts/SettingsContext.tsx`
- Create: `web/src/pages/SettingsPage.tsx`
- Modify: `web/src/router.tsx` (add settings route)
- Modify: `web/src/components/AppLayout.tsx` (add settings nav item)

**Interfaces:**
- Consumes: `SettingsContext`
- Produces: `settings`, `updateSettings()`

### Task 5: Settings Page

- [ ] **Step 1: Create SettingsContext**

```tsx
// web/src/contexts/SettingsContext.tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export interface AppSettings {
  language: 'en' | 'vi';
  theme: 'light' | 'dark' | 'system';
  autoRefresh: boolean;
  refreshInterval: number; // seconds
  showCISWarnings: boolean;
  defaultExportFormat: 'json' | 'csv' | 'pdf';
  compactView: boolean;
}

const DEFAULT_SETTINGS: AppSettings = {
  language: 'en',
  theme: 'system',
  autoRefresh: false,
  refreshInterval: 30,
  showCISWarnings: true,
  defaultExportFormat: 'json',
  compactView: false,
};

const STORAGE_KEY = 'sourcelogic-settings';

interface SettingsContextType {
  settings: AppSettings;
  updateSettings: (updates: Partial<AppSettings>) => void;
  resetSettings: () => void;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        try {
          return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
        } catch {
          return DEFAULT_SETTINGS;
        }
      }
    }
    return DEFAULT_SETTINGS;
  });

  // Persist settings changes
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  }, [settings]);

  const updateSettings = (updates: Partial<AppSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  };

  const resetSettings = () => {
    setSettings(DEFAULT_SETTINGS);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, resetSettings }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings(): SettingsContextType {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}
```

- [ ] **Step 2: Create SettingsPage component**

```tsx
// web/src/pages/SettingsPage.tsx
import { useI18n } from '@/contexts/I18nContext';
import { useTheme } from '@/contexts/ThemeContext';
import { useSettings } from '@/contexts/SettingsContext';
import { Sun, Moon, Monitor, Globe, RefreshCw, Bell, Download, Layout } from 'lucide-react';
import { cn } from '@/lib/utils';

export function SettingsPage() {
  const { t, language, setLanguage } = useI18n();
  const { theme, setTheme } = useTheme();
  const { settings, updateSettings } = useSettings();

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="font-display text-3xl font-bold text-slate-900 dark:text-slate-100">
          {t('settings.title')}
        </h1>
      </div>

      {/* Appearance Section */}
      <div className="card p-6 space-y-6">
        <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
          Appearance
        </h2>

        {/* Theme */}
        <div>
          <label className="input-label flex items-center gap-2">
            <Moon className="h-4 w-4" />
            {t('settings.theme')}
          </label>
          <div className="flex gap-2 mt-2">
            {(['light', 'dark', 'system'] as const).map((themeOption) => {
              const Icon = themeOption === 'light' ? Sun : themeOption === 'dark' ? Moon : Monitor;
              const label = themeOption === 'light' 
                ? t('settings.lightMode')
                : themeOption === 'dark'
                  ? t('settings.darkMode')
                  : t('settings.systemDefault');
              
              return (
                <button
                  key={themeOption}
                  onClick={() => setTheme(themeOption === 'system' ? 'light' : themeOption)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-xl border transition-all',
                    theme === themeOption
                      ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                      : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Language */}
        <div>
          <label className="input-label flex items-center gap-2">
            <Globe className="h-4 w-4" />
            {t('settings.language')}
          </label>
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => setLanguage('en')}
              className={cn(
                'px-4 py-2 rounded-xl border transition-all',
                language === 'en'
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950 text-indigo-700'
                  : 'border-slate-200 dark:border-slate-700 text-slate-600'
              )}
            >
              English
            </button>
            <button
              onClick={() => setLanguage('vi')}
              className={cn(
                'px-4 py-2 rounded-xl border transition-all',
                language === 'vi'
                  ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950 text-indigo-700'
                  : 'border-slate-200 dark:border-slate-700 text-slate-600'
              )}
            >
              Tiếng Việt
            </button>
          </div>
        </div>
      </div>

      {/* Preferences Section */}
      <div className="card p-6 space-y-6">
        <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
          Preferences
        </h2>

        {/* Auto Refresh */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <RefreshCw className="h-5 w-5 text-slate-400" />
            <div>
              <p className="font-medium text-slate-900 dark:text-slate-100">
                Auto-refresh dashboard
              </p>
              <p className="text-sm text-slate-500">
                Automatically refresh essay list every 30 seconds
              </p>
            </div>
          </div>
          <Toggle
            checked={settings.autoRefresh}
            onChange={(checked) => updateSettings({ autoRefresh: checked })}
          />
        </div>

        {/* CIS Warnings */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bell className="h-5 w-5 text-slate-400" />
            <div>
              <p className="font-medium text-slate-900 dark:text-slate-100">
                Show CIS warnings
              </p>
              <p className="text-sm text-slate-500">
                Highlight low CIS score essays
              </p>
            </div>
          </div>
          <Toggle
            checked={settings.showCISWarnings}
            onChange={(checked) => updateSettings({ showCISWarnings: checked })}
          />
        </div>

        {/* Compact View */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Layout className="h-5 w-5 text-slate-400" />
            <div>
              <p className="font-medium text-slate-900 dark:text-slate-100">
                Compact view
              </p>
              <p className="text-sm text-slate-500">
                Show more items with less spacing
              </p>
            </div>
          </div>
          <Toggle
            checked={settings.compactView}
            onChange={(checked) => updateSettings({ compactView: checked })}
          />
        </div>
      </div>

      {/* Export Section */}
      <div className="card p-6 space-y-6">
        <h2 className="font-display text-lg font-semibold text-slate-900 dark:text-slate-100">
          Export
        </h2>

        <div>
          <label className="input-label flex items-center gap-2">
            <Download className="h-4 w-4" />
            Default export format
          </label>
          <select
            value={settings.defaultExportFormat}
            onChange={(e) => updateSettings({ defaultExportFormat: e.target.value as any })}
            className="input mt-2"
          >
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
            <option value="pdf">PDF</option>
          </select>
        </div>
      </div>
    </div>
  );
}

// Simple toggle component
function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
        checked ? 'bg-indigo-600' : 'bg-slate-300 dark:bg-slate-600'
      )}
    >
      <span
        className={cn(
          'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
          checked ? 'translate-x-6' : 'translate-x-1'
        )}
      />
    </button>
  );
}
```

- [ ] **Step 3: Add SettingsProvider to App.tsx**

```tsx
// web/src/App.tsx
import { SettingsProvider } from './contexts/SettingsContext';

// Wrap with SettingsProvider
export default function App() {
  return (
    <ErrorBoundary fallbackComponent={ErrorFallback}>
      <ThemeProvider>
        <AuthProvider>
          <ToastProvider>
            <I18nProvider>
              <SettingsProvider>
                <RouterProvider router={router} />
                <ToastContainer />
              </SettingsProvider>
            </I18nProvider>
          </ToastProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
```

- [ ] **Step 4: Add SettingsPage to router**

```tsx
// web/src/router.tsx
import { SettingsPage } from './pages/SettingsPage';

// Add route
{
  path: '/settings',
  element: <SettingsPage />,
},
```

- [ ] **Step 5: Add Settings to AppLayout navigation**

```tsx
// web/src/components/AppLayout.tsx
import { Settings } from 'lucide-react';

// Add to navItems
const navItems: NavItem[] = [
  { path: '/dashboard', label: t('nav.dashboard'), icon: FileSearch },
  { path: '/upload', label: t('nav.newCheck'), icon: Upload },
  { path: '/batch-upload', label: t('nav.batchCheck'), icon: Layers },
  { path: '/history', label: t('nav.history'), icon: History },
  { path: '/settings', label: t('nav.settings'), icon: Settings },
];
```

- [ ] **Step 6: Commit**

```bash
git add web/src/contexts/SettingsContext.tsx web/src/pages/SettingsPage.tsx
git commit -m "feat: add settings page with preferences management"
```

---

## Task 6: API Rate Limiting UI Awareness

**Files:**
- Create: `web/src/contexts/RateLimitContext.tsx`
- Create: `web/src/hooks/useRateLimit.ts`
- Modify: `web/src/api/client.ts` (wrap API calls with rate limit tracking)

**Interfaces:**
- Consumes: `RateLimitContext`
- Produces: `isRateLimited`, `remainingCalls`, `resetTime`

### Task 6: API Rate Limiting UI Awareness

- [ ] **Step 1: Create RateLimitContext**

```tsx
// web/src/contexts/RateLimitContext.tsx
import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';

interface RateLimitState {
  isRateLimited: boolean;
  remainingCalls: number;
  resetTime: Date | null;
  totalCalls: number;
  maxCalls: number;
}

interface RateLimitContextType extends RateLimitState {
  recordCall: () => void;
  onRateLimitHit: (resetTime: Date) => void;
  reset: () => void;
}

const RateLimitContext = createContext<RateLimitContextType | undefined>(undefined);

const DEFAULT_MAX_CALLS = 100;
const WINDOW_MS = 60 * 1000; // 1 minute window

export function RateLimitProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<RateLimitState>({
    isRateLimited: false,
    remainingCalls: DEFAULT_MAX_CALLS,
    resetTime: null,
    totalCalls: 0,
    maxCalls: DEFAULT_MAX_CALLS,
  });

  const recordCall = useCallback(() => {
    setState((prev) => {
      const newRemaining = prev.remainingCalls - 1;
      const isNowLimited = newRemaining <= 0;
      
      return {
        ...prev,
        remainingCalls: Math.max(0, newRemaining),
        totalCalls: prev.totalCalls + 1,
        isRateLimited: isNowLimited,
        resetTime: isNowLimited ? new Date(Date.now() + WINDOW_MS) : prev.resetTime,
      };
    });
  }, []);

  const onRateLimitHit = useCallback((resetTime: Date) => {
    setState((prev) => ({
      ...prev,
      isRateLimited: true,
      remainingCalls: 0,
      resetTime,
    }));
  }, []);

  const reset = useCallback(() => {
    setState({
      isRateLimited: false,
      remainingCalls: DEFAULT_MAX_CALLS,
      resetTime: null,
      totalCalls: 0,
      maxCalls: DEFAULT_MAX_CALLS,
    });
  }, []);

  // Auto-reset after window expires
  useEffect(() => {
    if (!state.resetTime) return;

    const timeout = setTimeout(() => {
      reset();
    }, state.resetTime.getTime() - Date.now());

    return () => clearTimeout(timeout);
  }, [state.resetTime, reset]);

  return (
    <RateLimitContext.Provider
      value={{ ...state, recordCall, onRateLimitHit, reset }}
    >
      {children}
    </RateLimitContext.Provider>
  );
}

export function useRateLimit(): RateLimitContextType {
  const context = useContext(RateLimitContext);
  if (!context) {
    throw new Error('useRateLimit must be used within a RateLimitProvider');
  }
  return context;
}
```

- [ ] **Step 2: Create RateLimitWarning component**

```tsx
// web/src/components/RateLimitWarning.tsx
import { AlertTriangle, Clock } from 'lucide-react';
import { useRateLimit } from '@/contexts/RateLimitContext';
import { cn } from '@/lib/utils';

export function RateLimitWarning() {
  const { isRateLimited, remainingCalls, resetTime, maxCalls } = useRateLimit();

  if (!isRateLimited && remainingCalls > maxCalls * 0.2) return null;

  const percentage = (remainingCalls / maxCalls) * 100;
  const isLow = percentage <= 20;
  const isCritical = percentage <= 5;

  return (
    <div
      className={cn(
        'fixed bottom-4 left-4 z-50 p-4 rounded-xl border shadow-lg',
        'max-w-sm transition-all duration-300',
        isCritical
          ? 'bg-red-50 dark:bg-red-950 border-red-200 dark:border-red-800'
          : isLow
            ? 'bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-800'
            : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700'
      )}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle
          className={cn(
            'h-5 w-5 shrink-0 mt-0.5',
            isCritical
              ? 'text-red-600 dark:text-red-400'
              : isLow
                ? 'text-amber-600 dark:text-amber-400'
                : 'text-slate-500'
          )}
        />
        <div className="flex-1">
          <p
            className={cn(
              'font-semibold text-sm',
              isCritical
                ? 'text-red-800 dark:text-red-200'
                : isLow
                  ? 'text-amber-800 dark:text-amber-200'
                  : 'text-slate-800 dark:text-slate-200'
            )}
          >
            {isCritical
              ? 'Rate limit almost reached'
              : isLow
                ? 'API calls running low'
                : 'API Rate Limit'}
          </p>
          <p
            className={cn(
              'text-xs mt-1',
              isCritical
                ? 'text-red-600 dark:text-red-400'
                : isLow
                  ? 'text-amber-600 dark:text-amber-400'
                  : 'text-slate-600 dark:text-slate-400'
            )}
          >
            {remainingCalls} of {maxCalls} calls remaining
          </p>
          {resetTime && (
            <div className="flex items-center gap-1 mt-2 text-xs text-slate-500">
              <Clock className="h-3 w-3" />
              <span>
                Resets at {resetTime.toLocaleTimeString()}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Update API client to track rate limits**

```tsx
// web/src/api/client.ts - Add rate limit tracking
import { useRateLimit } from '@/contexts/RateLimitContext';

// In the api object, wrap fetch calls:
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { recordCall, onRateLimitHit } = useRateLimit();
  
  // Record this call
  recordCall();
  
  const token = localStorage.getItem('token');
  // ... existing code ...
  
  if (resp.status === 429) {
    const retryAfter = resp.headers.get('Retry-After');
    const resetTime = new Date(Date.now() + (parseInt(retryAfter || '60') * 1000));
    onRateLimitHit(resetTime);
    throw new Error('Rate limit exceeded. Please wait before making more requests.');
  }
  
  return resp.json();
}
```

- [ ] **Step 4: Add RateLimitProvider and Warning to App.tsx**

```tsx
// web/src/App.tsx
import { RateLimitProvider } from './contexts/RateLimitContext';
import { RateLimitWarning } from './components/RateLimitWarning';

// Wrap with RateLimitProvider
// Add RateLimitWarning after ToastContainer
```

- [ ] **Step 5: Commit**

```bash
git add web/src/contexts/RateLimitContext.tsx web/src/components/RateLimitWarning.tsx
git commit -m "feat: add API rate limiting awareness with UI warnings"
```

---

## Task 7: Export to DOCX

**Files:**
- Create: `web/src/lib/exportToDocx.ts`
- Create: `web/src/components/ExportButton.tsx`
- Modify: `web/src/pages/EssayPage.tsx` (add DOCX export option)

**Interfaces:**
- Consumes: `AnalysisReport`, `Verdict[]`
- Produces: `exportToDocx()` function that downloads .docx file

### Task 7: Export to DOCX

- [ ] **Step 1: Install docx library**

```bash
cd web
npm install docx
```

- [ ] **Step 2: Create exportToDocx function**

```tsx
// web/src/lib/exportToDocx.ts
import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  Table,
  TableRow,
  TableCell,
  WidthType,
  AlignmentType,
  BorderStyle,
} from 'docx';
import type { AnalysisReport, Verdict } from '@/api/client';

const verdictColors: Record<string, string> = {
  verified: '10B981',
  metadata_error: 'F59E0B',
  suspected_hallucination: 'EF4444',
  unresolved: '94A3B8',
  resource: '8B5CF6',
};

export async function exportToDocx(report: AnalysisReport): Promise<Blob> {
  const { cis, verdicts, filename, num_pages, num_citations } = report;

  // Calculate stats
  const stats = {
    total: verdicts.length,
    verified: verdicts.filter((v) => v.label === 'verified').length,
    metadataError: verdicts.filter((v) => v.label === 'metadata_error').length,
    suspectedHallucination: verdicts.filter((v) => v.label === 'suspected_hallucination').length,
    unresolved: verdicts.filter((v) => v.label === 'unresolved').length,
  };

  const children: Paragraph[] = [];

  // Title
  children.push(
    new Paragraph({
      text: `Citation Integrity Report: ${filename}`,
      heading: HeadingLevel.TITLE,
      spacing: { after: 400 },
    })
  );

  // Summary section
  children.push(
    new Paragraph({
      text: 'Summary',
      heading: HeadingLevel.HEADING_1,
      spacing: { before: 400, after: 200 },
    })
  );

  children.push(
    new Paragraph({
      children: [
        new TextRun({ text: 'Document: ', bold: true }),
        new TextRun(filename),
      ],
    })
  );

  children.push(
    new Paragraph({
      children: [
        new TextRun({ text: 'Pages: ', bold: true }),
        new TextRun(num_pages.toString()),
      ],
    })
  );

  children.push(
    new Paragraph({
      children: [
        new TextRun({ text: 'Total Citations: ', bold: true }),
        new TextRun(num_citations.toString()),
      ],
    })
  );

  children.push(
    new Paragraph({
      children: [
        new TextRun({ text: 'CIS Score: ', bold: true }),
        new TextRun(`${cis.score.toFixed(2)}%`),
      ],
    })
  );

  // Statistics table
  children.push(
    new Paragraph({
      text: 'Verification Statistics',
      heading: HeadingLevel.HEADING_2,
      spacing: { before: 400, after: 200 },
    })
  );

  const statsTable = new Table({
    width: { size: 50, type: WidthType.PERCENTAGE },
    rows: [
      new TableRow({
        children: ['Status', 'Count', 'Percentage'].map(
          (header) =>
            new TableCell({
              children: [
                new Paragraph({
                  children: [new TextRun({ text: header, bold: true })],
                  alignment: AlignmentType.CENTER,
                }),
              ],
              shading: { fill: 'E5E7EB' },
            })
        ),
      }),
      ...(['verified', 'metadata_error', 'suspected_hallucination', 'unresolved'].map(
        (label) => {
          const count =
            label === 'verified'
              ? stats.verified
              : label === 'metadata_error'
                ? stats.metadataError
                : label === 'suspected_hallucination'
                  ? stats.suspectedHallucination
                  : stats.unresolved;
          const percentage = stats.total > 0 ? ((count / stats.total) * 100).toFixed(1) : '0';

          return new TableRow({
            children: [
              new TableCell({
                children: [new Paragraph({ text: label.replace(/_/g, ' ').toUpperCase() })],
              }),
              new TableCell({
                children: [new Paragraph({ text: count.toString(), alignment: AlignmentType.CENTER })],
              }),
              new TableCell({
                children: [new Paragraph({ text: `${percentage}%`, alignment: AlignmentType.CENTER })],
              }),
            ],
          });
        }
      )),
    ],
  });

  children.push(statsTable);

  // Verdicts section
  children.push(
    new Paragraph({
      text: 'Citation Details',
      heading: HeadingLevel.HEADING_2,
      spacing: { before: 400, after: 200 },
    })
  );

  verdicts.slice(0, 50).forEach((verdict) => {
    const color = verdictColors[verdict.label] || '94A3B8';
    
    children.push(
      new Paragraph({
        children: [
          new TextRun({ text: `[${verdict.citation_id}] `, bold: true, color: '6B7280' }),
          new TextRun({ text: verdict.citation_raw?.slice(0, 100) || 'Unknown', color: `#${
            verdict.label === 'verified' ? '10B981' : verdict.label === 'suspected_hallucination' ? 'EF4444' : '6B7280'
          }` }),
        ],
        spacing: { after: 100 },
      })
    );

    children.push(
      new Paragraph({
        children: [
          new TextRun({ text: 'Status: ', bold: true }),
          new TextRun({ text: verdict.label.replace(/_/g, ' ').toUpperCase(), color }),
          new TextRun({ text: ` | Confidence: ${Math.round(verdict.confidence * 100)}%` }),
        ],
        spacing: { after: 50 },
        indent: { left: 200 },
      })
    );

    if (verdict.reasoning) {
      children.push(
        new Paragraph({
          children: [new TextRun({ text: verdict.reasoning, italics: true, color: '6B7280' })],
          spacing: { after: 200 },
          indent: { left: 200 },
        })
      );
    }
  });

  // Disclaimer
  children.push(
    new Paragraph({
      text: cis.disclaimer,
      spacing: { before: 600 },
      alignment: AlignmentType.CENTER,
      style: 'Caption',
    })
  );

  const doc = new Document({
    sections: [
      {
        properties: {},
        children,
      },
    ],
  });

  return Packer.toBlob(doc);
}

export function downloadDocx(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.replace('.pdf', '') + '.docx';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
```

- [ ] **Step 3: Create ExportButton component**

```tsx
// web/src/components/ExportButton.tsx
import { useState } from 'react';
import { Download, FileJson, FileSpreadsheet, FileText, Loader2 } from 'lucide-react';
import { exportToDocx, downloadDocx } from '@/lib/exportToDocx';
import type { AnalysisReport } from '@/api/client';
import { cn } from '@/lib/utils';

interface ExportButtonProps {
  report: AnalysisReport;
  currentFormat?: 'json' | 'csv' | 'pdf' | 'docx';
}

export function ExportButton({ report, currentFormat = 'json' }: ExportButtonProps) {
  const [exporting, setExporting] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  const handleExport = async (format: 'json' | 'csv' | 'pdf' | 'docx') => {
    setExporting(true);
    setShowMenu(false);

    try {
      switch (format) {
        case 'docx': {
          const blob = await exportToDocx(report);
          downloadDocx(blob, report.filename);
          break;
        }
        case 'json':
        case 'csv':
        case 'pdf':
          // Existing download logic
          window.location.href = `/api/essays/${report.essay_id}/report?format=${format}`;
          break;
      }
    } finally {
      setExporting(false);
    }
  };

  const formatIcons = {
    json: <FileJson className="h-4 w-4" />,
    csv: <FileSpreadsheet className="h-4 w-4" />,
    pdf: <FileText className="h-4 w-4" />,
    docx: <FileText className="h-4 w-4" />,
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        disabled={exporting}
        className="btn-primary btn-sm"
      >
        {exporting ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Download className="h-3.5 w-3.5" />
        )}
        Export
      </button>

      {showMenu && (
        <div className="absolute right-0 mt-2 w-40 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-lg py-1 z-10">
          {(['json', 'csv', 'pdf', 'docx'] as const).map((format) => (
            <button
              key={format}
              onClick={() => handleExport(format)}
              className={cn(
                'w-full flex items-center gap-2 px-4 py-2 text-sm text-left transition-colors',
                'text-slate-700 dark:text-slate-300',
                'hover:bg-slate-100 dark:hover:bg-slate-700',
                format === currentFormat && 'bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
              )}
            >
              {formatIcons[format]}
              <span className="uppercase">{format}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Update EssayPage to use ExportButton**

```tsx
// In EssayPage.tsx
import { ExportButton } from '@/components/ExportButton';

// Replace individual export links with ExportButton
<div className="flex gap-2 flex-wrap">
  <ExportButton report={report} currentFormat="json" />
</div>
```

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/exportToDocx.ts web/src/components/ExportButton.tsx
git commit -m "feat: add DOCX export for analysis reports"
```

---

## Task 8: Performance Optimization

**Files:**
- Modify: `web/src/router.tsx` (lazy load routes)
- Modify: `web/src/pages/*.tsx` (add React.memo where appropriate)
- Create: `web/src/components/SkeletonLoader.tsx`

**Interfaces:**
- Consumes: None
- Produces: Faster initial load, reduced re-renders

### Task 8: Performance Optimization

- [ ] **Step 1: Lazy load routes**

```tsx
// web/src/router.tsx
import { lazy, Suspense } from 'react';

// Lazy imports
const LandingPage = lazy(() => import('./pages/LandingPage').then(m => ({ default: m.LandingPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const UploadPage = lazy(() => import('./pages/UploadPage').then(m => ({ default: m.UploadPage })));
// ... other pages

// Wrap routes in Suspense
{
  path: '/dashboard',
  element: (
    <Suspense fallback={<PageLoader />}>
      <DashboardPage />
    </Suspense>
  ),
},
```

- [ ] **Step 2: Create SkeletonLoader component**

```tsx
// web/src/components/SkeletonLoader.tsx
export function PageLoader() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-10 w-48 bg-slate-200 dark:bg-slate-700 rounded-lg" />
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 bg-slate-200 dark:bg-slate-700 rounded-xl" />
        ))}
      </div>
      <div className="h-64 bg-slate-200 dark:bg-slate-700 rounded-xl" />
    </div>
  );
}
```

- [ ] **Step 3: Add memo to heavy components**

```tsx
// web/src/components/VerdictTable.tsx
import { memo } from 'react';

export const VerdictTable = memo(function VerdictTable({ ... }) {
  // existing code
});
```

Apply to: VerdictTable, CitationDetailDrawer, VerdictBadge, StatCard, ProcessingStep

- [ ] **Step 4: Optimize DashboardPage**

```tsx
// DashboardPage.tsx
import { memo, useMemo, useCallback } from 'react';

// Memoize filtered essays
const filteredEssays = useMemo(() => 
  essays.filter((essay) =>
    essay.filename.toLowerCase().includes(searchQuery.toLowerCase())
  ),
  [essays, searchQuery]
);

// Memoize delete handler
const handleDelete = useCallback(async (id: number) => {
  // ...
}, [toast]);
```

- [ ] **Step 5: Optimize EssayPage**

```tsx
// EssayPage.tsx
// Memoize derived data
const stats = useMemo(() => {
  const academicVerdicts = report.verdicts.filter((v) => !isUrlResource(v));
  return {
    total: academicVerdicts.length,
    verified: academicVerdicts.filter((v) => v.label === 'verified').length,
    // ...
  };
}, [report.verdicts]);

// Memoize handlers
const handleOverride = useCallback(async (verdict, req) => {
  // ...
}, [id, toast]);
```

- [ ] **Step 6: Commit**

```bash
git commit -m "perf: optimize rendering with lazy loading and memoization"
```

---

## Task 9: Help/Tutorial System

**Files:**
- Create: `web/src/components/HelpModal.tsx`
- Create: `web/src/components/KeyboardShortcuts.tsx`
- Create: `web/src/hooks/useKeyboardShortcuts.ts`
- Modify: `web/src/components/AppLayout.tsx` (add help button)

**Interfaces:**
- Consumes: None
- Produces: `HelpModal`, keyboard shortcuts

### Task 9: Help/Tutorial System

- [ ] **Step 1: Create useKeyboardShortcuts hook**

```tsx
// web/src/hooks/useKeyboardShortcuts.ts
import { useEffect, useCallback } from 'react';

interface Shortcut {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  action: () => void;
  description: string;
}

export function useKeyboardShortcuts(shortcuts: Shortcut[]) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      const shortcut = shortcuts.find(
        (s) =>
          s.key.toLowerCase() === event.key.toLowerCase() &&
          !!s.ctrl === (event.ctrlKey || event.metaKey) &&
          !!s.shift === event.shiftKey &&
          !!s.alt === event.altKey
      );

      if (shortcut) {
        event.preventDefault();
        shortcut.action();
      }
    },
    [shortcuts]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}
```

- [ ] **Step 2: Create HelpModal**

```tsx
// web/src/components/HelpModal.tsx
import { useState, useEffect } from 'react';
import { X, Search, Keyboard, Book, HelpCircle, ExternalLink } from 'lucide-react';
import { useI18n } from '@/contexts/I18nContext';
import { KeyboardShortcuts } from './KeyboardShortcuts';
import { cn } from '@/lib/utils';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const helpTopics = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    icon: Book,
    content: `
## Uploading Your First Document

1. Click **New Check** in the sidebar or dashboard
2. Drag and drop a PDF file or click to browse
3. Wait for the analysis to complete
4. Review your Citation Integrity Score (CIS)

## Understanding Verdicts

- **Verified** (green): Source confirmed in academic databases
- **Metadata Error** (yellow): Source found but details don't match
- **Suspected Hallucination** (red): Source not found, may be fabricated
- **Unresolved** (gray): Unable to verify due to limited information
    `,
  },
  {
    id: 'keyboard-shortcuts',
    title: 'Keyboard Shortcuts',
    icon: Keyboard,
    content: '',
    component: KeyboardShortcuts,
  },
  {
    id: 'about-cis',
    title: 'About CIS Score',
    icon: HelpCircle,
    content: `
## Citation Integrity Score (CIS)

The CIS score is a composite metric (0-100%) that indicates the overall reliability of citations in your document.

**Score Breakdown:**
- 90-100%: Excellent - Nearly all citations verified
- 70-89%: Good - Minor issues detected
- 50-69%: Warning - Several issues need attention
- Below 50%: Critical - Significant problems found

**Disclaimer:** This is a decision-support tool. All results should be reviewed by experts.
    `,
  },
];

export function HelpModal({ isOpen, onClose }: HelpModalProps) {
  const [activeTopic, setActiveTopic] = useState(helpTopics[0].id);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const activeTopicData = helpTopics.find((t) => t.id === activeTopic);
  const filteredTopics = helpTopics.filter((topic) =>
    topic.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-[200]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="absolute inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-full md:max-w-4xl md:max-h-[80vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
          <h2 className="font-display text-2xl font-bold text-slate-900 dark:text-slate-100">
            Help & Guide
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar */}
          <div className="w-64 border-r border-slate-200 dark:border-slate-700 p-4 overflow-y-auto">
            {/* Search */}
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search topics..."
                className="input pl-9 py-2 text-sm"
              />
            </div>

            {/* Topics */}
            <nav className="space-y-1">
              {filteredTopics.map((topic) => {
                const Icon = topic.icon;
                return (
                  <button
                    key={topic.id}
                    onClick={() => setActiveTopic(topic.id)}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-colors',
                      activeTopic === topic.id
                        ? 'bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                    )}
                  >
                    <Icon className="h-5 w-5 shrink-0" />
                    <span className="font-medium">{topic.title}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            {activeTopicData?.component ? (
              <activeTopicData.component />
            ) : (
              <div className="prose dark:prose-invert max-w-none">
                <div
                  dangerouslySetInnerHTML={{
                    __html: activeTopicData?.content
                      ?.replace(/^## /gm, '<h2 class="text-xl font-bold mt-6 mb-3">')
                      .replace(/^### /gm, '<h3 class="text-lg font-semibold mt-4 mb-2">')
                      .replace(/\n/g, '<br />')
                      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') || '',
                  }}
                />
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-700 text-center">
          <p className="text-sm text-slate-500">
            SourceLogic v1.11 - Academic Citation Verification
          </p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create KeyboardShortcuts component**

```tsx
// web/src/components/KeyboardShortcuts.tsx
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts';

const shortcuts = [
  { keys: ['N'], description: 'New upload' },
  { keys: ['D'], description: 'Go to dashboard' },
  { keys: ['?'], description: 'Open this help' },
  { keys: ['Esc'], description: 'Close modal/drawer' },
  { keys: ['T'], description: 'Toggle dark mode' },
];

export function KeyboardShortcuts() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Press <kbd className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded text-xs font-mono">?</kbd> anywhere to open this help.
      </p>

      <div className="space-y-2">
        {shortcuts.map((shortcut, i) => (
          <div key={i} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
            <span className="text-slate-700 dark:text-slate-300">{shortcut.description}</span>
            <div className="flex gap-1">
              {shortcut.keys.map((key) => (
                <kbd
                  key={key}
                  className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded text-xs font-mono text-slate-600 dark:text-slate-400"
                >
                  {key}
                </kbd>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Hook to register global shortcuts
export function useGlobalShortcuts(onHelpOpen: () => void, onNewUpload: () => void) {
  useKeyboardShortcuts([
    { key: '?', action: onHelpOpen, description: 'Open help' },
    { key: 'n', action: onNewUpload, description: 'New upload' },
    { key: 'd', action: () => window.location.href = '/dashboard', description: 'Dashboard' },
  ]);
}
```

- [ ] **Step 4: Add Help button to AppLayout**

```tsx
// AppLayout.tsx
import { HelpCircle } from 'lucide-react';
import { useState } from 'react';
import { HelpModal } from './HelpModal';

// In the sidebar header area, add:
const [showHelp, setShowHelp] = useState(false);

// Add help button near theme toggle
<button
  onClick={() => setShowHelp(true)}
  className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
  aria-label="Help"
>
  <HelpCircle className="h-5 w-5 text-slate-500" />
</button>

// Add modal at end of component
<HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
```

- [ ] **Step 5: Add help keyboard shortcut registration**

```tsx
// In AppLayout or a hook
useGlobalShortcuts(
  () => setShowHelp(true),
  () => navigate('/upload')
);
```

- [ ] **Step 6: Commit**

```bash
git add web/src/components/HelpModal.tsx web/src/components/KeyboardShortcuts.tsx web/src/hooks/useKeyboardShortcuts.ts
git commit -m "feat: add help modal and keyboard shortcuts"
```

---

## Summary

### Implementation Order

1. **Task 1** - React Error Boundaries (~30 min)
2. **Task 2** - Toast Notification System (~1 hour)
3. **Task 3** - Dark Mode (~1 hour)
4. **Task 4** - Internationalization (~2 hours)
5. **Task 5** - Settings Page (~1 hour)
6. **Task 6** - API Rate Limiting Awareness (~30 min)
7. **Task 7** - Export to DOCX (~1 hour)
8. **Task 8** - Performance Optimization (~30 min)
9. **Task 9** - Help/Tutorial System (~1 hour)

**Total estimated time: ~9 hours**

### Dependencies

- Task 3 (Dark Mode) depends on Task 2 (Toast)
- Task 4 (i18n) should be implemented before Task 5 (Settings)
- Task 6 (Rate Limiting) depends on Task 2 (Toast) for displaying warnings

### Testing Strategy

Each task includes unit tests. Integration tests should verify:
- Theme persistence across page reloads
- Language persistence across page reloads
- Toast queue management under rapid fire
- Error boundary isolation (one crash doesn't affect others)
