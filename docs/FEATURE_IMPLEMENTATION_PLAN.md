# Feature Implementation Plan — Essay Integrity Checker

**Version:** v1.12  
**Date:** 2026-01-XX  
**Status:** Planning  

---

## Executive Summary

Dựa trên nghiên cứu kỹ codebase, đây là plan chi tiết để implement các features "nice-to-have" cho dự án.

### Current Stack Analysis

| Component | Current State |
|-----------|---------------|
| **Frontend** | React 18 + TypeScript + Vite + Tailwind CSS |
| **Routing** | React Router v6 |
| **UI Library** | Radix UI + Lucide React |
| **Dark Mode** | Configured in Tailwind (`darkMode: ['class']`) nhưng CHƯA có toggle |
| **i18n** | NOT implemented |
| **Error Boundaries** | NOT implemented |
| **Toast System** | NOT implemented |
| **Settings Page** | NOT implemented |
| **Rate Limiting** | NOT implemented (backend) |
| **DOCX Export** | NOT implemented |
| **Tests** | 982 passed, 4 skipped (pytest + Playwright) |

---

## Priority 1: Must-Have Features

### 1. React Error Boundaries
**Time Estimate:** ~30 phút  
**Priority:** HIGH  
**Dependencies:** None  

#### Problem
- Runtime errors crash entire app
- API failures show raw error messages
- Component failures leave blank screens

#### Solution

**Create: `web/src/components/ErrorBoundary.tsx`**
```tsx
import { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);
    // TODO: Send to error tracking service
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <DefaultErrorFallback
          error={this.state.error}
          onReset={this.handleReset}
        />
      );
    }
    return this.props.children;
  }
}
```

**Files to Create:**
- `web/src/components/ErrorBoundary.tsx`

**Files to Modify:**
- `web/src/App.tsx` — Wrap with root error boundary
- `web/src/router.tsx` — Add per-route error boundaries
- Pages: DashboardPage, UploadPage, EssayPage, etc.

---

### 2. Toast Notification System
**Time Estimate:** ~1 giờ  
**Priority:** HIGH  
**Dependencies:** None  

#### Problem
- No feedback for user actions
- API errors shown inline
- Success messages don't persist

#### Solution

**Install Library:**
```bash
npm install react-hot-toast
```

**Files to Create:**
- `web/src/hooks/useToast.ts` — Wrapper around react-hot-toast

**Files to Modify:**
- `web/src/App.tsx` — Add `<Toaster />`
- All pages with API calls:
  - `DashboardPage.tsx` — Delete confirmation
  - `UploadPage.tsx` — Upload status
  - `ProfilePage.tsx` — Save feedback
  - `BatchUploadPage.tsx` — Batch status
  - `CitationDetailDrawer.tsx` — Override confirmation

**Usage Pattern:**
```tsx
import toast from 'react-hot-toast';

// Success
toast.success('Citation verified!');

// Error
toast.error('Upload failed', { duration: 6000 });

// With description
toast('Processing...', {
  icon: '⏳',
  duration: Infinity,
});
```

---

## Priority 2: Important Features

### 3. Dark Mode
**Time Estimate:** ~2 giờ  
**Priority:** HIGH  
**Dependencies:** None  

#### Current State
- Tailwind config: `darkMode: ['class']` ✓
- CSS variables defined ✓
- Dark variants in components: Partial (many `.dark .class` exist)
- No toggle component: **MISSING**
- No theme persistence: **MISSING**

#### Solution

**Step 1: Create Theme Context**

**Create: `web/src/contexts/ThemeContext.tsx`**
```tsx
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type Theme = 'light' | 'dark' | 'system';

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolvedTheme: 'light' | 'dark';
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    return (localStorage.getItem('theme') as Theme) || 'system';
  });

  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const root = window.document.documentElement;

    const applyTheme = (t: 'light' | 'dark') => {
      root.classList.remove('light', 'dark');
      root.classList.add(t);
      setResolvedTheme(t);
    };

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      applyTheme(mediaQuery.matches ? 'dark' : 'light');

      const handler = (e: MediaQueryListEvent) => {
        applyTheme(e.matches ? 'dark' : 'light');
      };
      mediaQuery.addEventListener('change', handler);
      return () => mediaQuery.removeEventListener('change', handler);
    } else {
      applyTheme(theme);
    }
  }, [theme]);

  const setTheme = (t: Theme) => {
    localStorage.setItem('theme', t);
    setThemeState(t);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, resolvedTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
}
```

**Step 2: Create Theme Toggle**

