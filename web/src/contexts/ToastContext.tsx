/**
 * Toast Context & Provider
 * Global toast notification system using React Context
 */
import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  X,
  Loader2,
} from 'lucide-react';

// ============================================================
// Types
// ============================================================

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'loading';

export interface Toast {
  id: string;
  type: ToastType;
  title?: string;
  message?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  createdAt: number;
}

export interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id' | 'createdAt'>) => string;
  removeToast: (id: string) => void;
  dismissAll: () => void;
  // Convenience methods
  success: (title: string, message?: string, options?: Partial<Toast>) => string;
  error: (title: string, message?: string, options?: Partial<Toast>) => string;
  warning: (title: string, message?: string, options?: Partial<Toast>) => string;
  info: (title: string, message?: string, options?: Partial<Toast>) => string;
  loading: (title: string, message?: string) => string;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

// ============================================================
// Default durations (ms)
const DEFAULT_DURATION = 5000;
const LOADING_DURATION = Infinity;

// ============================================================
// Provider Component
// ============================================================

interface ToastProviderProps {
  children: ReactNode;
  /** Position of toast container */
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
  /** Max toasts to show */
  maxToasts?: number;
}

export function ToastProvider({
  children,
  position = 'bottom-right',
  maxToasts = 5,
}: ToastProviderProps): ReactNode {
  const [toasts, setToasts] = useState<Toast[]>([]);

  // Generate unique ID
  const generateId = () => `toast-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

  // Add toast
  const addToast = useCallback(
    (toast: Omit<Toast, 'id' | 'createdAt'>): string => {
      const id = generateId();
      const newToast: Toast = {
        ...toast,
        id,
        createdAt: Date.now(),
        duration: toast.duration ?? (toast.type === 'loading' ? LOADING_DURATION : DEFAULT_DURATION),
      };

      setToasts((prev) => {
        // Limit max toasts
        const updated = [newToast, ...prev];
        return updated.slice(0, maxToasts);
      });

      // Auto-dismiss (except loading)
      if (newToast.duration !== Infinity) {
        setTimeout(() => {
          setToasts((prev) => prev.filter((t) => t.id !== id));
        }, newToast.duration);
      }

      return id;
    },
    [maxToasts]
  );

  // Remove toast
  const removeToast = useCallback((id: string): void => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Dismiss all
  const dismissAll = useCallback((): void => {
    setToasts([]);
  }, []);

  // Convenience methods
  const success = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) =>
      addToast({ type: 'success', title, message, ...options }),
    [addToast]
  );

  const error = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) =>
      addToast({ type: 'error', title, message, ...options }),
    [addToast]
  );

  const warning = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) =>
      addToast({ type: 'warning', title, message, ...options }),
    [addToast]
  );

  const info = useCallback(
    (title: string, message?: string, options?: Partial<Toast>) =>
      addToast({ type: 'info', title, message, ...options }),
    [addToast]
  );

  const loading = useCallback(
    (title: string, message?: string) =>
      addToast({ type: 'loading', title, message }),
    [addToast]
  );

  const value: ToastContextValue = {
    toasts,
    addToast,
    removeToast,
    dismissAll,
    success,
    error,
    warning,
    info,
    loading,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} position={position} />
    </ToastContext.Provider>
  );
}

// ============================================================
// Hook
// ============================================================

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

// Convenience hooks
export const useSuccessToast = () => {
  const { success } = useToast();
  return success;
};

export const useErrorToast = () => {
  const { error } = useToast();
  return error;
};

// ============================================================
// Toast Container Component
// ============================================================

interface ToastContainerProps {
  toasts: Toast[];
  onRemove: (id: string) => void;
  position: ToastProviderProps['position'];
}

function ToastContainer({ toasts, onRemove, position = 'bottom-right' }: ToastContainerProps): ReactNode {
  const positionClasses: Record<NonNullable<ToastProviderProps['position']>, string> = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-center': 'top-4 left-1/2 -translate-x-1/2',
    'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
  };

  return (
    <div
      className={`fixed ${positionClasses[position]} z-[100] flex flex-col gap-2 pointer-events-none`}
      aria-live="polite"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
}

// ============================================================
// Individual Toast Component
// ============================================================

interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}

function ToastItem({ toast, onRemove }: ToastItemProps): ReactNode {
  const icons: Record<ToastType, ReactNode> = {
    success: <CheckCircle className="w-5 h-5 text-emerald-500" />,
    error: <XCircle className="w-5 h-5 text-red-500" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />,
    loading: <Loader2 className="w-5 h-5 text-slate-500 animate-spin" />,
  };

  const bgColors: Record<ToastType, string> = {
    success: 'bg-emerald-50 dark:bg-emerald-900/30 border-emerald-200 dark:border-emerald-800',
    error: 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800',
    warning: 'bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800',
    info: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800',
    loading: 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700',
  };

  const textColors: Record<ToastType, string> = {
    success: 'text-emerald-800 dark:text-emerald-200',
    error: 'text-red-800 dark:text-red-200',
    warning: 'text-amber-800 dark:text-amber-200',
    info: 'text-blue-800 dark:text-blue-200',
    loading: 'text-slate-700 dark:text-slate-300',
  };

  return (
    <div
      className={`
        pointer-events-auto flex items-start gap-3 p-4 rounded-xl border shadow-lg
        min-w-[320px] max-w-md
        animate-slide-up
        ${bgColors[toast.type]}
      `}
      role="alert"
    >
      <div className="shrink-0 mt-0.5">{icons[toast.type]}</div>
      <div className="flex-1 min-w-0">
        {toast.title && (
          <p className={`font-medium text-sm ${textColors[toast.type]}`}>
            {toast.title}
          </p>
        )}
        {toast.message && (
          <p className={`text-sm mt-0.5 ${textColors[toast.type]} opacity-80`}>
            {toast.message}
          </p>
        )}
        {toast.action && (
          <button
            onClick={toast.action.onClick}
            className={`mt-2 text-sm font-medium ${textColors[toast.type]} hover:underline`}
          >
            {toast.action.label}
          </button>
        )}
      </div>
      <button
        onClick={() => onRemove(toast.id)}
        className={`shrink-0 p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 ${textColors[toast.type]} opacity-60 hover:opacity-100 transition-opacity`}
        aria-label="Dismiss notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export default ToastProvider;
