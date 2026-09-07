# Strategic design review — Wave 4c ui-jobs-portfolio

Grain: feature / implementation plan (Session 6). Not a source-style audit.

## Verdict
- **Direction:** `mixed`
- **Why:** The work is to make an 8-hour Analyze waitable and to show the IB book as the same decision blotter Runs already almost is — server HTML, catalog math only, no SPA, no second FV. Designed from scratch that is two deep interfaces: a **job document** whose live region is one loop (JSON patch of status + `<meta refresh>` for no-JS; SSE does not also full-reload), with start/capacity/verb failures staying on that document; and a **book blotter** that reuses the Runs quote/Downside cell contract, with waterfall as signed NAV geometry on data already in sqlite. The brief is still a file-ownership patch: it layers a third wait path on `live.js`, leaves list-reload as an unresolved “or,” sends Resume/Busy to `error.html`, and specifies artifact DOM reconstruction the job JSON does not contain.
- **Do:** `reshape`

## Keep
- FastAPI + Jinja + small JS. No job-board SPA, no client router, no toast framework.
- No FV until snapshot; Compare does not blend FVs; do not rebuild IB ingest; do not rewrite `base.html`.
- Analyze/Compare stay POST forms with confirm. Cancel (kill, keep session) / Resume / Discard stay three verbs, not one Stop.
- Failed Compare Retry = new packet (POST same pair), not rewrite of an append-only packet.
- `quotes.js` already global (`base.html`); Downside stays `templating.downside_pct` vs **stored** bear. Portfolio sqlite join (`active_portfolio_view`) is the book.
- Wave 1 predecessor: complete Analyze is not a red reconcile `.err`; HTML 404/back link already the error-card home for *missing* resources.
- `resume_hint` / `phase_current` already on the job dict (`packages/research_jobs/jobs.py`). Empty-state voice (“Import an IB activity statement”) and missing-name → `/analyze/new?ticker=` are the right operator exits.
- File split vs Wave 3 is acceptable for parallelism **if** portfolio does not invent a second live-cell dialect.

## Candidates

### 1. One wait loop
- **Change:** Treat start-form + wait-loop + verbs + list-reload as **one job-document interface**, not four template nits.
  - Running Analyze/Compare: JS patches **badge, phase, error, `resume_hint`** from `/api/analyze/{id}` and `/api/compares/{id}`. Reload **only** on terminal status (so complete CTAs and verb sets are server HTML).
  - While `running`/`queued`, emit `<meta http-equiv="refresh" content="15">` and `aria-live="polite"` on the status line.
  - **Retire SSE full-reload on these pages:** drop `data-live-reload` from `analyze_detail.html`, `compare_detail.html`, `analyze.html`, `compares.html`. Do not add a “skip reload if ticker focused” branch in `live.js`. Do **not** add `/fragments/analyze` + `/fragments/compares`.
  - Do **not** rebuild the artifact `<ul>` in JS. `/api/analyze/{id}` is the job dict; artifact index is assembled only in `page_analyze_detail`. Names-only growth waits for meta refresh or the terminal reload.
  - Human wait copy is `resume_hint` when present; `phase_current` stays the machine id. No new phase-label map in the UI.
  - Claim **`compare_detail.html`** for this session (Retry form, Cancel confirm, meta, aria-live). Wave 1 already wrote the headline/error honesty; this session owns the wait/verbs on that file.
  - Start form: **Ticker + as-of date + Harness + submit** first; slug/models/notes/ingest in `<details>`. Round-trip every field. Disable submit after confirm. Reuse existing `.stack-form` class; do **not** lift `.stack-form` out of the 800px query in `app.css` (Wave 4b owns that breakpoint).
- **Why:** Today three loops already fight: `analyze_detail.js`/`compare_detail.js` reload on status string; `live.js` full-reloads any `data-live-reload` page when `analyze_changed`/`compare_changed` tokens move (and `onToken` calls `reloadSoon()` **without** kind); no meta refresh. Adding in-place patch **on top** is temporal decomposition and an unknown unknown (the patch will look broken because SSE will F5 anyway). Artifact patching is a shallow module (JS repeating Jinja) against an API that has no artifact list. List fragments would copy Runs’ live-search machine for a GET directory the operator is not staring at for eight hours. `resume_hint` is already the human sentence; a parallel “Valuation vs orch” table is information leakage from the harness.
  - Design it twice (wait): (A) status-line patch + meta, SSE off these pages; (B) fragment-swap the status card like Runs. **A** is the simpler common-case interface — phase ticks are rare; the complete page is a different document.
  - Design it twice (lists): (A) drop live-reload; (B) `/fragments/analyze|compares`. **A** wins. Runs needs fragments because the filter is a live working query; these lists are not.
- **When:** `this change`

### 2. Job errors stay on the task
- **Change:** One error rule for this session: **capacity and verb failures re-render the current task**; only missing resources use `error.html`.
  - `POST /analyze/new` and `POST /compares/new`: `AnalyzeBusy` / `CompareBusy` / Grok-missing / runbook-missing → same form with `error=` and **all fields preserved** (today: ticker/validation stay on form; 409/503 call `_error()` in `routes/analyze.py` and `routes/compares.py`).
  - Cancel / Resume / Discard: 303 back to `/analyze/{id}?flash=…` (or compare equivalent). Show `flash` via the existing `base.html` slot. Resume conflict / Busy / leftover-PID is copy on **that job page**, including `resume_hint`, not a chrome-less card. Cancel confirm: “Kill Grok, keep the session.”
  - 404 unknown job: keep `error.html` (Wave 1 back link).
- **Why:** Two error surfaces for the same operator task is overexposure and change amplification (Back on a POST 409 is a resubmit; typed harness pin is lost). The plan only names Busy/Grok on **start**, so Resume/Discard stay the old `_error()` maze — a patch around the form, not a redefined operation. Query `flash` matches shareable GET; do not add a flash cookie framework.
- **When:** `this change`

### 3. Portfolio is the Runs blotter cell, not a second Live dialect
- **Change:** Extend `_catalog_fields` in `apps/analysis_web/services/portfolio.py` with `fv_bear`, listing/quote symbol, `session_date`/`session_key`, and `decision_action` **when the run dict already has them**. Template: catalog price header **As-of**; Live + Downside % use the **same** `data-quote-symbol` / `data-downside-pct` / `data-fv-bear` / `data-asof-price` contract as `partials/runs_table.html`. Duration: print stored `decision_action` or `—` (omit invention). Missing / no-PASS: link `/analyze/new?ticker=` using `catalog_ticker` else `ib_symbol`. IB Close stays IB; do not mix vintages under “Price.”
  - Waterfall: mark Starting/Ending NAV as **total** rows (those names already exist on `nav_components`); signed components from a **zero gutter** via row fields + inline geometry in `portfolio.html`. Do not edit `app.css` `.perf-bar` in this wave (4b owns chrome CSS). Do not change `import_ib` / sqlite ingest.
  - Empty copy: operator sentence + path in `<code>`; drop `python -m apps.analysis_web.import_ib` as the headline.
- **Why:** Live/Downside/Duration knowledge would otherwise leak into a second HTML dialect, then fight Wave 3’s `quotes.js` chip change. `_catalog_fields` today has no `fv_bear` — a Downside column without it is a fake. Sequencing this child after Wave 1 only is fine **if** missing extras render as `—`; it is wrong if this session writes a portfolio-specific quote filler. Waterfall-in-`app.css` is special-purpose CSS in a file another parallel session must edit.
  - Design it twice: (A) reuse Runs cells + join fields; (B) portfolio-only live JS. **A**.
- **When:** `this change`
