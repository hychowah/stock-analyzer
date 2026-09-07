# Plan: analysis_web UI/UX improvement

Parent session: `eng/sessions/2026-09-06-ui-ux-review/`
Work type: **W4**. No `harness/VERSION` bump. No SPA. No second fair value.
Date: 2026-09-06.

Waves 1–5 in this file **shipped**. Remainder (Waves 6–9, post-SDR recut): **`PLAN_POST_COMPOSE.md`**. Next session: `START_NEXT_SESSION.md`.

This parent session is **reviews + plan + child briefs only**. Product CSS/HTML ships in the child sessions below.

## North star

An operator opening localhost should, in a few seconds:

1. See **the book** and **latest completed research per name**.
2. Read **cheap vs base (MoS)** and **cheap vs bear (Downside)** without confusing them with **Audit PASS** (process) or **duration `pass`** (do not initiate).
3. Start or watch an analysis, then compare two sessions of the same ticker.
4. Open the **CIO cover** first, not a filesystem path.

The site already has the ingredients (catalog numbers, live print, Downside display math, price chart, CIO README, IB join, two-session compare). The UI does not yet *compose* them.

## Method

Seven read-only persona reviews (live UI at `:8765` plus templates/CSS/JS):

| File | Lens |
|------|------|
| `handoffs/review-visual-hierarchy.md` | Type rank, first glance, Night leftovers |
| `handoffs/review-information-architecture.md` | Nine-peer nav, wayfinding, ticker graph |
| `handoffs/review-investor-workflow.md` | Book, duration vs audit, morning scan |
| `handoffs/review-accessibility.md` | WCAG 2.2 AA, keyboard, SR |
| `handoffs/review-mobile-responsive.md` | 800px cliff, leftovers of phone session |
| `handoffs/review-data-visualization.md` | MoS/Downside/chart/football field |
| `handoffs/review-interaction-flows.md` | Job wait, errors, Cancel/Resume |

Contract: `handoffs/REVIEW_CONTRACT.md`.

**Live-process skew (do not re-implement):** the process on `:8765` during review had `git_sha —`, JSON 404 on `/architecture`, empty `/portfolio` despite `.local/portfolio.sqlite`, and Harness `workflow_spec failed`. Working-tree code already mounts `architecture.router` and prefers sqlite for the book (`2026-09-05-ib-portfolio-v1` even notes “Existing :8765 is old code until restart”). Child sessions **must boot a UI from this tree** (`python -m apps.analysis_web --no-auto-restart`) and not treat process skew as missing features.

## Keep (from-scratch keepers, all seven agreed)

- FastAPI + Jinja + small JS. Shareable GET queries. No React/SPA.
- Catalog as the only FV/MoS source. Live Yahoo and Downside % are **display math**.
- One chrome token table (`app.css`). Night/Light via `theme.js`. Semantic greens/reds do not flip with chrome.
- Phone: one table restyled as cards (`.stack-table` + `data-label`), checkbox `.disclose` for Menu/Filters. Do not clone a second card tree.
- Runs live prefix search, query memory (do **not** replay onto empty `/`), abort-vs-empty for unknown tickers.
- Identity URLs (`research:`, `analyze:`, `compare:`).
- Compare does **not** blend FVs. Analyze does **not** show FV until snapshot.
- Agent 6 `charts/valuation_football_field.png` as the envelope graphic (already on disk; just link it).

## Do not do

- SPA / client router / mega-menu / icon rail / tenth peer link.
- Invent live MoS, blended compare target, or a JS DCF.
- Relabel Audit PASS as a buy list. Show duration beside it instead.
- Re-propose Menu / stack-table / theme switch as new products (they shipped 2026-09-05).
- Sticky site header (eats landscape phone).
- Watchlist as a third store of weights/FVs — IB book + latest-per-ticker is the watchlist.
- `git commit` until the user agrees. No `archive/research/**` or `archive/outcomes/**` rewrites.

## Consensus P0 (fix first)

Confirmed in code, not just live skew:

