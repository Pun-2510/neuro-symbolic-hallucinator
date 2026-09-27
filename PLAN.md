# Plan — Fix ProcessingScreen + matched_sources bug

## Context

There are two production-blocking bugs in the essay upload → report flow:

1. **ProcessingScreen không hoạt động.** `POST /api/essays` is currently a **synchronous** handler: it calls `pipeline.run()` inside `loop.run_in_executor`, waits for the full analysis (PDF parse → retrieval → rules → CIS) to complete, then returns. For a 16-page BERT paper this can take 20-60+ seconds (Crossref/OpenAlex/S2/CORE calls in parallel). During that time the user sees only a tiny button-level spinner on the Upload page. The dedicated ProcessingScreen route (`/verification/processing/:id`) only mounts *after* upload finishes, so the rich "Verification Pipeline" stepper UI never appears during the long wait.
2. **`verdict.matched_sources is not iterable` crash.** The frontend `Verdict` interface in `web/src/api/client.ts:105` declares `matched_sources: MatchedSource[]` (required), and `CitationGraphView`/`ProcessingPage` call `.some()`, `.filter(...).length` on it. But the backend **never serializes `matched_sources`** into the report payload — `report.py:114-132` builds the verdict dict without that key, so the JSON omits it and JS receives `undefined`. This breaks the Evidence Graph and the "Source Retrieval" counters on the Processing page.

The user wants:
- ProcessingScreen to appear immediately on click, with **real** progress pulled from the backend (no fake data, no fake timers).
- The `matched_sources` bug to be completely gone.

## Approach

### Backend

**1. In-memory progress tracker** — `src/integrity_checker/api/progress.py` (new).

Module-level dict keyed by `essay_id` storing a `ProgressState` dataclass:
```python
@dataclass
class ProgressState:
    status: str                     # "queued" | "processing" | "completed" | "failed"
    step: str                       # "parsing" | "extracting" | "linking" | "retrieving" | "checking" | "scoring" | "done"
    step_index: int                 # 0..7
    total_steps: int                # 8
    message: str
    citations_found: int = 0
    references_found: int = 0
    linked: int = 0
    sources_queried: dict[str, str] = field(default_factory=dict)  # crossref: "ok" | "failed: 429" | "pending"
    started_at: float
    finished_at: float | None = None
    error: str | None = None
```

Expose `get(essay_id)`, `set(essay_id, **kwargs)`, `clear(essay_id)`, `snapshot(essay_id) -> dict`.

**2. Async upload** — `src/integrity_checker/api/routes/essays.py`.

