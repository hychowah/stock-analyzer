# Strategic design review — Wave 4b ui-a11y-phone

Grain: Plan (Session 5 / child `eng/sessions/2026-09-06-ui-a11y-phone/`).
Constraints honored: one table + CSS restyle (no second card markup); no sticky site header; do not reorder runs columns; do not implement; do not edit `PLAN.md`.

## Verdict
- **Direction:** `mixed`
- **Why:** The work is to make already-shipped phone chrome keyboardable and to turn stacked cards on at `main`’s width (landscape phone / tablet), not to invent a second UI. Designed today that is two deep modules: (1) one named narrow-layout contract in `app.css` at 1100px covering Menu, stack-table, forms, 44px, overflow, architecture frame, and the chart-stage *query*; (2) one list-replacement contract — a live node outside `#runs-results` plus a table-updated event. The brief is still that structure *plus* a finding-by-finding bag: clip-thead (recreates the invisible tab stop this session exists to kill), a second 900px harness policy, and an underspecified fragment/error/compare handshake.
- **Do:** `reshape`

## Keep
- Product shape A from the parent plan and from `2026-09-05-ui-phone-comfortable`: one entity `<table>`, `.stack-table` + `data-label` restyle, one checkbox-disclosure module. Do not clone cards for live quotes or compare picks.
- Raise the existing phone query to **1100px** (`main { max-width: 1100px }`). One policy in `app.css`. No orientation query, no second breakpoint for Menu vs table vs 44px. Desktop visual freeze stays behind `min-width: 1101px`.
- Disclose: **class-level** `display: none` on `.disclose` and `.disclose-btn` when wide — that defines the checkbox out of the tab order and covers Menu, Wave 2’s Lab disclose, and Filters. Phone: keep the CSS hack; name from the visible label; `:focus-visible` ring on `.disclose-btn`. Do not special-case `#nav-open`.
- Skip link and `aria-current` stay in `ui-nav-ia`. This session does not re-propose nav grouping.
- Contrast lives in the **one token table** (both `html[data-theme="dark"]` *and* the `prefers-color-scheme` copy). Night `--btn-bg` ≥ 4.5:1 with white (`#2563eb`). Point word uses (`.quote-kind`, `.chart-grid text`) at `--muted`. Leave `--faint` for non-text (sibling strokes, perf-bar default, header tagline). Do not invert semantic greens/reds.
- No sticky **site** header. `#compare-bar` may stick to the bottom of `main` **only while a pick is on**. Compare stays checkbox-in-the-row; 44px hit is CSS on `td.pick`, not a second picker.
- Report/matrix tables get a local `overflow-x: auto` scroller. They do not become `.stack-table`.
- Fragment swap stays HTML, not a SPA. Do not dispatch `catalog-changed` to refresh the compare bar (that re-fetches the table). Do not live-announce every Yahoo tick.
- File split vs Wave 4a: this session owns the **media-query width** in `app.css`. `ui-run-reading` owns `price_chart.js` and may change `.chart-stage` **height** inside the 1100px block. Do not reorder runs columns (`ui-decision-blotter`). If blotter has not landed, keep `data-label` aligned with whatever headers exist.
- Architecture: keep framed mermaid + Reset; `controlIconsEnabled: true` is the non-drag equivalent. Do not write a pinch engine.
- Tests: the 09-05 phone tests never asserted the number 800 (only selectors). The contract comments in `app.css` and `apps/analysis_web/README.md` (“Below 800px…”) *do* — those comments are the interface and must move with the query.

## Candidates

### 1. One 1100px comment, every `app.css` 800px query
- **Change:** Write the narrow contract **once** above the first query: 1100px = `main` max-width; Menu, stack-table, grid2, forms, 44px, 16px inputs, ticker `flex: 1 1 100%`, overflow-x, architecture-figure min/height, **and** `.chart-stage` all use it. Replace every `max-width: 800px` in `app.css` (six blocks today). Desktop disclose hide is `min-width: 1101px`, not a leftover 801. Handoff one sentence to `ui-run-reading`: do not reintroduce 800; only edit the height values. Do not leave a 800px island.
- **Why:** Six queries with the same number is repetition; a 800px chart query next to a 1100px Menu is information leakage and the same “tablet hole” this session is meant to close. File ownership as written (“run-reading avoid chrome CSS” vs Session 4’s phone stage height) is an unknown unknown for two parallel Wave 4 writers.
- **When:** `this change`

### 2. Do not clip `.stack-table thead`
- **Change:** Keep `thead { display: none }` at 1100px so clipped sort links are **not** tab stops (the F1 bug class). Empty pick `th` may get `aria-label="Select for compare"` (one attribute, not a column reorder). For SR names without thead: in the same pass that runs after `innerHTML`, set `aria-label` from `data-label` on non-pick `td`s (pick cells already have checkbox names). Do **not** visually-hide thead. Later, once blotter is the only writer of `runs_table.html`, replace `::before { content: attr(data-label) }` with a real `.cell-label` in the cell and drop the JS copy.
- **Why:** Clip-thead is a special-case patch on the 09-05 `display:none` + `::before` design. It puts every sort `<a>` in the tab order with no visible focus — Wave 4b’s P0 for disclose, applied to the table. Constraint: blotter owns column markup this wave, so full `.cell-label` DOM is `later`; the this-change is to refuse clip.
- **When:** `this change` (clip refusal + aria-label from `data-label`); `later` (real cell labels in templates)

### 3. List replacement = one live node + one event
- **Change:** In `runs.html`, put `#runs-status` (`aria-live="polite"`) **outside** `#runs-results`. Strip `aria-live` from the count `<p>` in `partials/runs_table.html` (that node dies on every swap today). After `innerHTML`, copy count/abort into `#runs-status`, restore focus to `a.sort.is-active` or the ticker field, and `dispatchEvent("runs-table-updated")`. `compares.js` listens to **that** event and calls `updateBar`. Fetch failure (non-abort) writes the same status node and a visible flash; the stale table stays. `#compare-hint` is a **separate** live region (selection rules, not table replacement). Hint text: ticker + `data-session-key` if present — do not parse `research:` run_ids.
- **Why:** Plan text lists symptoms (focus, hint, error, bar) without an interface. Implementers will either double-announce (partial keeps `aria-live` *and* a new node) or fire `catalog-changed` and loop with `fetchTable`. Shallow “restore focus” slice vs a real list-replacement module.
- **When:** `this change`

### 4. Harness 900px is not this session
- **Change:** Drop slice `figures-harness`’s harness.css / harness.js work (pipeline `flex-direction: column`, `scrollIntoView`, 900px 44px). Keep architecture frame height inside candidate 1 and `controlIconsEnabled: true` in `mermaid_boot.js`. Either a later lab pass owns `/harness`, or that pass **joins 1100** — do not ship a second “narrow” number while the brief says “one breakpoint.” a11y F8 (fake `tablist`, `h3` inside `<button>`, inspector not live) is not solved by a column stack; do not pretend it is.
- **Why:** Temporal leftover tour. The 09-05 phone plan explicitly did not tour Architecture/Harness. Mixing `harness.css` 900px into a session whose abstraction is the 1100px `app.css` contract is special–general mixture and a shallow module (“also do the lab pages”). North star is the book, not the pipeline map.
- **When:** `this change` (drop from Wave 4b); harness unify-or-fix is `later`