| ID | Finding | Home |
|----|---------|------|
| P0-A | Compare headline cells blank: Jinja `row.values[key]` is `dict.values`, not the `"values"` key. On-disk `headline.json` has the numbers. | `templates/compare_detail.html` |
| P0-B | Unknown browser routes are FastAPI JSON (`{"detail":"Not Found"}`) — `app.py` has an HTML handler for `Exception` only, not 404. `error.html` has no back link. | `app.py`, `error.html` |
| P0-C | Complete Analyze can paint a red `.err` for reconcile notes (`abandon.json present on finalized session…`) and leave `phase orch`. | `analyze_detail.html` |
| P0-D | First Tab on every page hits a 1px-clipped `#nav-open` checkbox; desktop Menu label is `display:none`. | `base.html`, `app.css` `.disclose` |
| P0-E | Audit PASS (process) is the only verdict on `/`; snapshot already has `decision_action` / `verdict_line` / cheap claim. 4516.T MoS 42.7 + PASS reads as buyable until the CIO cover says duration `pass`. | catalog extras + `runs_table.html` + `run_detail.html` |
| P0-F | Nine equal header links; jobs sit beside Harness/Architecture/Health. | `base.html` |

**Not P0 product work (ops / leftover):** restart UI so `/architecture` and sqlite portfolio match this tree; Health `git_sha` must not be silent `—` once the process can read git.

## Design it twice (product shape)

| | A — compose in the current tree | B — new shell |
|---|---|---|
| Nav | One `<nav>`, primary + quieter utility group, `aria-current` | Sidebar + SPA router |
| Decision | Rank columns + type scale + duration from catalog extras | New dashboard widgets / second FV |
| Phone | Raise existing 800px query toward `main` max-width (1100px) | Second card markup |
| Jobs | Patch badge/phase in existing poll JS + `meta refresh` | Job-board SPA |

**Winner: A.** Every persona said keep Jinja. Change rank, grouping, and a handful of bugs.

## Strategic design review (2026-09-06)

One Plan-mode review per wave (`handoffs/sdr-wave*.md`). All six: **mixed / reshape**. Absorb log: `handoffs/SDR_ABSORB.md`.

| Wave | Direction | Load-bearing reshape |
|------|-----------|----------------------|
| 1 trust-p0 | mixed | Headline is a Python view, not Jinja `values`. 404 is Accept negotiation. |
| 2 nav-ia | mixed | One `render_page` injects `nav`. Disclose pairs wrapped. Crumbs stop at chrome+Lab. |
| 3 blotter | mixed | `catalog_api` + `RunQuery` *is* the blotter; HTML only ranks it. Duration ≠ Audit badge. |
| 4a run-reading | mixed | `render_session_report` ≠ sanitizer. `page_run` owns football href. Chart copy is one formatter. |
| 4b a11y-phone | mixed | One 1100px contract. Do not clip thead. List replacement = live node + event. Drop harness 900px. |
| 4c jobs-portfolio | mixed | One wait loop (drop SSE reload). Errors stay on the task. Portfolio reuses Runs cells. |

## Child sessions (multi-agent work)

Execute **in waves**. Do not start a session until its predecessor in the same file set has landed (or you are the only writer). Each child has `AGENT_BRIEF.md` (post-SDR).

```text
Wave 1 (unblocks trust)     2026-09-06-ui-trust-p0
Wave 2 (chrome)             2026-09-06-ui-nav-ia            after Wave 1
Wave 3 (the blotter)        2026-09-06-ui-decision-blotter   after Wave 2
Wave 4 (parallel)           2026-09-06-ui-run-reading        after Wave 3 (run_detail)
                            2026-09-06-ui-jobs-portfolio     after Wave 1 (job files)
Wave 5 (narrow chrome)      2026-09-06-ui-a11y-phone         after Wave 2 AND Wave 3 (app.css)
```

`ui-a11y-phone` is **not** parallel with the blotter. Both write `app.css` (`.decision` / `.below-bear` vs the 1100px contract). `ui-run-reading` may set `.chart-stage` **height** but must not reintroduce `max-width: 800px`. `ui-jobs-portfolio` must not edit `quotes.js` or `app.css`.

### File ownership