**Create: `web/src/components/ThemeToggle.tsx`**
```tsx
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const toggle = () => {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  };

  return (
    <button
      onClick={toggle}
      className="btn-ghost p-2"
      title={`Theme: ${theme}`}
    >
      {theme === 'dark' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
    </button>
  );
}
```

**Step 3: Integrate**

**Modify:**
- `web/src/App.tsx` — Add `<ThemeProvider>`
- `web/src/components/AppLayout.tsx` — Add `<ThemeToggle />` to sidebar

**Files to Create:**
- `web/src/contexts/ThemeContext.tsx`
- `web/src/components/ThemeToggle.tsx`

---

### 4. Settings Page
**Time Estimate:** ~2 giờ  
**Priority:** MEDIUM  
**Dependencies:** ThemeContext  

#### Solution

**Create: `web/src/pages/SettingsPage.tsx`**
```tsx
import { useTheme } from '@/contexts/ThemeContext';

export function SettingsPage() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="container-page py-8">
      <h1 className="text-headline mb-8">Settings</h1>

      <div className="max-w-2xl space-y-8">
        {/* Appearance */}
        <section className="card">
          <h2 className="text-lg font-semibold mb-4">Appearance</h2>

          <div className="space-y-4">
            <div>
              <label className="input-label">Theme</label>
              <div className="flex gap-2">
                {(['light', 'dark', 'system'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTheme(t)}
                    className={`btn-secondary ${theme === t ? 'btn-primary' : ''}`}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* About */}
        <section className="card">
          <h2 className="text-lg font-semibold mb-4">About</h2>
          <p className="text-muted-foreground">Version: 1.11</p>
        </section>
      </div>
    </div>
  );
}
```

**Modify:**
- `web/src/router.tsx` — Add `/settings` route
- `web/src/components/AppLayout.tsx` — Add Settings link

**Files to Create:**
- `web/src/pages/SettingsPage.tsx`

---

### 5. Internationalization (VI/EN)
**Time Estimate:** ~4 giờ  
**Priority:** MEDIUM  
**Dependencies:** Settings Page (for language selector)  

#### Solution

**Step 1: Install Dependencies**
```bash
npm install react-i18next i18next
```

**Step 2: Create i18n Structure**

**Create: `web/src/i18n/index.ts`**
```typescript
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import vi from './locales/vi.json';

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    vi: { translation: vi },
  },
  lng: localStorage.getItem('language') || 'en',
  fallbackLng: 'en',
});

export default i18n;
```

**Create: `web/src/i18n/locales/en.json`**
```json
{
  "nav": {
    "dashboard": "Dashboard",
    "upload": "New Check",
    "history": "History",
    "settings": "Settings"
  },
  "verdict": {
    "verified": "Verified",
    "metadata_error": "Needs Review",
    "suspected_hallucination": "Suspected Hallucination",
    "unresolved": "Unresolved"
  },
  "action": {
    "upload": "Upload PDF",
    "delete": "Delete",
    "save": "Save Changes",
    "cancel": "Cancel"
  },
  "status": {
    "loading": "Loading...",
    "processing": "Processing...",
    "success": "Success",
    "error": "Error"
  }
}
```

**Create: `web/src/i18n/locales/vi.json`**
```json
{
  "nav": {
    "dashboard": "Bảng điều khiển",
    "upload": "Kiểm tra mới",
    "history": "Lịch sử",
    "settings": "Cài đặt"
  },
  "verdict": {
    "verified": "Đã xác minh",
    "metadata_error": "Cần xem xét",
    "suspected_hallucination": "Nghi ngờ bịa đặt",
    "unresolved": "Chưa giải quyết"
  },
  "action": {
    "upload": "Tải lên PDF",
    "delete": "Xóa",
    "save": "Lưu thay đổi",
    "cancel": "Hủy"
  },
  "status": {
    "loading": "Đang tải...",
    "processing": "Đang xử lý...",
    "success": "Thành công",
    "error": "Lỗi"
  }
}
```

**Step 3: Create Language Selector**

**Create: `web/src/components/LanguageSelector.tsx`**
```tsx
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';

export function LanguageSelector() {
  const { i18n } = useTranslation();

  const toggle = () => {
    const next = i18n.language === 'en' ? 'vi' : 'en';
    i18n.changeLanguage(next);
    localStorage.setItem('language', next);
  };

  return (
    <button onClick={toggle} className="btn-ghost p-2" title="Toggle language">
      <Globe className="w-5 h-5" />
      <span className="text-xs ml-1">{i18n.language.toUpperCase()}</span>
    </button>
  );
}
```

**Step 4: Update Components**

