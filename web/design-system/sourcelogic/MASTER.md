# SourceLogic Design System — Master

> **LOGIC:** When building a specific page, first check `pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** SourceLogic — Academic Source Verification Workspace
**Generated:** 2026-09-25
**Based on:** UX/UI Concept Specification v1.0

---

## Product Vision

"Academic Source Verification Workspace" — not an essay grader.
Mental model: "Debugger for citations"

---

## Color Palette

| Role | Hex | CSS Variable | Usage |
|------|-----|--------------|-------|
| Background | `#F8FAFC` | `--bg` | Page background |
| Surface | `#FFFFFF` | `--surface` | Cards, panels |
| Text Primary | `#0F172A` | `--text` | Headlines, body |
| Text Muted | `#64748B` | `--muted` | Secondary text |
| Border | `#E2E8F0` | `--border` | Dividers, outlines |
| Primary | `#4F46E5` | `--primary` | Actions, links |
| Verified | `#10B981` | `--verified` | VERIFIED status |
| Metadata Warning | `#F59E0B` | `--warning` | METADATA_ERROR |
| Source Mismatch | `#F97316` | `--mismatch` | SOURCE_MISMATCH |
| Hallucinated | `#EF4444` | `--danger` | HALLUCINATED |
| Unverifiable | `#94A3B8` | `--unknown` | UNVERIFIABLE |

**Dark Mode:** Use `dark:` prefix with slate-900/800 variants

---

## Typography

- **Heading Font:** Source Serif 4 (serif for academic feel)
- **Body Font:** Inter (clean UI font)
- **Monospace:** For code, IDs, technical data

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&display=swap');
```

```css
font-family: 'Inter', system-ui, -apple-system, sans-serif; /* UI */
font-family: 'Source Serif 4', Georgia, serif; /* Headlines */
```

---

## Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px | Tight gaps |
| `--space-sm` | 8px | Icon gaps |
| `--space-md` | 16px | Standard padding |
| `--space-lg` | 24px | Section padding |
| `--space-xl` | 32px | Large gaps |
| `--space-2xl` | 48px | Page margins |

---

## Component Specs

### Cards

```css
.card {
  background: white;
  border: 1px solid #E2E8F0;
  border-radius: 18px;
  padding: 22px;
}

.dark .card {
  background: #0F172A;
  border-color: #1E293B;
}
```

### Buttons

```css
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: #4F46E5;
  color: white;
  border-radius: 12px;
  font-weight: 600;
  transition: all 200ms ease;
}

.btn-primary:hover {
  background: #4338CA;
  box-shadow: 0 4px 6px rgba(79, 70, 229, 0.2);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: #F1F5F9;
  color: #0F172A;
  border-radius: 12px;
  font-weight: 600;
  transition: all 200ms ease;
}
```

### Badges

```css
.verdict-badge {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.verified { background: #ECFDF5; color: #047857; }
.metadata-error { background: #FFFBEB; color: #B45309; }
.hallucinated { background: #FEF2F2; color: #B91C1C; }
.unverifiable { background: #F1F5F9; color: #475569; }
```

### Dropzone

```css
.dropzone {
  border: 2px dashed #CBD5E1;
  border-radius: 18px;
  padding: 64px;
  text-align: center;
  transition: all 200ms ease;
}

.dropzone:hover {
  border-color: #818CF8;
  background: #EEF2FF;
}
```

### Pipeline Steps

```css
.pipeline-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
}

.pipeline-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

---

## Shadows

| Level | Value |
|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.03)` |
| `--shadow` | `0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.05)` |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.05)` |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.05)` |

---

## Icons (Lucide React)

Use Lucide React icons throughout:
- Document/File: `FileText`
- Verification: `Shield`, `CheckCircle`
- Warnings: `AlertTriangle`, `AlertCircle`
- Errors: `XCircle`
- Navigation: `ChevronRight`, `ChevronDown`
- Actions: `Upload`, `Download`, `Search`
- Data: `Database`, `Link`, `GitBranch`

**NO emojis as icons**

---

## Anti-Patterns (Do NOT Use)

- ❌ AI-style visuals: robots, brains, sparkles, heavy gradients
- ❌ "Integrity Score 82/100" without scientific definition
- ❌ Essay/Grammar/Writing Quality concepts (not the product scope)
- ❌ Emojis as icons
- ❌ Missing cursor:pointer on clickables
- ❌ Instant state changes (no transitions)
- ❌ Low contrast text (< 4.5:1)

---

## Pre-Delivery Checklist

- [ ] No emojis used as icons
- [ ] All icons from Lucide React
- [ ] cursor-pointer on all clickables
- [ ] Hover states with 200ms transitions
- [ ] Light mode contrast 4.5:1 minimum
- [ ] Dark mode supported
- [ ] Responsive: 375px, 768px, 1024px
- [ ] No horizontal scroll
