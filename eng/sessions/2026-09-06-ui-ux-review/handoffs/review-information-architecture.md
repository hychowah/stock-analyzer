# Review: Information architecture

## Verdict

This is **nine tools sharing a header**, not one product with a primary job. The operator’s real loop is find a completed run → start or watch an analysis → compare two sessions → check the book; the chrome treats that loop as equal to Harness, Architecture, Experiments, Calibration, and Health, in an order that splits Analyze from Compares with two reference pages. Live, two of those nine peers are dead (Architecture is a JSON 404 with no chrome; Harness is an empty `workflow_spec failed:` card), and nothing in the header says which page you are on. The single highest-leverage change is to **group the nav into four primary jobs and a quiet utility row**, and to make every advertised destination either work or fail inside the same HTML chrome — without a mega-menu and without a SPA.

## Findings

### F1 — Nine peer links, no primary vs utility

- **Severity:** P0
- **Pages:** `/` and every page that extends `templates/base.html`
- **Evidence:** Live header on `/`, `/analyze`, `/compares`, `/portfolio`, `/health` (2026-09-06) is one undifferentiated `<nav id="site-nav">` with nine equal `<a>`s in this order: Runs, Analyze, Architecture, Harness, Compares, Health, Experiments, Calibration, Portfolio (`apps/analysis_web/templates/base.html` lines 19–28). CSS (`.header-links a` in `static/app.css`) gives them identical color and spacing; there is no `aria-current`, no group, no “More”. The tagline is implementation (“catalog + job scheduler · Analyze starts Mode A · Compare appends archive/comparisons/”), not a job. Phone (≤800px) stuffs the same nine peers behind **Menu**. Working-tree `ARCHITECTURE.md` § The website lists the same surfaces as peers.
- **Why it matters:** An operator opening localhost to “look at META / start a run / watch a job / compare two sessions” must hunt among system-map and calibration tools. Architecture sitting between Analyze and Compares is the tell: this chrome was appended as features shipped, not designed as a product.
- **Recommendation:** In `templates/base.html` + a small `.header-links` rule in `static/app.css`, split one nav into **primary** (Runs, Analyze, Compare, Portfolio) and **utility** (Harness, Architecture, Experiments, Calibration, Health). Utility can be a second, quieter inline group on desktop and a second disclose labeled **System** on phone — not a mega-menu, not nested flyouts. Keep all nine URLs. Pass `request` (or `nav`) into every `_render` so the active primary item can be marked (see F3).
- **Keep vs reshape:** Keep every destination and the server-rendered pages. Reshape only grouping and visual weight. Do not add a tenth top-level link.

### F2 — Advertised destinations that leave the product

- **Severity:** P0
- **Pages:** `/architecture`, `/harness`, `/health`
- **Evidence:** Live `GET /architecture` → HTTP 404, `content-type: application/json`, body `{"detail":"Not Found"}` (22 bytes), **no header**. Working tree mounts `architecture.router` in `apps/analysis_web/app.py` and `templates/base.html` already links it — chrome is disk templates; the booted process does not serve the route. Live `GET /harness` → 200 HTML error card “workflow_spec failed:” with an empty message (`templates/error.html` inside chrome). Live `/health` shows `git_sha` as “—” (`templates/health.html`; `identity.boot_git_sha` returned None), so the operator cannot tell chrome vs process skew. Custom 404s that *do* exist (run not found) still use `error.html` with **no back link**.
- **Why it matters:** A header click that dumps JSON or a blank failure is a trust break. Utility pages can be secondary; they cannot be traps. Health is the only place that should explain “this UI process,” and today it cannot.
- **Recommendation:** (1) HTML 404 handler in `app.py` that always renders `error.html` (never FastAPI JSON) for browser `Accept: text/html`. (2) `error.html`: one line `← Runs` plus the failing path. (3) `/health` must show boot SHA or an explicit “git unreadable — chrome may not match this process.” (4) Fix/restart so `/architecture` serves `architecture.html`; Harness failure should name the pin/version and link `← Runs`. Do not hide the links until they work — make failure in-product.
- **Keep vs reshape:** Keep Architecture as the working-tree map and Harness as the pin inspector. Reshape only failure chrome. Restarting a stale UI is ops, not a new page.

### F3 — No current-page indication

