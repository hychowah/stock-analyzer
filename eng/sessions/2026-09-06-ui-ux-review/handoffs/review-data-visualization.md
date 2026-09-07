# Review: Decision-support visualization

## Verdict

This UI already has the right *ingredients* for a capital decision — frozen catalog FV, an As-of column, a Live Yahoo print, MoS %, Downside % display math, a price-vs-analysis SVG, and session football-field PNGs on disk — but it does not yet *compose* them into a five-second read of “how cheap vs bear, vs base, vs last run.” Numbers sit in a wide table with unlabeled vintages; the interactive chart is a tape viewer that clips the scenario envelope; the football field that *does* answer the question is never linked; and the compare headline table, the one place two sessions should be compared as numbers, renders blank cells even when `headline.json` is full. Highest-leverage change: make the decision strip honest and visible (MoS = vs base / as-of, Downside = vs bear / live-or-as-of, both labeled) and put the stored football-field PNG next to the tape chart so uncertainty is a range, not three anonymous point lines.

## Findings

### F1 — Compare headline table is empty on a complete packet
- **Severity:** P0
- **Pages:** `/compares/{id}` (live: `compare:AVGO:2026-09-04__2026-08-23__r3_vs_2026-09-01`)
- **Evidence:** `apps/analysis_web/templates/compare_detail.html` interpolates `{{ row.values[key] }}`. On a Jinja dict, `.values` is `dict.values`, not the `"values"` key, so every numeric cell is blank. Live HTML: `<th>fv_base</th><td class="num"></td><td class="num"></td>`. On disk, `archive/comparisons/AVGO/2026-09-04__2026-08-23__r3_vs_2026-09-01/headline.json` has `108.46` vs `210.99`, as-of `368.45` vs `370.34`, MoS `-239.7` vs `-75.5`. Synthesis text then has to carry the only numbers. No test asserts headline cells. Field names stay snake_case; values would be raw even after the lookup works. `key_risks` in the JSON is unused.
- **Why it matters:** Compare exists to answer “did base/bear/bull move, or did the tape?” A blank headline forces the operator into a 38k-character synthesis for a six-number grid.
- **Recommendation:** In `compare_detail.html` use `row['values'][key]`, pipe numbers through `fmt_num` / `fmt_num(1)` for MoS, and map field keys to English labels (`As-of`, `FV base`, `FV bear`, `FV bull`, `MoS %`). Optional display-math delta column `(B − A)` — not a blended FV.
- **Keep vs reshape:** Keep the two-session snapshot table and the “helper only / not a blended fair value” disclaimer. Reshape the lookup and formatting, not the packet.

### F2 — MoS, Downside, Live, and As-of are adjacent but not distinguishable
- **Severity:** P1
- **Pages:** `/`, `/runs/{id}`
- **Evidence:** `partials/runs_table.html` and `run_detail.html` put **MoS %** (catalog, vs FV *base*, denominator = base, frozen at as-of) next to **Downside %** (`(price − bear) / price`, starts as as-of, then `quotes.js` `fillDownside` silently overwrites with live). Header `title` explains Downside; the cell itself is a bare `73.6`. After quotes, title becomes `live · 1,662,000.00 → bear 369,823.67` — hover only. MoS has no tooltip and never updates. Live `/`: `000660.KS` As-of `1,401,000.00`, Live `—` until JS, MoS `-114.7`, Downside `73.6`. `/api/quotes` last print `1,662,000` (+18.6% vs as-of). `0762.HK` Downside `-15.4` (price already *below* bear) with no “below bear” encoding. ACN `2026-08-29`: MoS `18.6` (cheap vs base) and Downside `0.4` (sitting on bear) — the actual decision — look like two unexplained percents. Run-detail Live cell is another `—` until poll; no vintage chip on Downside after it mutates.
- **Why it matters:** Opposite signals are normal (expensive vs base *and* a long way to bear). Unlabeled vintages and legs make the pair look like a bug, or worse, like live MoS.
- **Recommendation:** Treat the four columns as a labeled strip, not four independent numbers. Headers: **MoS %** with subtitle/title `vs base · as-of`; **Downside %** `vs bear · live if printed, else as-of`. After `fillDownside`, write a visible `live` / `as-of` suffix (or `data-vintage` class) on the Downside cell — same string already computed. Negative Downside: class `below-bear` and keep the minus; do not paint it green. Do **not** compute a live MoS in the UI; if you ever show cheapness vs live, it must be Downside-style display math vs *stored* FV and labeled as such.
- **Keep vs reshape:** Keep both metrics and the live-then-as-of Downside rule. Reshape the labeling so the contract is on the cell, not in a `title`.

