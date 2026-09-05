# Plan: comfortable phone use of the analysis website

**Branch:** `ui-phone-comfortable` (do not merge).  
**Work type:** W4. No `harness/VERSION` bump. No catalog, jobs, or archive writes.

**Review (2026-09-05):** Direction mixed → reshape. Two candidates applied: (1) `.stack-table` is only entity row-lists (not Health / property-row tables); hide class is `desktop-only`; empty colspan stays a message. (2) One checkbox-disclosure CSS module in slice 1; slice 3 reuses it for extra filters — not a leftover-page tour. Chart 220px stage is already done. Three slices kept.

## Goal

A person can use the analysis website on a phone without sideways-reading 13-column tables or a header that eats the screen. Desktop layout stays as it is today. Same routes, same data, same JS contracts (live quotes, compare picks, live table swap).

Done means: on a ~390px-wide viewport, (1) nav is a Menu control, (2) Runs and Portfolio **positions** read as stacked cards with the numbers that matter, (3) Runs filters are collapsed except ticker + Filter + Reset, (4) other entity lists use the same stack-table, (5) tests + `eng_verify` green, (6) browser check at desktop and phone widths.

## Current shape

One FastAPI + Jinja app. Every page extends `apps/analysis_web/templates/base.html`.

- Viewport meta is already set. `app.css` already stacks `.grid2` and shrinks the chart / perf bars at `max-width: 800px`. Harness already stacks its side panel at 900px and horizontally scrolls the pipeline.
- Header is a dark bar with a long tagline and **nine** links plus Night/Light. Links `flex-wrap`; there is no Menu.
- Runs (`partials/runs_table.html`) is a **13-column** HTML table. Live reload swaps that fragment. Compare checkboxes and `quotes.js` bind to cells in that same table. Portfolio positions can also be 13 columns.
- Filters on `/` are two wrapping rows of inputs (`min-width: 7rem`). Compare selects are `min-width: 16rem`.
- Other **entity** list pages (Analyze jobs, Compares, Experiments, Calibration) are narrower tables with no card restyle.
- Health, Portfolio NAV/perf summaries, run-detail valuation, and compare metadata are **property-row** tables (`th`+`td` per field). They already read on a phone.
- No hamburger, no `data-label`, no filter disclosure, no 44px tap targets.

Home of presentation: `static/app.css`. Harness extras: `static/harness.css`. No Python change is required for layout.

## Design it twice

| | A — one markup, CSS restyles at 800px | B — second card markup (JS or extra templates) |
|---|---|---|
| Runs / Portfolio | Same `<table>`; `@media` hides `thead`, stacks `tr` as cards, labels from `data-label` | Clone each row into a `<div class="card">` (or a mobile-only Jinja block) |
| Live quotes / compare / live swap | Unchanged DOM; `quotes.js` and `compares.js` keep working | Must keep both trees in sync on every fragment swap |
| Nav | Checkbox + label Menu; CSS shows/hides the panel | Extra JS drawer |
| Common case | One table, one CSS module | Two UIs for one list |

**Winner: A.** Presentation belongs in CSS. The from-scratch design of this site, if phone had been a requirement on day one, is still one HTML table of runs and one header nav — not a second component tree. Duplicating rows is change amplification (every new column, live cell, and checkbox would be edited twice).

Keep the existing **800px** breakpoint. Do not add a second policy. Leave harness workspace at 900px.

## Shared module: checkbox disclosure

One CSS contract, introduced in slice 1, reused in slice 3:

- Hidden checkbox (`.disclose`) + label (`.disclose-btn`) + sibling panel (`.disclose-panel`).
- Desktop: label hidden; panel always shown (existing layout).
- Phone (800px): label shown (≥44px); panel hidden until `:checked`.
- Comment this contract next to the rules. Do not invent a second checkbox hack for Filters.

## Slices (3)

Each slice is one abstraction, shippable and committable on this branch.

### Slice 1 — Narrow chrome

**Abstraction:** shared header is a compact phone bar; disclosure module exists.

- Hide `.header-tagline` below 800px.
- Menu uses the disclosure module (no new JS). Desktop: Menu hidden, links in a row as today. Phone: links hidden until checked; then a vertical list under the bar (`flex-basis: 100%`). Theme toggle stays visible.
- Tap targets ≥44px for header links, Menu, theme button — **inside the 800px query only** (desktop visual freeze).
- `main` padding stays; no new max-width.

Files: `templates/base.html`, `static/app.css`, tests on markup + CSS, README one line.

### Slice 2 — Stack tables (entity row-lists only)

**Abstraction:** `.stack-table` is an opt-in presentation for **one-entity-per-row** lists.

Markup:

- Class `stack-table` on those `<table>`s (Runs keeps `runs-table` too).
- Each body cell gets `data-label` matching the column header (not `nth-child` — Portfolio IB columns are conditional).
- Secondary cells get `desktop-only` (hidden on phone, visible on desktop).
- Empty bodies (`colspan` “No runs”, Calibration empty) stay **one muted message**. CSS: no `::before` label on `td[colspan]`.
- At 800px the **row** is the card. The wrapping page `.card` is not restyled into a second chrome box.

CSS below 800px (comment the contract above the rules):