- **Severity:** P1
- **Pages:** all chrome pages
- **Evidence:** Grep of `apps/analysis_web` templates/CSS/JS: no `aria-current`, no `nav-active`, no `.is-active` on header links (sort headers on the runs table *do* use `.is-active` — the list knows the current column; the site does not know the current product). Live `/analyze/new`, `/compares/{id}`, `/runs/research:META:2026-08-23__r3` all show the same nine unstyled links. `_render` in `routes/pages.py` / `analyze.py` / `compares.py` does not pass `request` into Jinja, so `base.html` cannot see the path even if it wanted to.
- **Why it matters:** Wayfinding is “which of these nine am I in?” After a job redirect to `/analyze/{id}` or a compare packet, the header looks like the home page. On phone, Menu does not even show the current name when closed.
- **Recommendation:** Pass `request` (or a `nav` key) from every `_render`. In `base.html`, set `aria-current="page"` on the matching primary prefix (`/` and `/runs` → Runs; `/analyze` → Analyze; `/compares` → Compare; `/portfolio` → Portfolio; utilities similarly). One CSS rule: `.header-links a[aria-current="page"] { color: var(--header-fg); text-decoration: underline; }`. On phone, the closed Menu label can read `Menu · Analyze` when current is not Runs.
- **Keep vs reshape:** Keep the existing `<a>` list. Do not invent a tab component or SPA router.

### F4 — Labels are pipeline jargon, not jobs

- **Severity:** P1
- **Pages:** `base.html` header; `/analyze`, `/analyze/new`; `/compares`, `/compares/new`; `/harness`; `/architecture`; `/calibration`
- **Evidence:** Live brand is **Archive Analysis**; document title suffix is **Stock Research Archive**; page h1s are “Research runs”, “Mode A Analyze”, “Start Mode A analysis”, “Session compares”. Nav says **Compares** (noun pile) vs in-page **Compare selected** / **Compare form** / **New compare** (three labels for one job). **Architecture** is the repo map, not investment architecture. **Harness** and **Calibration** are unexplained. Tagline names `archive/comparisons/` and Mode A. Operator-localhost is the audience — jargon is allowed *on the page* — but the header is the map and it currently teaches the data plane, not the jobs.
- **Why it matters:** “Where do I start a new META analysis?” competes with “what is Mode A vs Compare vs Harness vs Architecture.” Ambiguous Architecture/Harness is why those clicks happen (and then F2 fires).
- **Recommendation:** Chrome copy only, URLs unchanged: brand **Stock Research** (make the `<strong>` in `base.html` an `<a href="/">`); tagline **Completed runs · start analysis · compare sessions**; nav **Compare** (singular); keep Harness/Calibration as words but add a one-line purpose already present on those pages (“How a Mode A run is staged”; “MoS vs later outcomes”). Leave Mode A / pin / packet language on the Analyze and Compare *bodies*.
- **Keep vs reshape:** Keep URL paths (`/analyze`, `/harness`, `/architecture`). Reshape labels. Do not rename `run_id` shapes.

### F5 — Four jobs have no shared map (latest run / new analysis / watch job / compare)

- **Severity:** P1
- **Pages:** `/`, `/runs/{run_id}`, `/analyze`, `/analyze/new`, `/compares`, `/compares/new`, `/compares/{id}`
- **Evidence (live, 2026-09-06):**
  - **Latest META:** `/?ticker_prefix=META` → 200, “5 shown · 5 matching”; sessions `2026-08-23__r3`, `r2`, `2026-08-14`, `2026-08-03`, `2026-07-30`. Default catalog order `ORDER BY ticker, session_date DESC, session_key DESC` (`packages/catalog_api/client.py`) already puts the newest META first. **Credit: live prefix search works.** Gaps: unfiltered `/` is alphabetical (`000660.KS` first, not newest overall); the ticker cell links to **that row’s run**, not a ticker hub; `session_key` is plain text (`partials/runs_table.html`); from `/runs/research:META:2026-08-23__r3` there is no “all META sessions” link and **no sibling compare form** (template gates on `siblings` from `list_runs(..., comparable_only=True)` in `routes/pages.py` — five META rows on the list, zero compare path on the detail).
  - **Start analysis:** `/analyze` → **New analysis**; unknown ticker 404 on `/` offers `Start Mode A analysis for ZZZZNOTICKER` (`partials/runs_table.html`) — **credit that CTA**. No start link on a real ticker’s run detail or on Analyze rows.
  - **Watch a job:** `/analyze` lists 24 jobs, all `complete`, none `running`/`queued`. Header never shows a live count. Header **Analyze** is always `/analyze`, ignoring `?ticker=`. Completed job `/analyze/analyze:COHR:2026-09-03` does **Open catalog run** — that handoff works.
  - **Compare two sessions:** three entries — list checkboxes + **Compare selected** (`static/compares.js` POSTs `/api/compares`); **Compare form** → `/compares/new` (two `<select>`s of the full catalog, live ~20 KB); run-detail picker (absent for META). `/compares` ticker links go to the **packet**, not the runs. Packet detail correctly links `run_id_a` / `run_id_b`.
