# Review: Mobile / tablet (phone ~390px, tablet ~768–900px)

## Verdict

Portrait phone (~390px) already has the 2026-09-05 chrome: Menu, stacked run cards, extra Filters behind a disclosure, 44px buttons. That work landed and should stay. What still hurts is everything the **800px cliff** does not catch, plus the surfaces that slice never restyled. Rotate the same phone (iPhone 14 landscape is 844×390) or sit on an iPad Air portrait (820 CSS px) and you are back in the 13-column Runs table, the long tagline, and nine header links wrapping over a short viewport — the original sideways-read problem, leftover. Highest-leverage change: **raise the existing 800px query (Menu, `.stack-table`, disclose, form stacking, 44px) to 1100px** (`main`’s max-width) so landscape phones and tablet portrait inherit yesterday’s layout instead of the desktop table.

Live notes: `/` (50 stacked runs), `/runs/research:000660.KS:2026-07-29` + its fundamental report, `/analyze`, `/analyze/new`, `/compares`, `/compares/new`, `/experiments`, `/calibration`, `/health` loaded. `/architecture` returned 404 (working-tree `ARCHITECTURE.md` missing to that process). `/harness` rendered `workflow_spec failed`. `/portfolio` had no book. Those three are reviewed from templates/CSS/JS.

## Findings

### F1 — 800px cliff: landscape phone and tablet still get the 13-column desktop

- **Severity:** P0
- **Pages:** `/` (Runs), `/portfolio` positions, header chrome on every route; also `/compares/new` `min-width: 16rem` selects at 801px+
- **Evidence:** All phone rules live in six `@media (max-width: 800px)` blocks in `apps/analysis_web/static/app.css` (Menu/tagline, `.stack-table`, `.grid2`, chart 220px, perf bars, forms). There is no orientation query and no 768/900/1024 companion. Live `/` still ships 13 columns; only Harness/Sector/Region/Tech carry `desktop-only` (`templates/partials/runs_table.html`). iPhone 14 landscape is **844px wide × 390px tall** — above 800, so `.header-tagline` stays visible, Menu stays `display:none`, `.header-links a` wrap as desktop, and the 13-col table is back. iPad Air / 10th-gen portrait (~820–834) is the same hole. iPad Mini 768 luckily falls *inside* 800 and gets cards. Compare selects still have `min-width: 16rem` outside the 800px query (`app.css` `.compare-form select`).
- **Why it matters:** The shipped phone work’s success criterion was “no sideways-reading 13-column tables.” Landscape is how a phone user reads a run list on the couch. A tablet is the other hand-held. Both still fail that test. On a 390px-tall landscape screen the *desktop* header (tagline + nine links + Night) eats a third of the viewport even though the header is not sticky.
- **Recommendation:** Raise the existing 800px media queries in `app.css` (and the matching tests in `apps/analysis_web/tests/test_analysis_web.py`) to **1100px**, matching `main { max-width: 1100px }`. One breakpoint, same markup. Do not add a second parallel policy. Leave `harness.css` 900px workspace stack as-is unless you also align it (see F5).
- **Keep vs reshape:** Keep yesterday’s mechanism (one table, CSS restyle, checkbox Menu). Reshape only the width at which it turns on.

### F2 — Chart 220px cannot show KRW-scale FV lines; touch scrub is a tap, not a drag

- **Severity:** P1
- **Pages:** `/runs/{run_id}`
- **Evidence:** Live overlay on `000660.KS`: `asof_price` 1,401,000, `fv_base` 652,671, `fv_bear` 369,824, `fv_bull` 1,107,176 KRW. `app.css` still sets `.chart-stage { height: 220px }` at 800px. `price_chart.js` `layout()` locks `pad.l = 56` and draws Y ticks with `toLocaleString` (`1,401,000` is wider than 56px at 10px mono). X-axis writes five `YYYY-MM-DD` labels across `innerW` ≈ 250px. FV labels are 10px `"bear"|"base"|"bull"|"wtd"` at the right edge; `domainY()` only anchors on price + base + as-of, so **bear is clipped off the bottom** on this run. Range chips inherit `button { min-height: 44px }` — seven chips wrap to two rows (~88px) *above* the 220px plot. Touch: `touchstart` → `onMove` only (`passive: true`); no `touchmove`/`touchend`. Tooltip is `white-space: pre` and can stick. Readout is one long mono string (`Close · Bear · Base · Bull · KRW`). Valuation fallback `369,823.67 / 652,670.88 / 1,107,176.04` sits in one `td.num` beside “FV bear / base / bull”.
- **Why it matters:** This page is why you open a run on a phone — is price vs bear/base/bull? At 220px with million-unit labels, the lines are decorative. The 44px chip rule (good) now costs more vertical space than the plot it serves. Tap-to-scrub that does not follow the finger trains the user that the chart is dead.
- **Recommendation:** In the phone query, set `.chart-stage { height: min(42vh, 320px); min-height: 260px }`. In `price_chart.js` `layout()`, size `pad.l` from the longest Y tick (KRW millions) and shorten X labels to `YYYY-MM` when `innerW < 400`. Add `touchmove` (and `touchend` to hide the tooltip) next to the existing `touchstart`. Do not invent a second FV; the overlay JSON is already correct.
- **Keep vs reshape:** Keep the SVG overlay + range chips + readout. Reshape only stage height, axis padding, and touch handlers. The 220px number was a desktop-shrink leftover, not a product choice that still works.

