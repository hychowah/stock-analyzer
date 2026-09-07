# Review: Interaction flows

## Verdict

This is a solid FastAPI+Jinja operator console: GET forms still work, Runs already distinguish “unknown ticker” from “empty table,” and Analyze/Compare start as POST forms with a JS confirm. The product then drops the human during the hours that matter. Job pages only reload on *status string* change, not phase; Cancel has no confirm while Discard does; 409/503/404 land on a chrome-less-feeling `error.html` with no back; live `/architecture` is a raw JSON 404. Highest-leverage change: make running Analyze/Compare pages patch badge + phase in place (and `<meta refresh>` without JS), and send every start/busy/not-found failure back to the same form or list with a flash — never a dead card.

## Findings

### F1 — Running job pages are not waitable
- **Severity:** P0
- **Pages:** `/analyze/{id}`, `/compares/{id}`, `/analyze`, `/compares`
- **Evidence:** `templates/analyze_detail.html` prints `badge status-{{ job.status }}` and `phase {{ job.phase_current }}` once. `static/analyze_detail.js` (and `compare_detail.js`) poll JSON every 5s/3s but **only `window.location.reload()` when `job.status !==` the boot status**; phase, pid, artifacts, and errors are ignored. `catch` is empty. No `<meta http-equiv="refresh">`, no `aria-live` on the badge. SSE `analyze_changed` in `live.js` can full-reload the page *if* `phase_status.json` mtime moves (`change_feed.py` fingerprints it). Live `/api/events?once=1` hello had **no `git_sha`**. No running jobs on disk today; complete COHR still shows `phase orch`.
- **Why it matters:** Mode A is 2–8 hours. A human watching “queued / orch / 1_parallel” needs the badge and phase to move without F5, and without a full reload that jumps scroll. No-JS operators have no wait loop at all.
- **Recommendation:** In `analyze_detail.js` / `compare_detail.js`, patch the badge, phase, error, pid, and artifact list from `/api/analyze/{id}` (and compare) on every tick; reload only on terminal status. In the templates, when `job.status in ['running','queued']`, emit `<meta http-equiv="refresh" content="15">` plus `aria-live="polite"` on the status line.
- **Keep vs reshape:** Keep server-rendered job pages + JSON poll. Do not replace with a SPA dashboard.

### F2 — Failures leave the task: `error.html` and JSON 404
- **Severity:** P0
- **Pages:** `/analyze/new` POST, `/compares/new` POST, `/analyze/{id}`, `/compares/{id}`, `/architecture`, unknown paths
- **Evidence:** `routes/analyze.py` re-renders the form only for `AnalyzeTickerError` / `AnalyzeValidationError`. `AnalyzeBusy` (409), `AnalyzeGrokMissing` / `AnalyzeRunbookMissing` (503), resume conflicts, and missing jobs all call `_error()` → `templates/error.html`: a single `<p>{{ message }}</p>`, no back link, no “open Analyze,” no replayed fields. Same pattern in `routes/compares.py`. Live `GET /analyze/does-not-exist` and `/runs/does-not-exist` are that card. Live `GET /architecture` is FastAPI `{"detail":"Not Found"}` (22 bytes, no chrome) even though `base.html` nav links there. `app.py` has an HTML handler for `Exception` only — not 404.
- **Why it matters:** Slot-full and missing-Grok are the normal start failures. The operator loses ticker/date/models, and browser Back on a POST is a resubmit. Clicking Architecture in the header currently dumps you out of the product.
- **Recommendation:** Add a FastAPI 404 handler that renders `error.html` with `← Runs` / `← Analyze`. Change `post_analyze_new` / `post_compare_new` Busy and Grok-missing to re-render the *form* with `error=` (same as ticker errors), preserving every field. Put a contextual back link on `error.html` (`back_href`, `back_label`).
- **Keep vs reshape:** Keep one HTML error template. Do not add a toast framework.

### F3 — Complete Analyze can look failed
- **Severity:** P0
- **Pages:** `/analyze/{id}`
- **Evidence:** Live `GET /analyze/analyze:COHR:2026-09-03` — badge `complete`, catalog link present, **and** `<p class="err">abandon.json present on finalized session; not treating as abandoned</p>`, **and** `phase orch`. Template always paints `job.error` as `.err` (`analyze_detail.html`). That string is a reconcile note from `packages/research_jobs/jobs.py`, not an operator failure.
- **Why it matters:** Red error on a finished run destroys trust in Cancel vs Discard vs “this snapshot is real.” Phase `orch` on complete also makes the wait UI look broken after the fact.
- **Recommendation:** In `analyze_detail.html`, only use `.err` when `job.status` is `failed` / `cancelled` (or `abandoned`). Show reconcile notes as `.muted`. Prefer `phase_current` from `phase_status.json` (`done` when complete) and do not leave `orch` on a finalized job in the refresh path.
- **Keep vs reshape:** Keep the complete + catalog-run link. Hide internal reconcile from the error slot.