- **Why it matters:** These four questions *are* the product. Today each has a page, but the graph does not carry ticker context across Runs ↔ Analyze ↔ Compare. You must already know `run_id` / `analyze_id` / `compare_id` to deep-link a record (good) and must reconstruct the ticker by hand to move between lists (bad).
- **Recommendation:** One server-rendered **ticker strip** (not a SPA hub) on run detail, analyze list (when filtered), and compare list: `META · 5 runs · 0 jobs · Start analysis · Compare`. Session column on the runs table becomes a link to `/runs/{run_id}` (ticker can stay as now, or become the strip filter `/?ticker_prefix=META`). On run detail, always list other sessions as links even when `comparable_only` hides the Grok compare form; add `/?ticker_prefix={{ ticker }}` as the crumb next to `← Runs`. Optional: a **Session** sort chip on empty `/` labeled Recent — do not change the default alpha order without a visible control (shareable URLs already encode `sort=session_date&dir=desc`).
- **Keep vs reshape:** Keep live search, checkbox compare, `/analyze/new?ticker=`, identity URLs (`research:META:…`, `analyze:COHR:…`, `compare:MELI:…`). Do not add a `/ticker/META` SPA.

### F6 — Filter memory is Runs-only and invisible

- **Severity:** P1
- **Pages:** `/`, `/runs/{run_id}`, `/analyze`, `/compares`; `static/runs.js`
- **Evidence:** `runs.js` (loaded globally from `base.html`) remembers the last non-empty Runs query in `localStorage` key `analysis_web.runs.query`, rewrites `#nav-runs` and `a.js-runs-back`, does **not** replay storage onto empty `/`, and **Reset** is the only clear. That contract matches `apps/analysis_web/README.md` and the code. **Credit: query memory works as designed** (cannot exercise `localStorage` via curl; the link rewrite and canonicalize/Reset paths are correct). Live `← Runs` on META detail is `href="/"` until JS runs — no-JS still lands on default list. Analyze `GET /analyze?ticker=COHR` filters to one job but header Analyze stays `/analyze`. Compares ticker filter is the same. Nav never shows that Runs will restore `ticker_prefix=META`.
- **Why it matters:** Remembered filters are a wayfinding feature that looks like a bug if the label still says “Runs”. Analyze/Compares filters that die on the next header click train people not to filter those lists.
- **Recommendation:** Keep Runs memory; do not replay onto empty `/`. Surface it: when storage is non-empty, `#nav-runs` text becomes `Runs · META` (or `Runs · filtered`) from the same `syncLinks()` in `runs.js`. Either reuse that tiny pattern for Analyze/Compares ticker query **or** drop those list filters and send people through the Runs strip (F5). Reset remains the only clear.
- **Keep vs reshape:** Keep the mechanism (address bar is the working set; storage only rewrites links). Reshape visibility. Do not auto-apply storage on `/`.

### F7 — Dead-ends: errors, empty utilities, no crumbs

