# Plan: post-compose UI/UX fixes (after SDR)

Parent: `eng/sessions/2026-09-06-ui-ux-review/`
Findings: `handoffs/review-post-compose.md`
SDR absorb: `handoffs/SDR_ABSORB_POST_COMPOSE.md`
Branch: `ui-ux-compose`. Work type **W4**. No `harness/VERSION` bump. No SPA. No second fair value.
Live UI: one process `python -m apps.analysis_web --no-auto-restart --port 8765`.

Waves 1–5 already shipped (`PLAN.md`). This file is the **remainder**. Do not re-propose Menu, stack-table, theme switch, HTML 404, football PNG, or CIO title as new products.

Strategic design review of the first remainder draft: **mixed / reshape**. This document is split **B** (operator-surface sessions). CSS and Jinja travel with the feature. One writer at a time is implied by sequence, not by a CSS warehouse.

## North star leftover

An operator opening localhost should, in a few seconds:

1. See **latest completed research per name** (not a 50-row All dump).
2. Read **cheap vs base (MoS)** and **cheap vs bear (Downside)** without confusing them with **Audit PASS** (process) or duration **pass** (do not initiate).
3. Notice an in-flight Analyze without leaving Runs, then open the job.
4. On a run: **call → cone → CIO cover**, then the tape chart.

## Locked product choices

| Decision | Choice |
|----------|--------|
| Home grain | Brand + `#nav-runs` href = `/?latest=1`. Empty `/` and Reset stay **All** (shareable URL). Do not unique LIMIT 50 in Python. |
| Duration copy | Display map in `templating.py` only. Stored `decision_action` unchanged. `pass` → **Do not initiate**. Never `verdict_badge`. |
| Cheap claim | `franchise_mos` → **Franchise MoS** (underscore → spaces). Strip only, not a 10th list column. |
| `verdict_line` | Bleach-render as a paragraph in `templating.py`. Wave 8 applies it. |
| Night through-bear | Token `--below-bear` in **both** dark tables. Ink only, no fill, not `.badge.fail`. ≥4.5:1 on `--card`. |
| SR blotter | Delete `aria-label` from `data-label`. Visually hidden `.cell-label` span. Phone `thead` stays `display:none`. |
| Compare vs Latest | On Latest, picker stays disabled. Hint + link to All for that ticker. Compare from the run sheet (Wave 8). |
| Phase ids | No English map. Hide `#job-phase` when `resume_hint` is non-empty. |
| Banner | `page_runs` receives `[{ticker, href}, …]` (cap ~3). Template does not see raw job dicts. Isolation in `apps/analysis_web/services/` — do not import `research_jobs` into `pages.py`. |
| Siblings | Wave 8: two named lists — `sibling_links` (all other catalog sessions) and `comparable_siblings` (Grok `<select>`). |

## Keep / do not

**Keep:** FastAPI + Jinja + small JS. Catalog-only FV/MoS. Downside display math. One chrome token table. `.stack-table` + `.disclose`. `RunQuery.latest` SQL grain. Identity URLs. Agent 6 football PNG. `render_session_report` ≠ sanitizer. IB book + latest-per-ticker as the watchlist.

**Do not:** SPA / `/ticker/META` hub. Invent live MoS or blended compare FV. Relabel Audit PASS as a buy list. Sticky header. Unify router `_error()` copies. Restyle `harness.css`. Pagination. Desktop 44px everywhere. `phase_current` English map. Rewrite `archive/research/**` or `archive/outcomes/**`. `git commit` until the user agrees.

## Design it twice (split of work)