### F3 — Runs table scan path buries the decision numbers
- **Severity:** P1
- **Pages:** `/`
- **Evidence:** Column order in `partials/runs_table.html`: Ticker, Session, Harness, Sector, Region, As-of, Live, FV base, MoS %, Downside %, Audit, Tech. Live `/`: 50 rows, mixed `1,401,000.00` KRW / `23.76` HKD / later USD with **no currency column**. FV bear/bull absent (Downside is the only bear encoding). Downside is not a sort header (`pages.py` `_SORT_HEADERS` omits it; tests assert `data-sort="downside_pct"` is absent). Caption `live is Yahoo last print` is the only vintage note. Phone `.stack-table` already hides Harness/Sector/Region/Tech (`desktop-only`) — so the *phone* card is a better decision strip than desktop. Default sort is ticker, so SK Hynix (`MoS -114.7`) leads the list as if it were a buy screen.
- **Why it matters:** You cannot answer “how cheap vs base / vs bear / vs last print” in five seconds when three context columns sit between the name and the money, and 1.4 million KRW is ununit-ed.
- **Recommendation:** Reorder `runs_table.html` (and `_SORT_HEADERS`) to **Ticker · Session · As-of · Live · FV base · MoS % · Downside % · Audit**, then Harness/Sector/Region/Tech as `desktop-only`. Show `currency` (or listing suffix) on As-of. Allow sort of *as-of* Downside as display math from stored bear vs `asof_price` — do not sort the live-mutated value on the server.
- **Keep vs reshape:** Keep live search/sort, stack-table cards, and the Downside column. Reshape order and units, not the catalog query.

### F4 — Price chart encodes tape well and the scenario envelope poorly
- **Severity:** P1
- **Pages:** `/runs/{id}`
- **Evidence:** `static/price_chart.js` `domainY()` comment: “Price is the scale. Base and as-of are anchors. Bear/bull/weighted clip.” Live 3M `000660.KS`: closes `1.32M–2.92M` → bear `369,824` **off-chart**; 1Y `0762.HK`: bull `19.15` **off-chart** (domain max ~14.1). ACN 1Y this-run levels fit, but sibling `2026-08-10` base `364.55` / bull `451.98` clip — “vs last run” is a grey stub. Weighted line is drawn (`chart-weighted`) but **not** in the legend (`run_detail.html`: Price / Bear / Base / Bull / As-of only). Sibling stems have no legend entry (only muted copy “Other sessions are markers”). Tooltip (`showTooltip`) is Close + Base; the readout under the chart already has Bear/Base/Bull — hover is strictly worse. No live last-print marker. Band between bear and bull is a flat wash; `p_bear / p_base / p_bull` stay in the valuation table as `0.33 / 0.47 / 0.20` (not percents, not on the chart). Range chips and `aria-pressed` work; 1Y default is fine. Loading/error paths (`Loading price history…`, `Price history unavailable (…). Analysis levels still shown.`, `No listing symbol — showing analysis levels only.`) are honest.
- **Why it matters:** A capital decision needs the cone vs the tape. A price-centric Y scale on 3M *hides* the bear the Downside column is talking about. Hover that omits bear trains the eye to treat base as the only level.
- **Recommendation:** Do **not** force 3M tape and a 4×-away bear onto one linear axis (that squashes the tape). Keep price-centric `domainY` for the time series, but (1) make tooltip == readout (date, close, bear, base, bull, currency); (2) add legend items for weighted and “other sessions”; (3) if a stored level clips, set `#price-chart-status` to `Bear 369,824 off-chart` rather than failing silent; (4) optional: a last Yahoo close as a distinct *print* dot (not a new FV). Pair with F5 for the envelope.
- **Keep vs reshape:** Keep range chips, SVG overlay from catalog JSON, sibling click-through, clipPath, hover crosshair. Reshape tooltip/legend/clip signaling; do not draw a second DCF.