- **Severity:** P1
- **Pages:** `error.html`; `/runs/{missing}`; `/artifact`; `/calibration`; `/experiments`; `/portfolio`; `/health`
- **Evidence:** Live `/runs/nope` → “Run not found: nope”, chrome, **zero content links**. `templates/error.html` is a card and a message. Live `/calibration` → “Joined rows: 0”, empty table, **no links** out of `<main>`. Live `/experiments` → one `<h2>(none)</h2>` and a dump of catalog rows linked to `/runs/…` — no `/?experiment_id=` (template never emits it; `page_experiments` collapses untagged-all into a fake group). Live `/portfolio` → “Portfolio · default”, no book, copy/import CLI only, **0 content links**. `/health` is a stats table with no outbound. Contrast: `/analyze/new`, `/analyze/{id}`, `/compares/new`, `/compares/{id}` all have `← Analyze` / `← Compares`; META README artifact has `← Run` to `/runs/research:META:2026-08-23__r3` — those crumbs work.
- **Why it matters:** A map with trap doors is not a map. Empty Calibration/Experiments/Portfolio occupying peer nav (F1) is worse because they do not offer a next click into the primary loop.
- **Recommendation:** `error.html`: `← Runs`. Experiments: if the only bucket is `(none)`, show “No tagged experiments” + link to `/` — do not clone the runs table; when ids exist, `h2` links to `/?experiment_id=`. Calibration empty state: one sentence + `← Runs` (when buckets have `n`, link `/?mos_min=&mos_max=`). Portfolio empty: keep the CLI, add `← Runs` and `/analyze/new`. Health: one line “Catalog has N runs” linking `/`.
- **Keep vs reshape:** Keep these pages. Reshape empty states into exits. Do not delete Health.

### F8 — Experiments and Calibration are a second Runs list and a closed report

- **Severity:** P1
- **Pages:** `/experiments`, `/calibration`
- **Evidence:** Live Experiments title “Grouped from catalog runs (limit 500 scan)”; single group `(none)` because `page_experiments` only uses `kind: none` when there is **more than one** experiment id (`routes/pages.py`). Calibration is a horizon form and a bucket table with no per-run or per-ticker hrefs (`templates/calibration.html`). Both are header peers equal to Runs.
- **Why it matters:** After F1 grouping, these still need a job. As shipped they compete with `/` without adding a different question (except Calibration’s hit-rate math, which currently has no rows).
- **Recommendation:** Demote per F1. On the pages: Experiments is a **filter index** (ids → `/?experiment_id=`), not a 500-row clone. Calibration stays a report; wire buckets to Runs queries when `n_scored > 0`. No new nav items.
- **Keep vs reshape:** Keep the sqlite joins and the URLs. Reshape information role.

### F9 — Deep-link IDs are strong; entity navigation is weak

- **Severity:** P1
- **Pages:** `/runs/{run_id}`, `/analyze/{analyze_id}`, `/compares/{compare_id}`, `/artifact`, `/analyze-artifact`, `/compare-artifact`
- **Evidence:** Live IDs in the address bar (`research:META:2026-08-23__r3`, `analyze:COHR:2026-09-03`, `compare:MELI:2026-08-26__2026-08-23__r2_vs_2026-08-24`) match `ARCHITECTURE.md` § Identity and are bookmarkable. Artifact query params `run_id` + `path` work; `raw=1` on reports. Legacy `/run?run_id=test` 302 → `/runs/test`. **Shareable Runs queries work** (live META URL `/?ticker_prefix=META`). What requires prior knowledge: any detail URL (you cannot browse to a run without an id). From a run, you cannot list the ticker’s Analyze jobs or Compare packets. Compare packet files are deep-linked; some in-body “99_synthesis.md” hrefs are relative (live MELI page) and only work if the browser is already on `/compares/{id}`.
- **Why it matters:** Operators paste IDs in chat — keep that. Operators also think in tickers. The site is ID-native and ticker-poor once you leave `/`.
- **Recommendation:** Implement the F5 ticker strip; add `/?ticker_prefix=` crumb on every run/analyze/compare detail. Leave ID URLs stable. Fix compare markdown relative links in the existing sanitizer/render path only if they 404 off-packet — do not invent a second ID scheme.
- **Keep vs reshape:** Keep identity strings and query-string artifacts. Reshape cross-links.

### F10 — Small wayfinding nits (one bucket)

- **Severity:** P2
- **Pages:** chrome, `/`, `/compares*`
- **Evidence / recommendation (merged):** Brand `<strong>Archive Analysis</strong>` is not a home link. `/runs` duplicates `/` with no canonical hint. Three Compare CTAs (“Compare selected”, “Compare form”, “New compare”) — pick **Compare** / **New compare**. Phone hides the tagline, so F4 jargon is replaced by nothing. `runs.js` loads on every page (correct for nav rewrite; fine). Default `limit=50` omitted from query string — keep.
- **Why it matters:** Polish after F1–F9.
- **Keep vs reshape:** Nits only.