| | A — exclusive file owners (rejected) | B — operator surfaces (winner) |
|---|---|---|
| Wave 6 | CSS warehouse: pre-land `.table-scroll`, disabled-Compare, stack-form for later waves | **Readable:** Night AA, SR hears numbers, chrome `--muted`. CSS that *is* this surface. |
| Wave 7 | Duration + Latest hrefs; banner and Apply wait for Wave 9 | **Scan:** `/` is Latest + English Duration + in-flight names + Apply. Whole `runs.html`. |
| Wave 8 | `run_detail.html` after Wave 7 already touched the strip | **Sheet:** cover-first page. `.table-scroll` lands here. Two sibling lists. |
| Wave 9 | Watch + leftover chrome (Filter, portfolio path, favicon, compare labels, `pages.py` banner) | **Job:** wait page is `resume_hint`; complete offers Open catalog run / Read CIO cover. |

Winner **B**. One writer at a time follows from the sequence below, not from a warehouse session.

---

## Wave 6 — `ui-readable` (P0)

**Interface:** Night signed ink meets AA; screen readers hear blotter numbers; chrome words use `--muted`.

**Owns:** `app.css` (tokens and list/chrome only), `static/runs.js` (`labelStackedCells` delete), cell-label markup in `partials/runs_table.html` and `portfolio.html`, favicon (`static/favicon.ico` or `GET /favicon.ico` → 204).

**Must not:** Duration copy, Latest hrefs, `.table-scroll`, `#compare-btn:disabled`, `run_detail.html` order, `base.html` hrefs, analyze wait JS.

### Slices

1. **`--below-bear` (F1).** Light `:root` `#7f1d1d`. Dark `html[data-theme="dark"]` **and** `prefers-color-scheme` twin: `#fca5a5` (or measured ≥4.5:1 on `--card`). `.below-bear { color: var(--below-bear); background: none; }`. Delete the Light-only hex.

2. **Header words (F8).** `.header-tagline` and `.header-lab a` → `var(--muted)`. Lab stays 0.9rem; current Lab link `--header-fg`. Global `a:focus-visible, button:focus-visible` (2px `var(--link)`). Do not restyle `#theme-toggle` besides outline.

3. **SR names (F2).** Delete `labelStackedCells` and its call sites in `runs.js`. Each `td[data-label]` starts with `<span class="cell-label">…</span>` then the value. `.cell-label` uses the clip recipe (not `display:none`). Sighted cards still use `::before`. Keep pick `th` `aria-label="Select for compare"`.

4. **Same-surface CSS.** Scope uppercase `th` to `thead th`. Lift `.stack-form` input/select **skin** to the base sheet; keep 16px / 44px inside the 1100px query. Desktop (min-width 1101px) `.runs-table` (or its card) `overflow-x: auto` so Region/Tech do not stick out of the 1100px card. Drop `tr:hover` on tables without `thead`. Delete dead `.chart-stage { height: 220px }` leftover.

5. **Favicon.** Tiny `static/favicon.ico` or 204 on `/favicon.ico` so the console is not a 404 on every page.

### Verify

- Pytest: home HTML has `.cell-label`; no `aria-label="MoS"` on a value `td`.
- Playwright Night: `.below-bear` contrast ≥4.5:1 vs `--card`.
- First Tab is still Skip to content; desktop `#nav-open` is not a tab stop.

---

## Wave 7 — `ui-scan` (P1 morning `/`)

**Start after Wave 6** (`runs_table.html` cell-label already there; `app.css` free).

**Interface:** Opening Runs is latest-per-name; Duration is English and `.decision`; Compare explains Latest; in-flight names sit above the blotter.

**Owns:** `templating.py` filters (`duration_label`, `cheap_claim_label`, bleach `verdict_line` as a paragraph), Duration/cheap cells (preserve Wave 6 `.cell-label`), **entire** `runs.html` (legend, Apply vs Filters, banner), `base.html` brand + `#nav-runs`, `runs.js` empty stored query → `/?latest=1` on chrome links only, `compares.js` Latest hint, `#compare-btn:disabled` look in `app.css`, `page_runs` banner via a small service, portfolio Duration cells + empty-book copy.

**Must not:** `run_detail.html` (filters exist; the sheet applies them in Wave 8), analyze wait templates.

### Slices