| Session | Owns (write) | Must not rewrite |
|---------|--------------|------------------|
| ui-trust-p0 | Headline **view** in `templating.py` or `page_compare_detail`; `compare_detail.html` (iterate labels/cells only); `app.py` 404 **negotiation**; `error.html`; `analyze_detail.html` (error vs muted); `compares.html` abort branch | `base.html`, `runs_table.html`, router `_error()` copies, on-disk `headline.json` key `"values"` |
| ui-nav-ia | `templating.py` `render_page` + `nav`; `base.html` (two wrapped navs + skip); header CSS; crumbs on run/analyze/compare **detail** back-link slot; experiments/calibration/health empty copy | `runs_table.html`, `portfolio.html`, stack-table media query, disclose tab-order (Wave 5) |
| ui-decision-blotter | `catalog_api` hydrate; `RunQuery.latest` + `asof_downside_pct` sort; `runs_query.py`; `runs.js` `QUERY_KEYS`; `pages.py` sort headers; `runs_table.html`; `runs.html` legend; `run_detail.html` strip + **full-width** valuation; `quotes.js` chip; `.decision` / `.below-bear` in `app.css`; `templating.py` duration ≠ audit badge | report viewer, `price_chart.js` domain, 1100px media queries |
| ui-run-reading | `render_session_report` in `render_markdown.py`; `artifacts.py` wiring; `page_run` `football_href`; reports/charts block of `run_detail.html`; `report.html`; `price_chart.js`; `.chart-stage` **height** (not the max-width query) | header, runs columns, `@media (max-width: …)` blocks |
| ui-a11y-phone | **Every** `app.css` 800px query → 1100px (one contract comment); disclose desktop hide; Night `--btn-bg`; `--muted` for words; `runs.js` live node + `runs-table-updated`; `compares.js` listens to that event; `mermaid_boot.js` control icons; architecture frame size in the 1100px query | column order, `.decision` rules, harness.css 900px, `price_chart.js` |
| ui-jobs-portfolio | `analyze_new.html` / analyze routes (Busy stays on form); `analyze_detail.html` + js; `compare_detail.html` wait/verbs/Retry (Wave 1 already fixed headline); drop `data-live-reload` on analyze/compare pages; `portfolio.py` extra join fields; `portfolio.html` cells | `base.html`, `quotes.js`, `app.css`, IB ingest |

### Session 1 — `ui-trust-p0`

**Goal:** The operator never sees a blank compare grid, a JSON 404, or a red “error” on a completed Analyze.

Slices:

1. **Headline view (not packet-in-template).** Project `headline.json` into `{sessions, rows: [{label, cells}]}` in Python (`templating.py` helper or `page_compare_detail`). English labels in that one map. `fmt_num` (None → `—`). Template iterates `row.label` / `row.cells` only. Do **not** rename on-disk `"values"` (packets + `compare_jobs/headline.py`). No blended delta column. Do not leave `row['values'][key]` as the fix — that keeps the `dict.values` collision in the interface.
2. **404 is content negotiation.** Unmatched / `HTTPException` 404: if Accept prefers `text/html`, render `error.html` + `← Runs`; else keep JSON `{"detail": …}`. Do not HTML-ify `/api/*` JSON Accept (job pollers). Pass `request` into the render (Wave 2 current-page). `error.html` default back is `/`. Do **not** unify the six router `_error()` copies this wave.
3. `analyze_detail.html`: `.err` only when status is failed/cancelled/abandoned; reconcile notes `.muted`. Do not parse the reconcile string; do not reshape `research_jobs`.
4. `compares.html`: if `error`, do not also say “No compare packets yet.” Keep HTTP 404 + `is-abort`.

Verify: pytest that a fixture/packet headline renders numbers (not a source grep); unknown path + `Accept: text/html` is chrome; `/api/…` miss with JSON Accept stays JSON.

### Session 2 — `ui-nav-ia`

**Goal:** Four primary jobs, quiet lab, you can see where you are.

Slices:

1. **One `render_page` injects `nav`.** Collapse the five `_render` clones into `templating.render_page`. It always injects `nav.current` from a prefix table (closed set: runs / analyze / compare / portfolio / harness / architecture / experiments / calibration / health). Fragments stay a separate chrome-less render. Full pages that extend `base.html` today bypassing `_render` (`page_runs`, `error.html`, artifacts/report) go through `render_page`. `base.html` matches `nav.current`, not `request.url.path`. Do not put FastAPI `Request` in the template.
2. **Two wrapped navs + disclose.** Primary `<nav aria-label="Primary">` (Runs · Analyze · Compare · Portfolio) and Lab `<nav aria-label="Lab">`. Phone: each group is its own `.disclose` instance **wrapped** so `:checked ~ .disclose-panel` cannot see the other panel. Brand home link **Stock Research**. Tagline: completed runs · start analysis · compare sessions. Nav word **Compare**. Skip link `#content` on `<main>`. Wave 5 still hides `.disclose` on desktop.
3. **Crumbs + Lab copy only.** On run/analyze/compare detail, add `/?ticker_prefix={{ ticker }}` beside the existing back link — same slot. Empty + purpose copy on experiments, calibration, health only. Experiments `h2` → `/?experiment_id=` when ids exist. Health human labels; git SHA never silent `—`. **Do not** edit `runs_table.html` (session→run link is Wave 3). **Do not** edit portfolio empty copy (Wave 4c). No ticker strip `META · 5 runs · Start`.

Keep all nine URLs. Do not add `/ticker/META` as a SPA.

### Session 3 — `ui-decision-blotter`

**Goal:** First glance is ticker · live/as-of · FV · MoS · Downside · duration · audit. **`catalog_api` + `RunQuery` is the blotter interface;** HTML only ranks and labels it.

Slices:

1. **Catalog blotter record.** In `list_runs` / `get_run` hydrate: `verdict_line` (column), `decision_action` (extras), cheap claim (`extras.roic_cheap_claim`). Missing → omit/null. Templates and `/api/runs` read `run.decision_action`, never `extras_json`. No `Run` dataclass wrapper. Do not change export or sqlite schema.
2. **`RunQuery` grains.** Add `latest: bool`. `list_runs` / `count_runs` return at most one row per ticker (newest session) **after** existing filters, then sort/limit. One GET key through `RUN_QUERY_KEYS`, `_filter_href`, `runs.js` `QUERY_KEYS`. Visible Latest vs All; Reset / empty `/` omit the key. Allowlisted sort `asof_downside_pct` = SQL on stored `asof_price` vs `fv_bear` — **not** a `downside_pct` field, not the live-mutated cell. Do not unique-by-ticker in Python on LIMIT 50.
3. **Duration is not Audit.** Print stored action under **Duration**. Do **not** pipe through `verdict_badge` (duration `pass` must not become Audit green). Audit label: process completeness. `verdict_line` is the run-detail subhead; cheap claim on the strip, not a 10th list column. `.below-bear` is signed ink, not a fill.
4. **Paint.** Column order Ticker · Session · As-of · Live · FV · MoS · Downside · Duration · Audit; context `desktop-only`; currency on As-of; session cell links to the run. `.decision` type. MoS/Downside labels + visible vintage after `fillDownside`. Live: signed `%` chip, price in default ink, loading `…` + `aria-busy`, quote first 50 if over cap. Run detail: strip + **full-width** Valuation **above** the chart (Context is not a twin `.grid2`). Own `app.css` `.decision` / `.below-bear` — Wave 5 must not restyle them.

### Session 4 — `ui-run-reading`

**Goal:** Open a run → know the call → see the cone → read the CIO cover.

Slices:

1. **`render_session_report(text, *, run_id, relpath) -> {title, toc, html}`.** Used only by artifact markdown. `render_markdown()` stays `str` with no `run_id` (architecture, harness). Title = first markdown H1 (fallback relpath). TOC = h2/h3 from existing ids. Relative `.md` hrefs rewritten after bleach, resolved against `relpath`’s directory; reject `..`. One H1 on the page (extract title; do not also show it as the first body heading). Wire `artifacts.py` this wave.
2. **`page_run` owns reading facts.** Pass `football_href` (or none) by listing `charts/` for `valuation_football_field.png`. Template: `<img>` only when href is present; else one muted line. One **Read CIO cover** using the existing README link; allowlist table in `<details>` (drop duplicate Path). Do not gallery tornado/heatmap.
3. **One chart copy path.** Shared formatter for readout and tooltip (date, close, bear, base, bull, currency). After `draw()`, if a this-run level is outside `ydom`, say so on `#price-chart-status` (do not overwrite load/error). Legend includes weighted + other sessions. `touchmove` / `touchend`. `pad.l` from longest Y tick. **Stage height:** one `.chart-stage` rule (`min-height: 260px; height: min(42vh, 320px)`); delete the 220px leftover; **do not** edit the `@media (max-width: 800px)` block Wave 5 will move to 1100px. Keep price-centric `domainY`.