### F3 — Wide tables that never got `.stack-table` still scroll the whole page

- **Severity:** P1
- **Pages:** `/artifact` (markdown reports), `/runs/{run_id}` “All reports/”, `/compares/{id}` headline + packet path, `/portfolio` waterfall/MtM (`perf-table`)
- **Evidence:** Live `reports/01_000660.KS_fundamental.md` has **six** HTML tables, including 5-column ones (`Metric | Q2 2026 | YoY | QoQ | Source` with cells like `registry/latest_quarter.json; sec_filings.json`, and a WACC×margin matrix). `.report-body table` only sets margin (`app.css`); there is **no** `overflow-x` wrapper. `pre` scrolls; tables blow `body`. Run-detail artifact index is File + Path + Size without `.stack-table` — live rows duplicate `01_000660.KS_fundamental.md` in both File and Path. `perf-table` keeps `min-width: 4rem` bars at 800px; not a stack-table (correct per the 09-05 contract) but also not contained. Compare metadata dumps `job.out_dir` in `.mono`.
- **Why it matters:** After you survive the run list, reading the actual memo is the job. A 5-col source table sideways-scrolls the **page** (header, back link, and all), not a local scroller — the worst leftover overflow. Artifact Path is a second copy of File on a 350px card inner width.
- **Recommendation:** At the phone/tablet query, add `overflow-x: auto` on `.report-body` and on `.card > table:not(.stack-table)`. Drop the Path column from the run-detail artifact table in `run_detail.html` (File link is enough; size can stay). Do **not** put `.stack-table` on property-row or matrix tables.
- **Keep vs reshape:** Keep HTML tables for report matrices (they are data). Add a local scrollport. Reshape only the artifact index (two columns, not three).

### F4 — Architecture figures: 28rem frames steal scroll; wheel zoom has no phone equivalent

- **Severity:** P1
- **Pages:** `/architecture` (template + `mermaid_boot.js` + `app.css`; live route 404 in this process)
- **Evidence:** `ARCHITECTURE.md` has **three** mermaid blocks. `.architecture-figure` is `height: min(60vh, 36rem); min-height: 28rem` (~448px) with `overflow: auto`, then `overflow: hidden` once `is-interactive`. `mermaid_boot.js` sets `useMaxWidth: false`, `controlIconsEnabled: false`, `mouseWheelZoomEnabled` only on `pointerenter`/`pointerleave`. Copy on the page: “Drag a diagram to move it. Wheel over it to zoom.” No pinch hint, no `touch-action`, no on-screen +/- . Reset is `position: absolute` with desktop padding (44px only because the global `button` rule applies below 800). Three frames × 28rem ≈ 1344px of grab-surfaces before the rest of a long markdown doc.
- **Why it matters:** On a 667–844px-tall phone, one figure is more than half the screen. One-finger drag pans the SVG instead of the page, so you cannot scroll past the diagram. Wheel does not exist. Pinch *may* work via svg-pan-zoom but is undocumented and easy to miss. This is leftover of a desktop pan/zoom feature, not missing “add phone layout.”
- **Recommendation:** In the same width query as F1, set `.architecture-figure { min-height: 16rem; height: min(50vh, 22rem); }` and turn `controlIconsEnabled: true` in `mermaid_boot.js` so zoom does not depend on wheel. Keep drag-pan; do not write a custom pinch stack.
- **Keep vs reshape:** Keep mermaid-in-a-frame + Reset. Reshape the frame size and give touch a visible zoom control.

### F5 — Harness pipeline is still a horizontal strip; inspector sits below it