1. **Duration map.** `pass` → Do not initiate; `too_hard` → Too hard; others title-case (`initiate` → Initiate). Unknown: `_` → spaces. Filter `duration_label`. Print that string; `title` = stored token. Class `decision` on the Duration `td`. Audit stays `verdict_badge`. Legend: “Duration = stored action · Audit = process completeness.” Same filter on portfolio.

2. **Cheap-claim map.** `franchise_mos` → Franchise MoS; `equity_near_book` → Equity near book; `residual_option` → Residual option; `not_cheap` → Not cheap. Filter `cheap_claim_label`. Used on the run strip in Wave 8; Wave 7 registers the filter.

3. **`verdict_line` helper.** One bleach-markdown paragraph helper in `templating.py` (or `render_markdown.py` next to the existing sanitizer). Wave 8 is the only template that calls it.

4. **Latest is chrome home.** `base.html`: brand and `#nav-runs` default `href="/?latest=1"`. Empty `/` **still omits** `latest` (keep the All dump test). Reset stays `/`. In `runs.js`, next to `pathFromStored`: empty `/` stays All and is **never** rewritten from storage; `#nav-runs` / `.js-runs-back` are `/?latest=1` when storage is empty.

5. **Compare vs Latest.** `compares.js`: on `latest=1`, Compare stays disabled; hint “Latest shows one row per name. Switch to All to pick two sessions of {ticker}.” link `/?ticker_prefix={ticker}`. `#compare-btn:disabled` uses secondary/opacity, not a loud primary.

6. **In-flight banner.** New `apps/analysis_web/services/` helper returns `list[{ticker, href}]` (running/queued Analyze, cap ~3, optional “and N more”). `page_runs` passes that list only. **Do not** import `research_jobs` in `pages.py`. No SSE. No fragments.

7. **Apply vs Filters.** Submit button **Apply**. Disclose label **Filters**.

8. **Portfolio empty.** No absolute disk path. “No IB book yet. Import an activity statement or copy `portfolio.example.json` to `.local/`.”

### Verify

- 4516.T Duration on `/` = “Do not initiate”; Audit still green PASS.
- `GET /?latest=1` ≤1 row per ticker; `GET /` still All.
- Brand lands on Latest. Reset lands on All.
- On Latest, one pick does not enable Compare; hint links to All.
- Home banner absent when no running jobs.

---

## Wave 8 — `ui-sheet` (P1 reading)

**Start after Wave 7** (shared `app.css` / `pages.py` / strip voice).

**Interface:** Open a run → strip → cone + CIO cover → tape. Phone nested tables scroll inside a wrapper.

**Owns:** `run_detail.html`, `routes/pages.py` (`page_run` only), `.table-scroll` in `app.css`.

**Must not:** `templating.py`, `runs.js`, blotter columns, `runs.html`.

### Slices

1. **Page order.** After the decision strip, same first card: football `<img>` (or muted missing) + **Read CIO cover** as `.btn` → Price vs analysis → Context. Duplicate Valuation table in `<details>` (“Bear / base / bull / model”). Drop `.mono` on the ticker `h1`; keep `run_id` muted. Compare form card **after** the envelope/cover.

2. **Apply Wave 7 filters.** Duration + cheap-claim maps and bleach `verdict_line` on the strip/subhead. No unsanitized `| safe`.

3. **Two sibling lists.** `page_run` passes:
   - **`sibling_links`**: other catalog sessions of the ticker as `/runs/{id}` (always rendered; empty = “No other catalog sessions”).
   - **`comparable_siblings`**: existing `comparable_only` set that gates the Grok `<select>`.
   Do not reuse today’s `siblings` with a template flag. Chart overlay keeps the comparable set it already gets.

4. **`.table-scroll`.** Wrap strip, Context, and Valuation `<details>` tables. `overflow-x: auto; max-width: 100%`. Do not `.stack-table` property-row tables.

### Verify

- Playwright 4516.T: football + “Read CIO cover” **above** the chart and Compare form. `verdict_line` has no raw `**` / backticks.
- 390px run sheet: `scrollWidth == clientWidth`.
- CIO artifact still one H1 titled as cover.

