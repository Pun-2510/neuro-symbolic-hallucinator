# Web Frontend — Essay Integrity Checker

React + Vite + TypeScript + Tailwind CSS + shadcn/ui.

## Quick start

```bash
cd web
npm install
npm run dev
# → http://localhost:5173
```

Build production:

```bash
npm run build
```

### Vite dev cache (504 "Outdated Optimize Dep")

After restarting the Vite dev server, navigating directly to `/verification/report/:id`
(EssayPage) or any other lazy-loaded page may briefly throw
`Failed to fetch dynamically imported module`. This is Vite's pre-bundling cache
going stale — it resolves itself once you visit any other page first.

If you hit it persistently, clear the cache:

```bash
npm run dev:clean    # = rm -rf node_modules/.vite && vite
```

## Stack

- **React 18** + **TypeScript** + **Vite 5**
- **Tailwind CSS** — utility-first CSS
- **shadcn/ui** — accessible primitives (Button, Table, Dialog, Card...)
- **react-router-dom** — routing
- **lucide-react** — icons
- **clsx + tailwind-merge** — className helper

## Cấu trúc

```
web/src/
├── api/client.ts         # fetch wrapper + types (match backend Pydantic)
├── components/
│   ├── ui/               # shadcn-generated (Button, Card, Table, ...)
│   ├── DecisionSupportDisclaimer.tsx   # BẮT BUỘC trên mọi page
│   ├── VerdictBadge.tsx  # 4 màu cho 4 nhãn
│   ├── UploadDropzone.tsx
│   ├── VerdictTable.tsx
│   ├── CISScoreCard.tsx
│   └── ...
├── pages/
│   ├── UploadPage.tsx    # Upload PDF
│   ├── EssayPage.tsx     # Xem verdict + CIS
│   └── HistoryPage.tsx   # Lịch sử các essay đã upload
├── hooks/
│   └── useEssayAnalysis.ts
├── lib/utils.ts          # cn() helper
├── App.tsx
├── router.tsx
└── main.tsx
```

## ⚠️ Decision-support disclaimer

**Mọi page** PHẢI có `<DecisionSupportDisclaimer />` ở header. Component này lấy text từ backend `/api/health` endpoint (disclaimer.short + disclaimer.long).

## Env

```bash
# web/.env.local
VITE_API_BASE_URL=http://localhost:8000
```

Xem `.env.example`.

## Quyết định cốt lõi (UI phải hiện rõ)

- Citation-only — KHÔNG chấm điểm toàn bài tiểu luận.
- CIS = Citation Integrity Score, KHÔNG phải điểm tổng bài.
- 4 nhãn: verified / metadata_error / suspected_hallucination / unresolved.
- Hệ thống là decision-support — giảng viên là người quyết định cuối.