### F4 — Cancel / Resume / Discard are uneven verbs
- **Severity:** P1
- **Pages:** `/analyze/{id}`, `/compares/{id}`
- **Evidence:** Start form confirm in `analyze_new.html` *explains* “Cancel is kill-only (resumable); Discard abandons.” On the job page, **Cancel has no `confirm()`** (`analyze_detail.html` POST `/analyze-cancel`; compare Cancel POST `/compare-cancel` with no confirm). Discard has confirm. Resume is a bare POST with no “confirm no leftover `grok.exe`” (README) and **`resume_hint` is never shown** (stored in `jobs.py`, absent from the template). Cancel/resume/discard 303 back with no `flash` (`base.html` `{% if flash %}` is never passed from these routes). Compare has no Resume/Discard at all.
- **Why it matters:** Accidental Cancel kills an 8-hour Grok. Resume without the leftover-process warning is the documented foot-gun. The operator cannot see *where* resume will pick up.
- **Recommendation:** Confirm Cancel (“Kill Grok, keep the session, Resume later”). On Resume, show `resume_hint` and a one-line leftover-PID warning; confirm submit. After Cancel/Resume/Discard, 303 with `?flash=` (or session cookie) into `base.html` flash. Leave Compare as cancel-only plus Retry (F5).
- **Keep vs reshape:** Keep the three verbs and POST forms. Do not collapse them into one “Stop.”

### F5 — Failed Compare is a cul-de-sac
- **Severity:** P1
- **Pages:** `/compares/{id}`, `/compares/new`, `/`
- **Evidence:** Live `GET /compares/compare:AVGO:2026-09-03__2026-08-23__r3_vs_2026-09-01` — `status-failed`, error `Grok process exited before 99_synthesis.md`, headline table with **empty cells**, packet files only. No Retry. `compare_new.html` has no `force` checkbox even though `post_compare_new` reads `force`. Backend `_find_pair` only short-circuits running/complete, so a new POST of the same pair *would* spawn — the page just never offers it. `compares.js` list picker has the same gap.
- **Why it matters:** Failure is a normal 15–40 minute outcome. The human has to re-find two sessions in a 200-row `<select>` with no ticker grouping.
- **Recommendation:** On failed/cancelled compare detail, POST the same `run_id_a` / `run_id_b` to `/compares/new` (hidden fields + confirm). Optional `force` only when retrying a complete packet. Pre-select those ids on `compare_new.html`.
- **Keep vs reshape:** Keep append-only packets; Retry = new packet, not rewrite.

### F6 — Compare ticker abort still looks like “no packets”
- **Severity:** P1
- **Pages:** `/compares`
- **Evidence:** Live `GET /compares?ticker=ZZZZNOTATICKER` → HTTP 404, `form.filters.is-abort`, `role="alert"` **Aborted.** Then a second card: “No compare packets yet. Select two same-ticker runs and hit Compare.” (`compares.html` `{% else %}` on empty `jobs` does not check `error`). Contrast Runs: live `/?ticker_prefix=ZZZZNOTATICKER` aborts **without** a table; live `/?ticker_prefix=META&mos_min=999` is 200 “No runs”. Analyze unknown ticker is correctly 200 “No Analyze jobs for ZZZZNOTATICKER” (catalog not required).
- **Why it matters:** The one place Runs got abort-vs-empty right, Compare undoes it. Operator may hunt for a packet that cannot exist.
- **Recommendation:** In `compares.html`, if `error`, do not render the empty-packet sentence; keep the abort + Filter. Mirror Runs: link to `/analyze/new?ticker=` only if you mean “this symbol is unknown to the catalog.”
- **Keep vs reshape:** Keep HTTP 404 + `is-abort`. Fix the copy branch.