- **Severity:** P1
- **Pages:** `/harness` (live: `workflow_spec failed` error card; review from `harness.css` / `harness.html` / `harness.js`)
- **Evidence:** `.harness-workspace` stacks at **900px**, not 800. `.harness-pipeline` is `overflow-x: auto` with `.harness-phase { min-width: 12.5rem }` — a sideways swipe of stages. `.harness-inspector { position: sticky; top: 0.75rem }` is the **second grid row** once stacked, so sticky does nothing useful until you have scrolled past the whole pipeline. `harness.js` `selectAgent` / `selectPhase` paint the inspector but never `scrollIntoView`. Tap-size `min-height: 44px` on `button` applies only at 800px, so 801–900px is stacked workspace + 16px-class agent chips. Phase head padding is `0.15rem`.
- **Why it matters:** Harness is a map you *tap through*. On a phone you swipe a strip you cannot see, tap a tile, then scroll down a long way to read the inspector — if you notice it moved. The 800 vs 900 split is the tablet in-between in CSS form.
- **Recommendation:** Below 900px, set `.harness-pipeline { flex-direction: column; overflow-x: visible; }` so stages stack, and `scrollIntoView({block:'nearest'})` the inspector after select in `harness.js`. Align the 44px `button` rule with this 900px query (or with the raised F1 breakpoint). Keep overflow-x on desktop.
- **Keep vs reshape:** Keep the pipeline-as-buttons + inspector. Reshape only the narrow-width flow (column, not a hidden horizontal scroller).

### F6 — Compare on a phone: 16px checkboxes, CTA above 50 tall cards

- **Severity:** P1
- **Pages:** `/` compare bar + picks; `/compares/new`
- **Evidence:** `td.pick` is unlabeled on purpose (`app.css` `.stack-table td.pick::before { content: none }`) but the checkbox never got a 44px hit area — only `button`/`.btn`/header links did. Live home: **50** `.compare-pick` boxes, each the UA ~16px control, first row of a card that is itself eight labeled fields. `#compare-bar` sits in the filter card *above* `#runs-results` (`runs.html`). On success, `compares.js` sets `hint.textContent = "Compare " + t0 + ": " + ids[0] + " vs " + ids[1]` e.g. `Compare 000660.KS: research:000660.KS:2026-07-29 vs research:…` — a full-width mono dump. `/compares/new` *does* stack at 800px (`min-width: 0; width: 100%`); native `<select>` options like `000660.KS 2026-07-29 · FV 652,670.88` are fine in the iOS picker. That 16rem leftover is fixed **only** below 800 (see F1).
- **Why it matters:** Compare is a primary Runs action. Fat-finger misses on 16px boxes, then you must scroll back to the top of a 50-card list to press Compare. The hint with two `research:` IDs wraps into noise. The dedicated compare form is actually the more phone-friendly path — if you can find “Compare form” in the wrapping bar.
- **Recommendation:** In the phone query, make `.stack-table td.pick` a 44×44 flex hit area (`input { width: 22px; height: 22px }` is enough if the cell is the target). Move `#compare-bar` to `position: sticky; bottom: 0` inside `main` (or duplicate a short “Compare selected” next to the bar only when `ids.length > 0`) so the CTA follows the thumb. Hint: ticker + two session_keys, not raw run_ids.
- **Keep vs reshape:** Keep checkbox-in-the-row (JS contract with `compares.js` / live fragment swap). Reshape hit size and where the confirm lives. Do not clone a second mobile picker tree.

### F7 — Filter/form leftovers: tiny ticker field, invisible extra filters, iOS zoom

- **Severity:** P1
- **Pages:** `/` filters, `/analyze/new`, `/calibration`, `/portfolio` error, `/analyze` + `/compares` ticker rows
- **Evidence:** Phone rules set `form.filters input { min-width: 0; width: 100% }` but `.filters-row label` is **not** `flex: 1` / `width: 100%` (`app.css`). The always-on Ticker field sizes to the label word “Ticker”, then fights 44px Filter + Reset in one wrap row. Extra filters sit in `#filters-extra.disclose-panel` with no chip of what is still applied when the panel is closed (`runs.html`). Inputs never set `font-size: 16px` — iOS Safari zooms the page on focus when the computed input size is the UA ~13.3px. `/calibration` puts the sentence “Audit PASS filter (process completeness, not a buy list)” as a column label beside Horizon. Live `/portfolio` error embeds the full Windows path `C:\Users\user\…\portfolio.json` in `.mono` with no `overflow-wrap`. `analyze_new.html` `.stack-form` *does* stretch labels — that pattern is the one that works. Limit still has an inline `style="min-width:4rem"`.
- **Why it matters:** The always-on row is the one phone filter you are supposed to use without opening Filters. If Ticker is a stubby field and extra constraints are invisible when collapsed, you filter “wrong” and do not know why the list is short. iOS zoom is a one-way trip off the layout.
- **Recommendation:** In the phone query, `form.filters .filters-row label { flex: 1 1 100% }` (ticker full width, buttons on the next row), `input, select { font-size: 16px }`, and when any extra filter is non-empty, put a one-line muted summary above the disclose button (`sector=… · mos≥…`) even while the panel is closed. Reuse `.stack-form` width rules; do not invent a second form system.
- **Keep vs reshape:** Keep ticker + Filter + Reset always on, extras in the same disclose module. Reshape label flex and 16px font. A collapsed-filter summary is a small additive, not a new control.