---

## Wave 9 — `ui-job` (P1 wait page)

**Start after Wave 6.** **Parallel with Wave 8 only** — this recut no longer touches `pages.py` or `runs.html`.

**Interface:** The wait page is `resume_hint`; complete offers Open catalog run / Read CIO cover as `.btn`.

**Owns:** `analyze_detail.html`, `static/analyze_detail.js`, and `analyze.html` phase column **only if that file is already open**.

**Must not:** `app.css`, `run_detail.html`, `runs.html`, `routes/pages.py`.

### Slices

1. Hide `#job-phase` when `resume_hint` is non-empty (template + JS patch). Keep `<meta refresh=15>` while running.
2. Complete: `.btn` “Open catalog run”; if README allowlisted, “Read CIO cover”. Artifact `<ul>` stays.
3. Reconcile/abandon copy stays `.muted` unless status is failed/cancelled/abandoned. Do not map `orch`.

Not this wave (unless the owning file is already open): Compare A/B labels, synthesis-above-headline, `error.html` `nav.label`.

### Verify

- Complete job: no adjacent `phase orch` when `resume_hint` exists; “Open catalog run” is a button.

---

## File ownership

| Wave | Owns | Must not |
|------|------|----------|
| 6 readable | `app.css` (contrast, SR clip, list overflow, stack-form skin, favicon) | Duration copy, Latest hrefs, `.table-scroll`, `#compare-btn:disabled`, run-detail |
| 7 scan | `templating.py` filters, entire `runs.html`, `base.html` hrefs, `runs.js` home grain, `compares.js`, banner service, `#compare-btn:disabled`, portfolio cells/empty | `run_detail.html`, analyze wait templates |
| 8 sheet | `run_detail.html`, `page_run`, `.table-scroll` | `templating.py`, `runs.js`, blotter columns, `runs.html` |
| 9 job | `analyze_detail.html` + js | `app.css`, `run_detail.html`, `runs.html`, `pages.py` |

```text
Wave 6  ui-readable
Wave 7  ui-scan          after Wave 6
Wave 8  ui-sheet         after Wave 7
Wave 9  ui-job           after Wave 6; parallel with Wave 8
```

Do not run two writers on `app.css` at once (6 then 7 then 8). Do not run two writers on `pages.py` at once (7 banner then 8 `page_run` — Wave 9 no longer writes it).

## Out of scope

- Ticker strip `META · 5 runs · Start · Compare`
- Pagination beyond Latest
- `phase_current` English map
- Unify `_error()` helpers
- Calibration scatter / outcome bars
- Harness pipeline / fake tablist
- Desktop 44px on every control
- Query-memory chip on `#nav-runs`
- `fmt_num` dropping `.00` on large KRW
- Compare A/B labels / synthesis card order / `error.html` back label (not Wave 9)

## Implementation loop (each wave)

1. Scaffold `eng/sessions/2026-09-07-ui-<slug>/` with `feature_list.json` + `AGENT_BRIEF.md` pointing at this file.
2. Baseline `python scripts/eng_verify.py`.
3. Implement. Boot `--no-auto-restart --port 8765`.
4. Pytest `apps/analysis_web/tests` + Playwright the wave Verify table (1440, Night, 390).
5. Verifier flips `passes`. **No `git commit` until the user agrees.**

## Suggested first session paste

```
Mode B W4. Branch ui-ux-compose.

Read eng/AGENTS.md, then eng/sessions/2026-09-06-ui-ux-review/PLAN_POST_COMPOSE.md
Wave 6 (ui-readable) only.

Night --below-bear, header --muted, delete labelStackedCells, .cell-label,
list overflow, stack-form skin, favicon. Do not start Wave 7. Do not add
.table-scroll or Latest hrefs.

Boot python -m apps.analysis_web --no-auto-restart --port 8765.
Verify pytest apps/analysis_web/tests and Night contrast on .below-bear.
Do not git commit until I agree.
```