### F7 — Analyze/Compares lists full-reload and wipe the filter
- **Severity:** P1
- **Pages:** `/analyze`, `/compares`
- **Evidence:** Both bodies set `data-live-reload="1"` plus `data-live-analyze` / `data-live-compare`. `live.js` `reloadSoon` does `location.reload()` (400ms after a flash). Filter ticker is a GET input, not `data-live-partial`. Runs already solves this: `data-live-partial="1"` → `catalog-changed` refetches `/fragments/runs` and **does not** wipe `#runs-filters` (`runs.js`, `runs.html`). `analyze/new` and `compare_new.html` correctly omit `data-live-reload` (SHA watch still reloads on process replace).
- **Why it matters:** Typing a ticker filter on Analyze while another job’s `job.json` touches will wipe the input. Same on Compares during a 40-minute audit.
- **Recommendation:** Either drop live-reload from the *list* pages (manual Filter is enough) or add `/fragments/analyze` + `/fragments/compares` and `data-live-partial` the same way as Runs. Do not full-reload while the ticker input is focused.
- **Keep vs reshape:** Keep the Runs partial-reload pattern; copy it or don’t live-reload lists.

### F8 — Start forms forget what you typed
- **Severity:** P1
- **Pages:** `/analyze/new`, `/compares/new`
- **Evidence:** `page_analyze_new` only takes `ticker` + `error`. Validation failure drops `session_date`, `slug`, models, notes, ingest, harness. Busy/503 drop even ticker (F2). Compare new *does* round-trip `run_id_a` / `run_id_b`. Confirm dialogs are `onsubmit="return confirm(...)"` — no-JS POSTs skip them (acceptable) but JS users can double-submit after OK; buttons never disable.
- **Why it matters:** Re-typing an 8-hour job’s harness pin and models after a ticker typo is how people spawn the wrong pin.
- **Recommendation:** Pass every form field back on `page_analyze_new`. Disable the submit button on first successful confirm (`onsubmit` in the template). Keep the GET `?ticker=` prefill that Runs abort already uses.
- **Keep vs reshape:** Keep the POST form. Do not move start to fetch-only.

### F9 — Harness inspector is not a page without JS, and live it is an error card
- **Severity:** P1
- **Pages:** `/harness`, `/harness?version=2.39.0`
- **Evidence:** Live `GET /harness` and `?version=2.39.0` both render `error.html`: `workflow_spec failed: ` (empty stderr). In-tree `harness.html` is better: pipeline is server HTML, inspector empty state is honest, Prompt loads `/api/harness/prompt`. But the inspector body is **only** painted by `harness.js`; `?agent=` / `?phase=` are `data-open-*` for JS on load, not server-rendered. Version `<select onchange="this.form.submit()">` has **no submit button** — no-JS cannot change pin. Tiles are `<button type="button">` with no links.
- **Why it matters:** This is the map of the 8-hour job the operator just started. Today the live page is a dead error; even healthy, no-JS sees only a poster.
- **Recommendation:** Fix the PinError empty message (show return code + cmd). Server-render the inspector from `agent` / `phase` query params. Make each tile `<a href="/harness?version=&agent=">`. Add `<button type="submit">` on the version GET form; keep `onchange` as progressive enhancement.
- **Keep vs reshape:** Keep the pipeline + inspector split. Do not make the inspector a client-only app.

### F10 — Live table and Compare-from-list hide errors
- **Severity:** P1
- **Pages:** `/`
- **Evidence:** `runs.js` `fetchTable` catch ignores everything except `AbortError` — a down `/fragments/runs` leaves a stale table with no flash. No `aria-busy` / pending class while the 100ms debounce fetch is in flight. 404 abort *does* toggle `form.is-abort` (good). `compares.js` writes API failures into `#compare-hint` with `className = "muted"` (not `.err`, no `role="alert"`). Network error string is easy to miss next to a disabled button that then re-enables.
- **Why it matters:** Filter/sort is the daily path. Silent stale table and a grey “409 busy” hint are how people double-start Compare or trust the wrong working set.
- **Recommendation:** On fragment fetch failure, set a `.flash.err` in `#runs-results` (don’t clear the old table until a 200). Add `aria-busy` on `#runs-results` during fetch. In `compares.js`, set `hint.className = "err"` and `role="alert"` on failure.
- **Keep vs reshape:** Keep fragment fetch + two-checkbox picker. Do not block Filter on JS.