### F5 — Football-field PNGs exist and are orphaned
- **Severity:** P1
- **Pages:** `/runs/{id}`, `/artifact`
- **Evidence:** Sessions on disk include `charts/valuation_football_field.png` (ACN `2026-08-29`, `000660.KS` `2026-07-29`, plus tornado/heatmap/price_trend). Catalog allowlist already includes `charts/` (`packages/catalog_api/client.py` `DEFAULT_ALLOW_PREFIXES`); `routes/artifacts.py` already serves `image/png`. Run detail only calls `list_artifacts(..., prefix="reports/")` and the primary-report trio README/Fundamental/Technical. Live ACN and SK Hynix run pages: `charts/` absent, `.png` absent. The ACN football field is the five-second chart this persona wants: bear–bull bar, PW vs base, as-of price as a dashed line, MoS 18.6% vs freeze $189.61, probabilities on the cone. The interactive SVG does none of that encoding.
- **Why it matters:** Agent 6 already produced the uncertainty graphic. The website hides it behind an allowlist nobody links.
- **Recommendation:** In `page_run` / `run_detail.html`, list `charts/` (football field first) as thumbnails or `<img src="/artifact?run_id=…&path=charts/valuation_football_field.png">` under the price chart. Missing PNG → one muted line `No football field in charts/`. Do not re-plot a Mode B football field from JS.
- **Keep vs reshape:** Keep Agent 6 PNGs and the artifact route. Surface them.

### F6 — Live quote coloring collides with PASS/FAIL; loading is a silent em dash
- **Severity:** P1
- **Pages:** `/`, `/runs/{id}`
- **Evidence:** `quotes.js` `fillCell` paints the **whole** `.quote-live` cell `chg-up` / `chg-down`. `app.css` uses the same green/red pair as `.badge.pass` / `.badge.fail` (comment even says they “rhyme … not shared meaning”). Server HTML is `—` with no `aria-busy`; first paint is indistinguishable from unstamped/error (`unstamped` title vs `—`). `/api/quotes` works (`000660.KS` +4.1% regular/intraday; `AAPL` −2.5%). `print_kind === "daily_close"` gets a good `quote-kind` label; `currency` on the live payload was `null`, so the muted currency span often never appears. `#quote-status` handles fetch fail and the 50-symbol cap; it stays `hidden` while cells are still empty. Cap = 50 unique listings = default page size, so one extra unique ticker on the list disables *all* quotes.
- **Why it matters:** Green Live next to green PASS reads as “the quote agrees with the audit.” A page of em dashes reads as “Yahoo is down” rather than “poll in flight.”
- **Recommendation:** Put day-change on a small signed chip (`+4.1%`) inside the cell; leave the price in default ink. Different hue or outline from pass/fail (e.g. background only on the chip). While `poll()` has not applied, set cell text to `…` and `aria-busy="true"`; keep `—` for error/unstamped. If `syms.length > MAX_SYMBOLS`, still quote the first 50 rather than none.
- **Keep vs reshape:** Keep listing-stamp quotes, `daily close` tag, and title `as_of · market_state`. Reshape the fill so change ≠ verdict.

### F7 — Portfolio cannot answer cheap-vs-bear; waterfall is a bar list
- **Severity:** P1
- **Pages:** `/portfolio`
- **Evidence:** Live `/portfolio` has no book (`No book at …/.local/portfolio.json`) — empty path is copy-paste instructions, which is fine. When a book exists (`portfolio.html` + `services/portfolio.py` `_bar_rows`): Change-in-NAV and MTM are **left-aligned magnitude bars** (`width: bar_pct%` of peak abs), not a bridge from starting NAV → components → ending NAV. Sign is only `pos`/`neg` color (`#86efac` / `#fca5a5`). Positions: Weight, **Price** (catalog as-of), FV base, MoS %, Audit — no Live, no Downside, no FV bear. IB mode adds Close / Value (base) beside catalog Price without saying which price MoS used. Coverage/mean MoS summary is numbers-only.
- **Why it matters:** A book view should answer “where is NAV, and which line is the cheapness?” Mixing IB close and catalog as-of under “Price” is the same vintage trap as F2.
- **Recommendation:** Rename catalog column **As-of**; add Downside % display math vs stored bear (same helper as runs). Waterfall: bold Starting/Ending NAV as total rows; draw signed components from a zero gutter (or a true offset waterfall). Keep IB TWR as a labeled IB-reported number.
- **Keep vs reshape:** Keep IB sqlite join, PASS-only filter, MTM top-20 + other. Reshape column names and bar geometry.

