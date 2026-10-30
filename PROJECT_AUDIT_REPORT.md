# MedPaperPulse AI — Project Audit Report

_Generated: 2026-10-30_

---

## Framework & Entry Points

| Layer | Technology | Entry Point |
|---|---|---|
| Backend | FastAPI 0.162.0 + Uvicorn 0.54.0 | `main.py` |
| Frontend | React 18 + TypeScript + Vite 6 | `frontend/src/main.tsx` |
| Python | 3.14.0 (venv at `.venv/`) | — |
| Node.js | v26.13.0 (at `C:\Program Files\nodejs\`) | — |

---

## How to Run (Windows PowerShell)

### Backend

```powershell
# Activate venv (once per terminal session)
.\.venv\Scripts\Activate.ps1

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
python main.py
# → Uvicorn on http://localhost:8000
# → API docs at http://localhost:8000/docs
```

### Frontend

```powershell
# Add Node.js to PATH (once per terminal session, if node is not found)
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH

cd frontend
npm install
npm run dev
# → Vite dev server on http://localhost:5173
```

> **Note:** Node.js v26.13.0 is installed at `C:\Program Files\nodejs\` but may not be on
> your default PATH. Add it permanently via: **System Properties → Environment Variables →
> Path → New → `C:\Program Files\nodejs`**.

---

## Errors Found and Fixed

### This Session

| # | File | Error | Fix |
|---|---|---|---|
| 1 | `frontend/src/api.ts` | 12 duplicate `const res = await fetch(...)` lines left over from a previous refactor — TypeScript reported "Expected ':' but found 'res'" | Removed all 12 stale `fetch(${API_BASE_URL}/...)` lines; each function now uses `safeFetch()` correctly |
| 2 | `frontend/src/lib/utils.ts` | File missing — `ErrorBoundary.tsx` imported `@/lib/utils` (the standard Shadcn `cn()` helper) which did not exist | Created `src/lib/utils.ts` exporting `cn()` using the project's existing `clsx` + `tailwind-merge` deps |

### Prior Sessions (carried forward)

| Area | Fix |
|---|---|
| `comparator.py` | Case-insensitive key lookup for conflict detection |
| `cache.py` | Replaced memory-only stub with full SQLiteCache |
| `xml_parser.py` | Used `itertext()`, added proper error propagation |
| `sentence_tagger.py` | Fixed abbreviation masking (et al., vs.) |
| `paste_parser.py` | Word-boundary PICO truncation |
| `eval/*.py` | TestClient fallback for offline testing |
| `main.py` | Added root `GET /` endpoint |
| `requirements.txt` | Added `pytest>=8.0.0` |
| `pytest.ini` | Created for test discovery config |
| `.gitignore` | Added `*.db` entries for SQLite files |

---

## Test Results

### Backend — pytest

```
87 passed, 1 warning in 5.43s
```

**PASS** — All 87 tests pass (75 in `tests/`, 12 in `eval/`).

> Warning: `starlette.testclient` deprecation (use `httpx2`). Non-breaking; no fix required now.

### Frontend — Vite production build

```
vite v6.4.5 building for production...
✓ 1594 modules transformed.
dist/index.html                   0.78 kB │ gzip:  0.45 kB
dist/assets/index-*.css          29.48 kB │ gzip:  7.38 kB
dist/assets/index-*.js          235.16 kB │ gzip: 72.21 kB
✓ built in 2.96s
```

**PASS** — Production build succeeds with zero errors.

### Frontend — TypeScript strict check (`tsc --noEmit`)

**PARTIAL** — `tsc --noEmit` on the entire `src/` directory reports many missing-module errors in unused Shadcn/ui component files (`src/components/ui/*`, `src/_core/`, `src/pages/ComponentShowcase.tsx`, etc.) that have extra deps not listed in `package.json`. **These files are not imported by the application** (`Home.tsx` only imports `react`; `App.tsx` only imports `Home` and `ErrorBoundary`). The build succeeds and the app runs correctly. The extra component files appear to be scaffolding carried over from a template that was not removed.

---

## Files Changed (This Session)

| File | Change |
|---|---|
| `frontend/src/api.ts` | Removed 12 duplicate `fetch(${API_BASE_URL}/...)` lines |
| `frontend/src/lib/utils.ts` | **Created** — standard `cn()` utility (clsx + tailwind-merge) |
| `PROJECT_AUDIT_REPORT.md` | This file |

---

## Remaining Issues

| Issue | Severity | Status |
|---|---|---|
| Many unused component files (`src/components/ui/*`, `src/_core/`, etc.) have missing npm deps (`@radix-ui/*`, `wouter`, `recharts`, `@trpc/client`, etc.) causing `tsc --noEmit` failures | Low — files unused by the app | OPEN (clean-up task, not a blocker) |
| `starlette.testclient` deprecation warning — install `httpx2` | Very Low | OPEN |
| No API keys configured in `.env` — AI features run in offline/deterministic mode | Informational | OPEN (requires user's API key) |
| Node.js not on default PATH — must prepend manually each session | Low | OPEN (one-time system PATH setting) |

---

## Security Summary

- No secrets, API keys, tokens, or credentials are present in source files or committed to version control.
- `.env` is excluded from Git via `.gitignore`.
- SQLite database files (`*.db`) are excluded from Git.
- Backend validates all inputs; no obvious injection vectors identified.
- No public ports, telemetry, or external integrations beyond the configured AI API.
- **Recommended:** Set API keys via `.env` only (already the existing pattern). Never hardcode.