### Session 5 — `ui-a11y-phone`

**Goal:** Keyboardable chrome; landscape phone and tablet inherit the stacked layout. **One named 1100px contract** in `app.css`.

Slices:

1. **One 1100px comment, every `app.css` 800px query.** 1100px = `main` max-width; Menu, stack-table, grid2, forms, 44px, 16px inputs, ticker flex, overflow-x, architecture-figure, **and** `.chart-stage` **query** all use it. Desktop disclose hide is `min-width: 1101px`. Handoff to run-reading: do not reintroduce 800; only edit height values. Update README / CSS comments that say “Below 800px”.
2. **Disclose.** Class-level `display: none` on `.disclose` / `.disclose-btn` when wide (covers Menu, Wave 2 Lab, Filters). Phone: keep the CSS hack; `:focus-visible` on `.disclose-btn`. Do not special-case `#nav-open`.
3. **Contrast.** Night `--btn-bg` ≥ 4.5:1 (`#2563eb`) in **both** dark tables (`data-theme` and `prefers-color-scheme`). Word uses (`.quote-kind`, chart ticks) → `--muted`. Leave `--faint` for non-text.
4. **Do not clip `.stack-table thead`.** Keep `display:none` so sort links are not invisible tab stops. Empty pick `th`: `aria-label="Select for compare"`. Wave 6: `.cell-label` spans, not JS `aria-label` on the value `td`.
5. **List replacement.** `#runs-status` (`aria-live="polite"`) **outside** `#runs-results`. Strip `aria-live` from the count inside the partial. After swap: copy count/abort into the live node, restore focus, `dispatchEvent("runs-table-updated")`. `compares.js` listens to **that** (not `catalog-changed`). Fetch failure: same status node + flash; stale table stays. `#compare-hint` is a separate live region. Hint: ticker + session_key, not raw `research:` ids. Compare pick 44px hit; sticky `#compare-bar` only while a pick is on.
6. **Architecture only (not harness).** Shorter figure frame inside the 1100px query; `controlIconsEnabled: true`. **Drop** harness.css 900px / pipeline column / `scrollIntoView` from this session.

### Session 6 — `ui-jobs-portfolio`

**Goal:** Wait on a job like a human; see the book as a blotter.

**Job document (one wait loop, not four nits):**

1. Start form: **Ticker + as-of + Harness + submit** first; slug/models/notes/ingest in `<details>`. Round-trip every field. Disable submit after confirm. Reuse `.stack-form`; do **not** lift it out of the 800px query (Wave 5 owns that).
2. Running Analyze/Compare: JS patches badge, phase, error, `resume_hint` from the JSON APIs. Reload **only** on terminal status. While running/queued: `<meta refresh=15>` + `aria-live` on the status line.
3. **Drop `data-live-reload`** from `analyze_detail.html`, `compare_detail.html`, `analyze.html`, `compares.html`. Do not add `/fragments/analyze`. Do not rebuild the artifact `<ul>` in JS (API has no index; names-only growth waits for meta or terminal reload). Human wait copy is `resume_hint`; no UI phase-name map.
4. **Errors stay on the task.** Busy / Grok-missing / runbook-missing on start → same form with `error=` and all fields. Cancel/Resume/Discard 303 back to the job with `?flash=`. Resume conflict is copy on that job page. Cancel confirm: “Kill Grok, keep the session.” Unknown job still `error.html` (Wave 1 back link). Failed Compare: Retry POST same pair (new packet). This session **owns `compare_detail.html` wait/verbs** (Wave 1 already fixed the headline view).

**Book blotter (reuse Runs cells, do not invent a dialect):**

1. Extend `_catalog_fields` with `fv_bear`, listing symbol, session dates, `decision_action` **when the run dict already has them**. Template: **As-of**; Live + Downside use the same `data-quote-symbol` / `data-downside-pct` / `data-fv-bear` / `data-asof-price` as `runs_table.html`. Duration: stored action or `—`. Missing / no-PASS → `/analyze/new?ticker=`. IB Close stays IB.
2. Empty copy: “Import an IB activity statement”; path in `<code>`; Python module is not the headline.
3. Waterfall: Starting/Ending NAV as total rows; signed components from a zero gutter via **row fields + inline geometry in `portfolio.html`**. Do not edit `app.css` `.perf-bar`. Do not edit `quotes.js`. Do not change `import_ib`.