### F8 — Calibration is a count table, not MoS-vs-outcomes
- **Severity:** P1
- **Pages:** `/calibration`
- **Evidence:** Live: `Joined rows: 0 · overall hit rate: — · mean return: —%` and `No outcomes joined for this horizon`. Template always suffixes `%` after `fmt_num`, so missing mean is `—%`. When rows exist, `calibration.html` is five columns (bucket, n, scored, hit rate, mean ret %) with no bar, no scatter, no color. `packages/kd_research/outcomes.py` already knows `direction_hit` and `fv_band_status` (`inside` / `below_bear` / `above_bull`); the page shows none of that. Empty state does not say a join needs `outcomes` marks / `price_path`.
- **Why it matters:** Calibration is how you learn whether MoS sign was worth trading. A zero-row table with `—%` looks broken; a filled table still does not show the relationship.
- **Recommendation:** Keep the bucket table. Add in-cell bars for hit rate and signed color for mean return (display of stored outcomes, not a new score). Empty copy: `No price_path marks joined for this horizon — outcomes are not computed in the UI.` Drop the extra `%` when `fmt_num` already returned `—`.
- **Keep vs reshape:** Keep horizon + PASS-only filters and sqlite join. Do not draw a second calibration model.

### F9 — Number formatting nits (merged)
- **Severity:** P2
- **Pages:** `/`, `/runs/{id}`, `/compares/{id}`, artifacts
- **Evidence:** `fmt_num` always two decimals (`1,401,000.00`, `p bear / base / bull` as `0.30 / 0.50 / 0.20` not 30/50/20%). Artifact sizes are raw bytes (`5503`). Experiments table has FV base + MoS but no as-of, so you cannot see cheapness vs last run without opening the run. Quote `toFixed(1)` on change is fine; large KRW live prints will match `fmt_num` once filled.
- **Why it matters:** Polish, but KRW with `.00` and probabilities as fractions slow the same scan as F3.
- **Recommendation:** Integers for `|n| ≥ 1000` with 0 decimals; show `p_bear` as percent in the valuation table only (stored `0.30` × 100, labeled). Humanize artifact sizes. Not a new FV.
- **Keep vs reshape:** Keep tabular-nums `.num`. Tweak digits.

## What already works

- **Decision math is catalog-only.** Downside % is `(price − stored bear) / price`; the website does not author FV. README and `ARCHITECTURE.md` say this out loud.
- **As-of and Live are separate columns** on Runs and run detail — the right split, even if Downside then blurs it.
- **Quote pipeline:** listing stamp → `/api/quotes`, `daily close` tag, hidden-tab pause, fragment rebind via `quotes-refresh`, 120s TTL.
- **Price chart scaffolding:** range chips, 1Y default, hover crosshair, sibling markers with click-through, analysis levels still drawn when Yahoo fails.
- **Phone stack-table** already promotes Ticker/Session/As-of/Live/FV/MoS/Downside/Audit — closer to a decision card than desktop.
- **Audit badges**, tabular numbers, compare “not a blended fair value” copy, ticker-not-found abort vs empty table.
- **Portfolio empty state** tells the operator how to copy `portfolio.example.json` or `import_ib` instead of a blank chart.
- **Artifact PNG route** is ready for football fields the moment the run page links them.

## From-scratch keepers

- Server-rendered tables with a **Ticker · Session · As-of · Live · FV · MoS · Downside** strip.
- Catalog overlay JSON (`_chart_overlay`) feeding the SVG — no Mode B DCF.
- Yahoo listing stamp distinct from catalog ticker.
- Agent 6 `charts/valuation_football_field.png` as the scenario graphic.
- Range-chip tape chart for *time*, football field for *levels*.
- Downside as display math vs stored bear (live print preferred).
- Compare headline as a two-column snapshot grid (once `row['values']` renders).
- One chrome token table; pass/fail and chg as *different* semantic paints.

## Do not do

- Do not invent a live MoS, a blended compare FV, or a JS DCF / second football-field model.
- Do not SPA-rewrite the runs table to get column reorder.
- Do not reuse pass/fail green-red for day-change, MoS, and Downside as if they shared meaning.
- Do not auto-expand 3M Y scale to a far-away bear if that destroys tape — put the envelope in the football field instead.
- Do not hide missing quotes as a permanent `—` without a loading vs error state.
- Do not sort or filter on the post-JS live Downside on the server.