Replace hardcoded text with `t('key')`:
- `AppLayout.tsx` — Navigation labels
- `DashboardPage.tsx` — Page content
- `VerdictBadge.tsx` — Status labels
- All page components

**Files to Create:**
- `web/src/i18n/index.ts`
- `web/src/i18n/locales/en.json`
- `web/src/i18n/locales/vi.json`
- `web/src/components/LanguageSelector.tsx`

**Files to Modify:**
- `web/src/main.tsx` — Import i18n
- Multiple page components

---

## Priority 3: Nice-to-Have Features

### 6. API Rate Limiting (Backend)
**Time Estimate:** ~2 giờ  
**Priority:** MEDIUM  
**Dependencies:** Toast System  

#### Solution

**Backend: Create Rate Limit Middleware**

**Create: `src/integrity_checker/api/middleware/rate_limit.py`**
```python
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = datetime.now()

        # Clean old requests
        self.requests[client_ip] = [
            t for t in self.requests[client_ip]
            if now - t < timedelta(minutes=1)
        ]

        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a minute."
            )

        self.requests[client_ip].append(now)
        return await call_next(request)
```

**Modify:**
- `src/integrity_checker/api/main.py` — Add middleware

**Frontend: Handle 429 Responses**

**Modify: `web/src/hooks/useToast.ts`**
```typescript
// Add rate limit handling
export function useApiError() {
  const toast = useToast();

  const handleError = (error: unknown) => {
    if (error instanceof Response && error.status === 429) {
      toast.error('Too many requests. Please wait a minute.');
      return;
    }
    // ... handle other errors
  };

  return { handleError };
}
```

---

### 7. Export to DOCX
**Time Estimate:** ~3 giờ  
**Priority:** LOW  
**Dependencies:** None  

#### Solution

**Backend: Add python-docx Endpoint**

**Install:**
```bash
pip install python-docx
```

**Create: `src/integrity_checker/api/routes/export.py`**
```python
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from docx import Document
from docx.shared import Inches, RGBColor
import io

router = APIRouter(prefix="/export", tags=["export"])

@router.get("/report/{essay_id}/docx")
async def export_report_docx(essay_id: int, token: str = Depends(get_current_user)):
    # Fetch essay data
    essay = await get_essay(essay_id, token)

    # Generate DOCX
    doc = Document()
    doc.add_heading('Essay Verification Report', 0)
    doc.add_paragraph(f"Document: {essay.filename}")
    doc.add_paragraph(f"CIS Score: {essay.cis_score}%")

    # Add verdicts table
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Citation'
    hdr_cells[1].text = 'Status'
    hdr_cells[2].text = 'Details'

    for verdict in essay.verdicts:
        row_cells = table.add_row().cells
        row_cells[0].text = verdict.citation_text
        row_cells[1].text = verdict.label
        row_cells[2].text = verdict.message or ""

    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=report_{essay_id}.docx"}
    )
```

**Modify:**
- `src/integrity_checker/api/main.py` — Include export router

**Frontend: Export Menu**

**Create: `web/src/components/ExportMenu.tsx`**
```tsx
import { Download } from 'lucide-react';

export function ExportMenu({ essayId }: { essayId: number }) {
  const downloadDocx = async () => {
    const response = await fetch(`/api/export/report/${essayId}/docx`);
    const blob = await response.blob();
    // ... trigger download
  };

  return (
    <button onClick={downloadDocx} className="btn-primary">
      <Download className="w-4 h-4" />
      Export DOCX
    </button>
  );
}
```

---

### 8. Performance Optimization
**Time Estimate:** ~4 giờ  
**Priority:** LOW  
**Dependencies:** None  

#### Solution

**Step 1: Route-based Code Splitting**

**Modify: `web/src/router.tsx`**
```tsx
import { lazy, Suspense } from 'react';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const EssayPage = lazy(() => import('./pages/EssayPage'));
// ... other pages

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full" />
    </div>
  );
}

// Wrap routes in <Suspense fallback={<LoadingFallback />}>
```

**Step 2: Memoize Expensive Components**

**Modify: `web/src/components/VerdictBadge.tsx`**
```tsx
import { memo } from 'react';

export const VerdictBadge = memo(function VerdictBadge({ status }: { status: string }) {
  return <span className={`verdict-badge-${status}`}>{status}</span>;
});
```

**Step 3: Virtualize Large Lists**

**Install:**
```bash
npm install @tanstack/react-virtual
```