## Finding → session map

| Review | Finding | Session |
|--------|---------|---------|
| visual F1, F3, F4, F5 | Decision strip, column rank, type scale, run order | decision-blotter (+ run-reading for chart) |
| visual F2, F7, F8 | Header, job chrome, IDs as titles | nav-ia, jobs-portfolio |
| visual F6 | Night semantic billboards | decision-blotter (chip) + a11y-phone (btn/faint) |
| IA F1–F4, F6–F8 | Nav group, labels, memory, empties | nav-ia |
| IA F2, F7 | Dead destinations, error.html | trust-p0 + nav-ia |
| IA F5, F9 | Ticker strip, crumbs | nav-ia |
| investor F1, F8 | Portfolio live/book | jobs-portfolio (plus boot-from-tree) |
| investor F2 | Duration vs Audit | decision-blotter |
| investor F3 | Blank headline | trust-p0 |
| investor F4, F9 | Latest-per-ticker, Downside sort | decision-blotter |
| investor F6, F7 | Wait screen, CIO viewer | jobs-portfolio, run-reading |
| a11y F1–F8 | Disclose, skip, live region, contrast, thead, figures | a11y-phone (skip in nav-ia; **do not clip thead**) |
| mobile F1–F7 | 1100px, chart, overflow, compare hit, 16px | a11y-phone, run-reading (chart height) |
| viz F1 | Headline Jinja | trust-p0 |
| viz F2–F6 | Labels, order, chart clip, football PNG, quote chip | decision-blotter, run-reading |
| viz F7–F8 | Portfolio/calibration viz | jobs-portfolio; calibration bars optional P2 |
| interaction F1–F10 | Wait, errors, verbs, abort copy, forms | trust-p0, jobs-portfolio (**drop SSE reload**, no list fragments) |

P2 nits ride along only when the owning file is already open.

## How a later agent starts

**Branch:** `ui-ux-compose` (all waves, sequential commits). Do not fork a second branch per wave — file ownership assumes one line of history.

```text
1. git checkout ui-ux-compose && git pull --ff-only (if remote exists)
2. Read eng/AGENTS.md (Mode B).
3. Read this PLAN.md and the child AGENT_BRIEF.md (post-SDR).
4. Confirm predecessor session is done (feature_list passes or user said to proceed).
5. Boot UI from this tree: python -m apps.analysis_web --no-auto-restart
   (do not trust a stale :8765 from another SHA)
6. Baseline: python scripts/eng_verify.py
7. Implement one feature_list item with passes: false.
8. Re-verify (pytest apps/analysis_web/tests + eng_verify). Browser or curl the routes you touched.
9. Do not git commit until the user agrees. Stay on ui-ux-compose.
10. If architecture (new page, new display math that looks like FV) changed, update ARCHITECTURE.md in the same change set.
```

Paste prompt (child): open `eng/sessions/<child>/AGENT_BRIEF.md` and follow it.

First implementation session: **Wave 1** `eng/sessions/2026-09-06-ui-trust-p0/AGENT_BRIEF.md`.

## Parent session success

- [x] Seven persona reviews on disk
- [x] This plan
- [x] Six child sessions scaffolded with `issue.json`, `feature_list.json`, `AGENT_BRIEF.md`
- [x] Strategic design review per wave; PLAN + briefs absorbed (`handoffs/SDR_ABSORB.md`)
- Parent does **not** mark product features `passes: true` — children own that.

## Out of scope until later

- Calibration scatter / outcome bars (empty join today).
- Experiments as a real filter index beyond the empty-state fix in nav-ia.
- Harness `workflow_spec` root-cause; harness pipeline column / fake tablist (dropped from Wave 5).
- Pagination of 89 runs beyond Latest-per-ticker.
- Desktop 44px everywhere (AA + keyboard is the bar).
- Unify router `_error()` helpers.
- Ticker strip `META · 5 runs · Start · Compare`.
- Real `.cell-label` in stacked cells — **shipped Wave 6** (`runs_table.html` + `portfolio.html`; other stack-tables still `data-label` only).
- UI map of `phase_current` ids to English (`resume_hint` is the human sentence).
```