- `thead { display: none }`
- `tr` becomes a card; `td` is a labeled row (`::before { content: attr(data-label) }`)
- `td.pick` stays a leading checkbox row without a noisy label
- `td.desktop-only { display: none }`

**Opt-in list (only these):**

| Table | Show on phone | `desktop-only` |
|-------|----------------|----------------|
| Runs | pick, Ticker, Session, As-of, Live, FV base, MoS %, Downside %, Audit | Harness, Sector, Region, Tech |
| Portfolio **positions** | Symbol, Weight, Price, FV base, MoS %, Audit, Session | Exch, Qty, Close, Value, Tech, Sector |
| Analyze jobs | all columns | none |
| Compares | all columns | none |
| Experiments (per-section run list) | all columns | none |
| Calibration buckets | all columns | none |

**Do not** add `.stack-table` to: Health, Portfolio summary / `perf-table`, compare metadata, compare headline matrix, packet file indexes, run-detail valuation/context.

Sort-by-column is **desktop-only** (thead is gone on phone). Filters still work. Do not invent a second sort control.

Do not change `compares.js` / `quotes.js` / live fragment swap. Labels live in `partials/runs_table.html` (the only Runs table; `/fragments/runs` uses it).

### Slice 3 — Secondary controls

**Abstraction:** extra filters yield the screen; the disclosure module is reused.

- **Runs filters:** ticker + Filter + Reset stay visible (always-on). Sector/region/audit/tech/harness/experiment/limit and all range pairs sit in a `.disclose-panel`. Hidden `sort`/`dir` stay in the always-on form so live `runs.js` still serializes every `[name]` (collapsed ≠ omitted).
- Desktop: Filters label hidden; all rows visible as today.
- Compare `<select>` drops `min-width: 16rem` at 800px. Compare bar already wraps.
- Analyze/new and similar stacked forms: labels full width, inputs 100%, tap-sized buttons **inside the 800px query**.
- Chart already has a 220px stage at 800px — do not relist it as work. Range chips inherit the same tap-size rule if they are too small.
- Do not tour Architecture / Harness as features. Existing stack + pipeline scroll stays. If a control there is too small, it inherits the tap-size rule.

## What to change (by slice)

| Slice | Files |
|-------|--------|
| 1 | `templates/base.html`, `static/app.css`, `apps/analysis_web/tests/test_analysis_web.py`, `apps/analysis_web/README.md` |
| 2 | `templates/partials/runs_table.html`, `templates/portfolio.html` (positions table only), `templates/analyze.html`, `templates/compares.html`, `templates/experiments.html`, `templates/calibration.html`, `static/app.css`, tests |
| 3 | `templates/runs.html`, `static/app.css`, maybe `templates/analyze_new.html` / `compare_new.html`, tests, README |

**Leave `ARCHITECTURE.md`.** No new page, route, CLI, archive plane, or identity. README owns “pages reflow below 800px.”

**Python / catalog / JS behavior:** none, unless a template change accidentally breaks a test selector.

## Tests

CSS/HTML assertions in `test_analysis_web.py` (same style as theme tests):

- Slice 1: base has `id="nav-open"` + `for="nav-open"`; `.disclose` / `.disclose-btn` / `.disclose-panel` exist; `@media (max-width: 800px)` hides `.header-tagline` and `.disclose-btn` is shown there; desktop rules do not hide `.header-links`.
- Slice 2: home HTML includes `stack-table` and `data-label="Ticker"` (and Live / MoS); `desktop-only` present for Harness/Sector/Region/Tech; CSS has `content: attr(data-label)` inside the 800px query; `/fragments/runs` still contains `runs-table` and compare-pick; Health HTML does **not** use `stack-table`.
- Slice 3: home HTML has Filters disclosure (`id="filters-open"`); ticker input is **not** inside that panel; hidden `sort`/`dir` still in the form.

Keep existing theme cascade tests intact (`:root` / dark / media regex).

Browser (when implementing): 1100px and ~390px on `/`, a run detail, `/portfolio`, `/analyze`. Confirm compare checkbox + live quote cell still present in the stacked Runs card. Desktop: no Menu button, full tables, all filters visible.

## Non-goals

- A separate mobile app, PWA, or new routes.
- User-agent sniffing or a second Jinja tree.
- Changing sort, filter semantics, live reload, quotes, or compare rules.
- A phone sort dropdown (later).
- Touch-pan rewrite of the price chart or mermaid.
- Native hamburger animation / drawer overlay covering the page.
- Applying `.stack-table` to property-row tables.
- `harness/VERSION` bump.

## Verify

```bash
python -m pytest apps/analysis_web/tests -q
python scripts/eng_verify.py
```

Plus the browser pass above for each slice that changes a visible surface.

## Risks

- `display: block` on `table`/`td` can fight `.num` alignment — cards use a label/value flex row instead of `text-align: right` alone.
- Live fragment swap must include `stack-table` + `data-label` or phone layout regresses after a catalog event.
- Checkbox nav is not a `details` element; label must stay associated (`for`/`id`) for a11y.
- Hiding columns on phone is a product choice: those values remain on desktop and on the run-detail page.

## Commit policy

User asked: commit each finished slice via `/smart-commit`; **do not merge**. Session files (`eng/sessions/2026-09-05-ui-phone-comfortable/`) ride with slice 1, then progress updates on later slices.