### F8 — Phone nits (merge)

- **Severity:** P2
- **Pages:** `/`, `/runs/{run_id}`, header, `/experiments`
- **Evidence:** Stacked `tr` cards sit inside a page `.card` (double chrome; 09-05 accepted this). Menu open is nine × 44px links (~396px) that do not auto-close until navigation — fine, just tall. Header is **not** `position: sticky` (does not eat scroll; landscape still loses space via F1). `price_chart.js` `Math.max(320, rect.width)` can be 2px wider than a 318px stage. Primary reports list repeats the path next to the link. Experiments “Model” column is long `orchestrator_model` text in every card. No phone sort (thead gone) — accepted non-goal in the 09-05 plan. `layout()` sibling dots are r=4.5px tap targets.
- **Why it matters:** None of these block a session. Together they make cards feel heavier than they are.
- **Recommendation:** Leave unless touching the same files as F1–F7. If already in `run_detail.html` for F3, drop the duplicate path on primary report `<li>`s.
- **Keep vs reshape:** Keep.

## What already works

- Viewport meta is set (`base.html`).
- Header **Menu** checkbox disclosure, tagline hidden, theme toggle stays visible, header links ≥44px — at ≤800px (`base.html`, `app.css`).
- Header is static, not sticky — portrait scroll is not eaten by a frozen bar.
- `.stack-table` + `data-label` + `td.desktop-only` on Runs, Portfolio positions, Analyze jobs, Compares, Experiments, Calibration. Health / valuation / NAV summaries correctly left as property-row tables.
- Runs hides Harness / Sector / Region / Tech on phone; live quote cell and compare checkbox remain in the card (live `/` confirmed `stack-table`, `desktop-only`, `compare-pick`).
- Extra Runs filters behind `#filters-open`; ticker + hidden `sort`/`dir` stay in the form (collapsed ≠ omitted).
- `.compare-form select` drops `min-width: 16rem` at 800px; `/analyze/new` `.stack-form` stretches labels.
- `.grid2` becomes one column at 800px (run-detail Valuation | Context stacks).
- Harness pipeline `overflow-x: auto` is an intentional desktop/tablet strip (pain is inspector placement, F5).
- 44px min-height on `button`, `.btn`, chart range chips, theme toggle, Menu — inside the 800px query only (desktop visual freeze held).

## From-scratch keepers

- One HTML table per entity list, restyled as cards in CSS (`.stack-table` / `data-label`). Do not clone a second card tree for live quotes or compare picks.
- One checkbox-disclosure module (`.disclose` / `.disclose-btn` / `.disclose-panel`) for Menu and Filters.
- Secondary columns hidden on the list, still on the run-detail page.
- Ticker + Filter + Reset always on; extras collapsed, not omitted from the GET.
- Server-rendered pages, `main` max-width, token table in `app.css`.
- Price chart as catalog overlay + Yahoo bars, with a text readout under the SVG.
- Native `<select>` on Compare two-sessions (system picker is the right phone UI).

## Do not do

- Do not re-propose Menu, `.stack-table`, filter disclosure, or 44px targets as new work — they shipped; raise the breakpoint (F1) and fix leftovers.
- Do not add a second Jinja card markup, PWA, user-agent sniffing, or React/SPA.
- Do not `position: sticky` the site header (it would eat the 390px-tall landscape viewport).
- Do not apply `.stack-table` to Health, NAV summaries, compare headline matrices, or markdown report tables.
- Do not invent a phone sort dropdown or a second fair-value series.
- Do not write a custom mermaid pinch engine; use the existing pan/zoom with on-screen controls.
- Do not git commit from this review.