**Modify: `web/src/components/VerdictTable.tsx`**
```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

function VerdictTable({ verdicts }: { verdicts: Verdict[] }) {
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: verdicts.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
  });

  return (
    <div ref={parentRef} className="h-[600px] overflow-auto">
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((virtual) => (
          <div
            key={virtual.index}
            style={{
              position: 'absolute',
              top: virtual.start,
              height: virtual.size,
            }}
          >
            <VerdictRow verdict={verdicts[virtual.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### 9. Help/Tutorial
**Time Estimate:** ~4 giờ  
**Priority:** LOW  
**Dependencies:** i18n (for localized help)  

#### Solution

**Step 1: Create Help Modal**

**Create: `web/src/components/HelpModal.tsx`**
```tsx
import { HelpCircle, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export function HelpModal() {
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();

  return (
    <>
      <button onClick={() => setIsOpen(true)} className="btn-ghost p-2">
        <HelpCircle className="w-5 h-5" />
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setIsOpen(false)} />
          <div className="relative bg-white dark:bg-slate-900 rounded-2xl p-8 max-w-2xl max-h-[80vh] overflow-auto">
            <button onClick={() => setIsOpen(false)} className="absolute top-4 right-4">
              <X className="w-5 h-5" />
            </button>
            <h2 className="text-2xl font-bold mb-4">{t('help.title')}</h2>
            {/* Help content */}
          </div>
        </div>
      )}
    </>
  );
}
```

**Step 2: Create Tutorial Steps**

**Create: `web/src/i18n/locales/help-en.json`**
```json
{
  "tutorial": {
    "welcome": {
      "title": "Welcome to Essay Integrity Checker",
      "content": "This tool helps verify citations in academic papers..."
    },
    "upload": {
      "title": "Upload Your Essay",
      "content": "Drag and drop a PDF file or click to browse..."
    }
  }
}
```

---

## Implementation Order

| # | Feature | Priority | Time | Dependencies | Week |
|---|---------|----------|------|--------------|------|
| 1 | Error Boundaries | HIGH | 30m | None | 1 |
| 2 | Toast System | HIGH | 1h | None | 1 |
| 3 | Dark Mode | HIGH | 2h | None | 1 |
| 4 | Settings Page | MEDIUM | 2h | ThemeContext | 2 |
| 5 | i18n (VI/EN) | MEDIUM | 4h | Settings | 2 |
| 6 | Rate Limiting | MEDIUM | 2h | Toast | 2 |
| 7 | Export DOCX | LOW | 3h | Toast | 3 |
| 8 | Performance | LOW | 4h | None | 3 |
| 9 | Help/Tutorial | LOW | 4h | i18n | 4 |

**Total Estimated:** ~23 giờ (~4 tuần)

---

## File Structure After Implementation

```
web/src/
├── components/
│   ├── ui/
│   │   └── Toast.tsx              # [EXISTING - may add wrapper]
│   ├── ErrorBoundary.tsx          # NEW
│   ├── ThemeToggle.tsx            # NEW
│   ├── LanguageSelector.tsx       # NEW
│   ├── ExportMenu.tsx            # NEW
│   └── HelpModal.tsx             # NEW
├── contexts/
│   ├── ThemeContext.tsx           # NEW
│   └── AuthContext.tsx            # [EXISTING]
├── hooks/
│   ├── useToast.ts                # NEW
│   └── useApiError.ts            # NEW
├── i18n/
│   ├── index.ts                  # NEW
│   └── locales/
│       ├── en.json               # NEW
│       └── vi.json               # NEW
└── pages/
    ├── SettingsPage.tsx           # NEW
    └── HelpPage.tsx              # NEW

src/integrity_checker/api/
├── middleware/
│   └── rate_limit.py             # NEW
└── routes/
    └── export.py                  # NEW
```

---

## Recommended Next Steps

1. **Start immediately:** Error Boundaries + Toast System (foundation for good UX)
2. **Next sprint:** Dark Mode (quick win, high impact)
3. **After that:** Settings Page + i18n (complete localization)
4. **Future:** Rate Limiting + DOCX Export (polish)
5. **Nice-to-have:** Performance + Help (low priority)

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Toast Library | `react-hot-toast` | Simple API, good defaults, customizable |
| i18n Library | `react-i18next` | Industry standard, good TypeScript support |
| Dark Mode | CSS class strategy | Already configured in Tailwind |
| DOCX Generation | Server-side | Better performance, consistent formatting |
| Rate Limiting | In-memory (production: Redis) | Simple for single-instance deployment |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Dark mode incomplete | Medium | Audit all components before shipping |
| i18n missing keys | Low | Add fallback to English |
| Rate limiting too strict | Medium | Make configurable via config.yaml |
| DOCX formatting issues | Low | Test with multiple templates |

---

*Last Updated: 2026-01-XX*