Refactor `upload_essay`:
- Read file, save to tempdir, validate PDF.
- Create the `EssayRecord` row immediately with `filename`, `num_pages=0`, `user_id`.
- Initialize `ProgressState(status="processing", step="parsing", step_index=0, started_at=time.time())`.
- Schedule background work via FastAPI's `BackgroundTasks` (already injected by FastAPI): `background_tasks.add_task(_run_pipeline_task, essay_id, tmp_path, user_id)`.
- Return `EssayUploadResponse` immediately with the real `essay_id`. No more waiting.
- Move all pipeline → DB write logic into a private async helper `_run_pipeline_task(essay_id, tmp_path, user_id)` that:
  - Updates `ProgressState` at each step (parsing → extracting → linking → retrieving → checking → scoring → done).
  - Calls `pipeline.run_async(pdf_path, essay_id)`.
  - **With small refactors to `IntegrityPipeline.run_async`** (see #4) so it reports progress.
  - Persists citations + verdicts + style_profile + cis on completion.
  - Sets `ProgressState.status = "completed"` (or `"failed"` with error).
  - Cleans up the temp file.

**3. New status endpoint** — `src/integrity_checker/api/routes/essays.py`.

```python
@router.get("/{essay_id}/status")
def get_essay_status(essay_id: int, ...):
    state = progress.get(essay_id)
    if state is None:
        # Fallback: check DB — if essay exists with verdicts, it's done
        essay = repo.get_essay(essay_id)
        if essay and repo.get_verdicts(essay_id):
            return {"status": "completed", "step": "done", ...}
        raise HTTPException(404)
    return progress.snapshot(essay_id)
```

Also adjust `GET /essays/{id}/report` (`report.py`) to return **HTTP 425 (Too Early)** with a `Retry-After` header when status is still `processing`, so the frontend's `getEssay` call on the Processing page gets a clear signal to keep polling instead of failing silently.

**4. Plumb progress into the pipeline** — `src/integrity_checker/pipeline/integrity_pipeline.py`.

Add an optional `progress_callback: Callable[[str, int, dict], None] | None = None` parameter to `run_async`. The 8 steps already exist (matching `ProcessingPage.steps`), so the callback fires at each natural boundary:
- step 0: parsing (before `self.parser.parse`)
- step 1: extracting style profile
- step 2: extracting citations & references
- step 3: linking citations ↔ references
- step 4: retrieving source metadata (per-citation, called once with total count)
- step 5: comparing candidate publications
- step 6: applying neuro-symbolic rules
- step 7: generating report (CIS + final write)

The callback receives `(step_key, step_index, partial_stats)` so the API layer can update its `ProgressState` (e.g. `citations_found=N`, `linked=M`, `sources_queried[db]="ok"|"failed"`).

**5. Fix `matched_sources` everywhere** — three places.

- `src/integrity_checker/pipeline/integrity_pipeline.py`:
  - `AnalysisReport.to_dict()` (line 97) — add `"matched_sources": _serialize_matched_sources(v.matched_source)` for each verdict.
  - `AnalysisReport.from_dict()` (line 166) — rehydrate `matched_sources` back into a `SourceResult` (best-effort) so cache-hit reports work.
  - New helper `_serialize_matched_sources(source: SourceResult | None) -> list[dict]` that maps each `SourceCandidate` (when `found=True`) to `{"source": source_name, "matched_fields": [...], "checked_at": "...", "url": ..., "doi": ..., "title": ...}`.
- `src/integrity_checker/api/routes/report.py` `_json_response` (line 110-132):
  - The verdict dict currently doesn't include `matched_sources`. Add it. For cache-hit / persisted reports we don't have the live `SourceResult`, so reconstruct from existing fields plus a new column-free derivation:
    - If the verdict record was persisted via the updated `add_verdicts` (see next), we can read it back from the joined JSON.
    - If it's an old essay: fall back to deriving `matched_sources` from `sources_succeeded` strings only (each becomes `{source: name, matched_fields: [], checked_at: validated_at}`).
- `src/integrity_checker/db/repository.py` `add_verdicts` (line 87):
  - Persist `matched_sources_json` on `VerdictRecord` — but to avoid a DB migration we serialize it into the existing `features` JSON column under a `"matched_sources"` key. Then `report.py` reads it back via `json.loads(v.features).get("matched_sources", [])`.
- `src/integrity_checker/api/routes/verdicts.py` (line 51, 100) — keep current `matched_sources=[]` for override responses but also load from `features` JSON for the list endpoint.

### Frontend

**1. `web/src/pages/UploadPage.tsx`** — change `handleUpload` so it navigates the moment the `essay_id` arrives. No waiting on the analysis; the POST now returns immediately (after #2 backend change).

**2. `web/src/pages/ProcessingPage.tsx`** — rewrite to be a real-time mirror of `/essays/{id}/status`:

- New `api.getEssayStatus(id)` in `web/src/api/client.ts` calling `GET /api/essays/{id}/status`.
- Polling loop polls **status** every 1.5 s. Step indicator, message, and counters (`num_citations`, `linked`, retrieval source list with their `ok|failed|pending` states) all come from the snapshot.
- Drop the existing fake `setTimeout`-based step progression (the line `const stepIndex = Math.min(Math.floor(pollCount / 1.5), steps.length - 1)`).
- Keep the existing visual stepper — just feed it `snapshot.step_index` instead of `pollCount`.
- When `status === "completed"` AND `verdicts` arrive on `/report`, navigate to `/verification/report/:id`.
- Show a friendly error UI when `status === "failed"`.
- The "Source Retrieval" tiles show `snapshot.sources_queried[db]` for real states; once the pipeline finishes they switch to the `report.verdicts.filter(...).length` count for verification (still real data).

**3. Defensive defaults** — `web/src/api/client.ts`:

- Make `Verdict.matched_sources` typed `MatchedSource[]` with a default of `[]` (TypeScript already infers the API response is non-null, but add `?? []` defensive reads in `ProcessingPage` and `CitationGraphView` to guard against older cached responses or new pipeline steps that don't yet emit candidates).
- Wrap the `EvidenceGraph` `useMemo` over `verdict.matched_sources` so it tolerates `undefined`.

**4. `web/src/components/CitationGraphView.tsx`** — defensive guard (one-liner `v.matched_sources ?? []` before `.some`).

## Files to change

| File | Change |
|------|--------|
| `src/integrity_checker/api/progress.py` (NEW) | In-memory `ProgressState` + tracker |
| `src/integrity_checker/api/routes/essays.py` | Async upload via `BackgroundTasks`, add `/{id}/status` endpoint, return essay_id immediately |
| `src/integrity_checker/pipeline/integrity_pipeline.py` | Add `progress_callback` param + emit at 8 step boundaries; serialize `matched_sources` in `to_dict`/`from_dict`; new `_serialize_matched_sources` helper |
| `src/integrity_checker/api/routes/report.py` | Include `matched_sources` in verdict dict (read from `features` JSON or reconstructed from `sources_succeeded`); return 425 if still processing |
| `src/integrity_checker/db/repository.py` | Store `matched_sources` inside `features` JSON blob in `add_verdicts` |
| `src/integrity_checker/api/routes/verdicts.py` | Read `matched_sources` from stored `features` JSON |
| `web/src/api/client.ts` | Add `getEssayStatus(id)`; defensive `matched_sources` defaults |
| `web/src/pages/UploadPage.tsx` | Navigate immediately on POST response (no client-side wait) |
| `web/src/pages/ProcessingPage.tsx` | Real-time polling of `/status`; drop fake step progression |
| `web/src/components/CitationGraphView.tsx` | Defensive `?? []` guard on `matched_sources` |

## Verification

1. **Unit / backend tests** — `python -m pytest tests/ -v` must remain green (619 passed baseline). Existing tests use synchronous pipeline; the new `progress_callback` defaults to `None` so legacy behavior is preserved.
2. **End-to-end manual flow**:
   - Start backend (`uvicorn src.integrity_checker.api.main:app --reload`) and frontend (`cd web && npm run dev`).
   - Sign in, navigate to **New Check**, drop a PDF (e.g. `data/papers/BERT.pdf`).
   - Confirm: ProcessingScreen appears **instantly**, stepper animates as `parsing → extracting → linking → retrieving → checking → scoring → done`, retrieval tiles show live `pending/ok/failed` states, citations/references counters tick up in real time.
   - On completion, redirected to `/verification/report/:id`. Click any verdict → Evidence Graph opens without `matched_sources` crash; the Source Retrieval tiles show the real verified count per DB.
3. **Regression** — re-run `python -m pytest tests/unit/test_bug_fixes.py -v` and the full suite to confirm no test broke.
4. **Old essays** — load a previously-uploaded essay (pre-fix DB rows). Report still renders; matched_sources reconstructed from `sources_succeeded` fallback path; no `undefined is not iterable`.