### F11 — Architecture figures: advertised, unreachable live; controls are JS-only
- **Severity:** P1 (leftover / process)
- **Pages:** `/architecture`
- **Evidence:** Header always links Architecture. Live GET is JSON 404 (F2). In-tree `architecture.html` + `mermaid_boot.js`: wrap `pre.mermaid`, inject Reset, pan/zoom from CDN, wheel only on pointerenter. No loading text while Mermaid loads; CDN fail leaves source text (good). Reset is not in the HTML. Theme does not retokenize Mermaid (`theme: "neutral"` always). `health.html` live `git_sha` is `—`; SSE hello omitted `git_sha` — `live.js` cannot detect a replaced UI.
- **Why it matters:** The operator cannot open the map from the product they are using, and cannot tell the UI process is stale.
- **Recommendation:** After HTML 404 (F2), show a “Reset” button in `architecture.html` hidden until `is-interactive`, with a `.muted` “Drawing…” in the figure. Put `git_sha` on `/health` and in SSE `hello` even when null, so a boot without git is visible. Do not SPA the diagrams.
- **Keep vs reshape:** Keep markdown + mermaid-in-page. Keep Reset / hover-wheel.

### F12 — Small interaction nits (one bucket)
- **Severity:** P2
- **Pages:** shared, `/compares/new`, `/portfolio`, `/health`, theme
- **Evidence / recommendation:**
  - Theme toggle is JS-only; no-JS already follows `prefers-color-scheme` in `app.css` — keep, don’t add a form.
  - `confirm()` on start is JS-only; native POST still works — keep.
  - `compare_new.html` dumps ~200 runs in two flat `<select>`s with no `<optgroup>` by ticker — group them.
  - Failed compare headline cells render empty (`row.values[key]` miss) — print `—`, don’t leave blank `<td class="num">`.
  - `base.html` flash slot is unused except Compare-complete inline flash — use it for F4.
  - Portfolio empty live is good (`.err` + copy `portfolio.example.json` / `import_ib`); keep.
  - Experiments/calibration are GET and fine; no empty-state beyond missing groups.
  - Disable Analyze submit after confirm to prevent double spawn (also F8).
- **Keep vs reshape:** Polish in place.

## What already works

- Runs **abort vs empty**: unknown prefix is HTTP 404 + abort card + “Start Mode A analysis for …” (`partials/runs_table.html`); real ticker + harsh filters is 200 “No runs.” Live fragment 404 matches.
- Runs **live search does not wipe input**: `data-live-partial` + `/fragments/runs` + 100ms debounce + `history.replaceState` + remembered query (`runs.js`).
- **No-JS Runs**: GET form Filter/Reset/sort links still work; checkboxes are extra.
- **Compare has a no-JS door**: `/compares/new` POST form and run-detail sibling form; list “Compare form” link. JS two-select is additive (`compares.js`).
- Analyze **ticker/validation errors stay on the form** with `.flash.err`.
- Analyze **new form is not live-reloaded** on catalog ticks (no `data-live-reload`) — typed fields survive other jobs.
- **Cancel = POST keep session; Discard = confirm + abandon** is the right verb split (once Cancel gets a confirm).
- **Artifact progressive disclosure**: in-progress names only until snapshot (`analyze_detail.html` `body_ok`).
- Status **badge colors** for running/queued/complete/failed (`app.css`).
- Compare **complete flash**: “Read the synthesis first.”
- Theme: first visit follows OS; click writes `analysis_web.theme`; private-mode failures ignored (`theme.js`).
- Phone Menu / Filters checkbox disclose; 44px targets already shipped.
- Portfolio missing-book state tells you exactly what to copy.
- SSE classifies catalog / portfolio / analyze / compare so Compare pages do not reload on Analyze mtimes (`live.js` + `change_feed.classify_change`).

## From-scratch keepers

- Server-rendered HTML as the product; JS for live cells, wait ticks, theme, figures.
- GET working query on `/` as the shareable filter (not a hidden client store as the only source).
- Abort (404, don’t continue) vs empty (200, keep going).
- Cancel (kill, resumable) vs Discard (abandon) vs Resume — three verbs, POST forms.
- Two-session Compare as a job page with headline first, synthesis when complete.
- `data-live-partial` so catalog ticks don’t eat an in-progress ticker field.
- Architecture as `ARCHITECTURE.md` in a figure frame, not a separate graph app.
- Harness as a staged pipeline you can open with a URL (`?agent=`).

## Do not do

- React/SPA rewrite of Analyze/Compare.
- Invent a second fair value or “blended” Compare number.
- Replace POST start with fetch-only (breaks no-JS).
- Auto-start Mode A from a Runs abort without the existing confirm.
- Full-page reload on every phase tick (patch the badge instead).
- `confirm()` as the only Discard guard (server already refuses snapshot sessions — keep that).
- Toast libraries, client routers, or WebSocket job dashboards.
- Live-reload the `/analyze/new` form on catalog/analyze events.