## Site graph (live)

```
Header (9 peers, no current, brand not a link)
│
├─ /  Runs  [live search + query memory + checkbox compare]
│     ├─ /?ticker_prefix=META          shareable hub (newest META first)
│     ├─ /?ticker_prefix=UNKNOWN       404 abort + Start analysis CTA
│     ├─ /runs/{run_id}                needs run_id
│     │     ├─ ← Runs (JS may restore query)
│     │     ├─ /artifact?run_id&path   ← Run
│     │     └─ sibling Compare form    (absent live on META)
│     └─ /compares/new                 “Compare form”
│
├─ /analyze  job list (filter ticker is URL-only, not remembered)
│     ├─ /analyze/new [?ticker=]       ← Analyze
│     └─ /analyze/{analyze_id}         needs analyze_id
│           ├─ /analyze-artifact       ← Analyze
│           └─ /runs/{run_id}          if snapshot ready
│
├─ /compares  packet list
│     ├─ /compares/new                 ← Compares; two full-catalog selects
│     └─ /compares/{compare_id}        needs compare_id
│           ├─ /runs/{a} /runs/{b}
│           └─ /compare-artifact       ← Compare
│
├─ /portfolio     empty book → CLI only (dead-end)
├─ /experiments   “(none)” dump → /runs/{id} (not a filter index)
├─ /calibration   0 joined rows (dead-end)
├─ /health        stats, git_sha —
├─ /harness       ERROR card (workflow_spec failed)
└─ /architecture  JSON 404, no chrome
```

Dead-ends: Architecture (out of product), Harness error, Calibration, empty Portfolio, `error.html`, Health. Requires an id: run / analyze / compare details and all artifact views.

## What already works

- Live Runs prefix search, facets, range filters, column sort, shareable query strings (`/?ticker_prefix=META` returned five sessions, newest first).
- Query memory in `static/runs.js`: header **Runs** and run-detail **← Runs** rewrite to the stored query; empty `/` stays the default list; **Reset** clears. Do not “add search.”
- Unknown-ticker abort (HTTP 404) plus **Start Mode A analysis for {ticker}** — the one place the graph teaches “list vs start.”
- Identity URLs and legacy `/run?run_id=` → `/runs/…`.
- Parent crumbs on Analyze/Compare new + detail; artifact `← Run` / `← Analyze` / `← Compare` when `back_href` is passed.
- Completed Analyze → **Open catalog run**; Compare detail → both `run_id`s.
- Checkbox two-same-ticker Compare from the list (`compares.js`) without leaving Runs.
- Phone **Menu** disclose and 44px targets (shipped; grouping should reuse it).
- Night/Light in the header, not in the archive.

## From-scratch keepers

If redesigning tomorrow, keep:

1. Server-rendered pages and shareable GET queries (not a SPA).
2. `/` as the working set of completed runs, with live search and link-only query memory.
3. One reading object: the run. Artifacts hang off it. Jobs and compare packets are separate ID types.
4. The four primary jobs (Runs, Analyze, Compare, Portfolio) as real pages.
5. Abort-don’t-pretend-empty for unknown tickers, with a start-analysis exit.
6. Header Menu disclose on phone; one chrome token table.
7. Utility pages (Harness map, Architecture map, Health, Calibration) as *secondary* HTML, not a second product.

## Do not do

- Do not rewrite as a SPA or add a client-side router so “nav can highlight.”
- Do not add a mega-menu, icon rail, or a tenth peer link.
- Do not invent fair values, a second MoS, or a blended compare FV.
- Do not replay `localStorage` onto empty `/` (breaks the default list and pasted URLs).
- Do not build `/ticker/META` as a JavaScript dashboard; the query URL is the hub.
- Do not hide Health/Harness/Architecture; demote them and make their failures in-chrome.
- Do not rename `research:` / `analyze:` / `compare:` IDs.
- Do not commit or mutate `archive/research/**` / `archive/outcomes/**` to “fix” this review.
