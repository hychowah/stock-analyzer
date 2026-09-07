# Review: Visual design and information hierarchy

## Verdict

This is a competent operator console that still looks like a catalog dump: navy chrome, one card language, one table language, and almost no type scale. In the first two seconds the eye hits the nine-link header, an implementation tagline, internal IDs, and a 280px empty chart — not ticker, live/as-of, FV, MoS, Downside, or audit. The single highest-leverage change is a **decision strip** (larger ticker + signed MoS/Downside + FV vs price + audit) at the top of `/` rows and `/runs/{id}`, with run_id, paths, harness, and the price chart demoted below that strip. Keep the server-rendered cards/tables; stop giving every cell the same 0.92rem voice.

## Findings

### F1 — First glance never lands on the decision
- **Severity:** P0
- **Pages:** `/`, `/runs/{run_id}`, `/portfolio`, `/analyze/new`
- **Evidence:** Live `/` (200, 50 rows of 89). Header is `<strong>Archive Analysis</strong>` plus `.header-tagline` (“catalog + job scheduler · Analyze starts Mode A · Compare appends archive/comparisons/”) plus nine `.header-links a` plus `#theme-toggle`. First card is `<h1>Research runs</h1>` then muted “source: catalog sqlite · live”, then the full filter wall and `#compare-bar`. Second card opens with “50 shown · 89 matching · max 50 · live is Yahoo last print”. Decision columns sit after Ticker, Session, Harness, Sector, Region, As-of, Live, FV base. First row `000660.KS`: MoS **-114.7**, Downside **73.6**, Audit PASS — all `font-size: 0.92rem` (`table` in `app.css`) with ticker at `.mono` **0.85rem**. Live `/runs/research:AVGO:2026-09-01`: back link → `<h1 class="mono">AVGO · 2026-09-01</h1>` → muted `research:AVGO:2026-09-01` → `#price-chart` (h2 1.05rem, seven range chips, `.chart-stage` **280px**) → only then `.grid2` `<h3>Valuation</h3>` | `<h3>Context</h3>`. MoS **-75.5** and Downside **81.3** are ordinary `.num` cells next to model `dcf_fcff_8y_growth_overlay`. Live `/portfolio`: h1 “Portfolio · default”, then the full `.local\portfolio.json` path, then the empty-book error. Live `/analyze/new`: a paragraph about Grok wall-clock before the ticker field.
- **Why it matters:** An operator opening the archive to judge a name should lock ticker / price / FV / MoS / Downside / audit in under two seconds. Today those facts are present but visually equal to chrome, sqlite provenance, and file paths.
- **Recommendation:** In `templates/partials/runs_table.html` and `templates/run_detail.html`, add a compact decision strip **above** filters-on-detail and **above** `#price-chart`: ticker (heavier than `.mono` 0.85rem), as-of + live, FV base (bear/base/bull as secondary), MoS %, Downside %, audit badge. Do not invent numbers — restyle catalog fields already on the page. Move `run.run_id` to a `<details>` or the Context table. On `/`, keep the 13-column table but give ticker + MoS + Downside + Audit a heavier class (e.g. `.decision`) and visually quiet Harness/Sector/Region/Tech.
- **Keep vs reshape:** Keep the catalog table and the chart. Reshape **order and type rank**. A from-scratch UI would still be a list + a run sheet; it would not lead with the chart or the run_id.

### F2 — Header chrome is the loudest object on every page
- **Severity:** P1
- **Pages:** all (`templates/base.html`)
- **Evidence:** `header` is always dark (`--header-bg: #0f172a` Light, `#020617` Night) even when the page is Light. Nine links share one style (`.header-links a { color: var(--header-link); margin-right: 1rem; }`) with **no** `aria-current`, no `.is-active`, no grouping. Hover is underline only. The tagline is 0.85rem `--faint` (`#94a3b8` Light / `#64748b` Night) on navy — implementation copy (`archive/comparisons/`), not a location cue. `#theme-toggle` is a bordered ghost on the same row. `main { max-width: 1100px }` so the header is full-bleed and the work is a centered column; the navy bar wins the first saccade. Live `/architecture` is FastAPI `{"detail":"Not Found"}` (JSON, not `error.html`); the ninth-ish link is a dead unstyled dump. Live `/harness` is `.card.err` “workflow_spec failed:” with an empty message.
- **Why it matters:** Nine equal destinations train the eye to hunt the chrome, not the page. A first-time operator cannot see they are already on Runs. Clicking Architecture/Harness currently punishes that hunt.
- **Recommendation:** In `base.html` + `app.css`, (1) drop or shorten `.header-tagline` to a product line (“Research archive”) — put Mode A/Compare mechanics on `/analyze` and `/compares`; (2) mark the current route (`aria-current="page"` + a header-fg/underline weight) from the existing path; (3) visually group the nine links into **Work** (Runs, Analyze, Compares, Portfolio) vs **System** (Harness, Architecture, Experiments, Calibration, Health) with a muted separator, still one `<nav>`, still no SPA. Wire unknown routes through `templates/error.html` so a missed `/architecture` is a card, not raw JSON.
- **Keep vs reshape:** Keep one global header and the Night button. Reshape density and current-page. Do not add a second sidebar nav.

### F3 — Runs list is a 13-column spreadsheet, not a scan
- **Severity:** P1
- **Pages:** `/` (`templates/partials/runs_table.html`, `templates/runs.html`)
- **Evidence:** Columns: pick, Ticker, Session, Harness, Sector, Region, As-of, Live, FV base, MoS %, Downside %, Audit, Tech. `th` is 0.8rem uppercase muted; `td` 0.92rem; ticker `.mono` 0.85rem — so the name is **smaller** than the prices. First live row Region and Tech are empty; Harness `2.38.0` still takes a desktop column. As-of `1,401,000.00` (always two decimals via `fmt_num`) crowds 1100px. Live cell is `—` until `quotes.js`; when it fills, `.quote-live.chg-up` paints the whole cell `#bbf7d0` (000660.KS live print 1,662,000, **+4.1%**). Compare checkboxes and `#compare-bar` sit in the **filter** card, above the numbers. Sort headers are the only emphasis (`th a.sort.is-active { color: var(--fg) }`).
- **Why it matters:** Horizontal scan buries MoS/Downside/Audit on the right. Empty Region/Tech still cost width. After quotes land, the green/red **Live** cell becomes the row’s climax — a 4% print, not a −114.7% MoS.
- **Recommendation:** In `runs_table.html` + `app.css`, add `.decision` on Ticker, MoS, Downside, Audit (weight 600, slightly larger). Keep Live as a number; stop filling the whole `<td>` (color the `%` span only). Mark empty Region/Tech with `.muted` “—” or fold them into the existing `.desktop-only` quieting (they already hide below 800px). Leave sort/search/compare as-is.
- **Keep vs reshape:** Keep live prefix search, sort, two-row Compare, Downside % math. Reshape column rank. Do not hide MoS/Downside behind a hover.

### F4 — Run detail leads with chart chrome and Context, not the call
- **Severity:** P1
- **Pages:** `/runs/{run_id}` (`templates/run_detail.html`, `static/app.css` `.price-chart`, `.grid2`)
- **Evidence:** Source order in `run_detail.html`: back link, h1.mono ticker·session, p.mono.muted **run_id**, `#price-chart` (h2, muted Yahoo sentence, `.chart-ranges` seven buttons, 280px `.chart-stage`, readout, status, legend), then `.grid2` Valuation | Context. `.grid2` is `1fr 1fr` down to 800px, so “Exported 2026-09-05T12:37:22Z” and empty Intensity get the same column as MoS. Valuation is an 8-row property table: as-of, live, bear/base/bull on **one** line, weighted, p’s, MoS, Downside, model. Chart legend omits weighted even though `price_chart.js` draws `.chart-weighted` (`#7c3aed`) and overlay JSON includes `fv_weighted`. First paint of the stage is an empty box until JS. Live AVGO: price 370.34 vs FV base 210.99 vs bear 69.34 — the relationship is in the table, not in a hero comparison.
- **Why it matters:** The operator came for “is this cheap, and did audit pass?” The page answers with a chart toolbar. Context is not secondary; it is a twin column.
- **Recommendation:** In `run_detail.html`, render a decision strip, then Valuation as the primary block (full width, not half of `.grid2`), then the chart, then Context + reports. Add a `.swatch-weighted` legend item next to the existing bear/base/bull swatches in the same template. Keep range chips and overlay JSON.
- **Keep vs reshape:** Keep Price vs analysis (shipped). Reshape **page order**. A from-scratch run sheet would still have this chart; it would not be the first 280px.

### F5 — There is no type scale; `th` does two jobs and loses both
- **Severity:** P1
- **Pages:** all list and property tables; `static/app.css`
- **Evidence:** `app.css` never sets `h1`/`h2`/`h3` size except `.price-chart h2 { font-size: 1.05rem }` and `.report-body h1–h3 { margin-top: 1.25em }`. Page titles are browser default (~2em) while the decision is 0.92rem. Global `th { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; color: var(--muted) }` applies to **column** headers **and** property-row labels (`<tr><th>MoS %</th><td class="num">-75.5</td></tr>`). So “MoS %” looks like a spreadsheet gutter, not a label for a hero number. `.mono` forces 0.85rem on tickers **and** on run_ids. `.card` padding 1rem 1.25rem + 8px radius + 1px `--border` is the only elevation; `box-shadow: 0 1px 2px rgba(0,0,0,0.04)` barely separates card from `--bg #f6f7f9`. `tr:hover` applies to property-row tables too, so hovering Valuation flashes the MoS row for no reason. `/analyze/new` `.stack-form` is styled **only** inside `@media (max-width: 800px)` — desktop ticker/date/slug inputs are unstyled browser controls next to styled `.filters` inputs elsewhere.
- **Why it matters:** Hierarchy is “whatever the browser does for h1, then a uniform table.” Labels recede; values do not rise. The start-analysis form looks like an unskinned admin POST.
- **Recommendation:** In `app.css` only: define `--h1: 1.35rem`, `--h2: 1.1rem`, `--h3: 0.95rem`, `.decision { font-size: 1.15rem; font-variant-numeric: tabular-nums; font-weight: 600 }`. Scope uppercase muted `th` to `thead th`. Add `td.prop { color: var(--muted); font-size: 0.8rem; width: 40% }` (or `th.prop`) for property rows. Lift `.stack-form` input/select rules out of the 800px block so desktop `/analyze/new` matches filter chrome. Remove `tr:hover` on tables without `thead` (valuation/health) or scope hover to `.stack-table tbody tr`.
- **Keep vs reshape:** Keep one token table and cards+tables. Reshape type. Do not introduce a second layout system (tiles, dashboards).

### F6 — Night is a real theme; semantic greens/reds become billboards and collide with audit
- **Severity:** P1
- **Pages:** `/` Live column, `/runs/{id}` Live + badges, `/portfolio` perf bars, `/analyze` status, `/compares` status; Light and Night
- **Evidence:** Comment at top of `app.css` is honest: chrome inverts; **semantic stays hex**. `.quote-live.chg-up` / `.badge.pass` / `.badge.status-complete` all use `#bbf7d0` / `#14532d`. Fail/down use `#fecaca` / `#7f1d1d`. CSS even says Live “rhyme with pass/fail for scan, not shared meaning.” On Light, a PASS pill and an up-day Live cell are the same object. On Night (`html[data-theme="dark"]`: `--card #1e293b`, `--bg #0b1220`) those pastel fills are the **brightest** patches on the page — louder than ticker or MoS. Chart series stay readable on `--chart-stage #0f172a`: price `--chart-ink #e2e8f0`, bear `#b91c1c`, base `#1d4ed8`, bull `#15803d`, weighted `#7c3aed`. As-of `#94a3b8` and `.chart-band { fill: rgba(29,78,216,0.08) }` go quiet on dark. `.architecture-figure` uses `--paper` (light-only `#fff`) and Reset hardcodes `#0f172a` on paper — **correct** for mermaid `theme: "neutral"` (`mermaid_boot.js`). `.header-tagline { color: var(--faint) }` in Night is `#64748b` on `#020617` (weaker than Light). `.harness-chip.is-required` is `#e0f2fe` / `#075985` (light-only leftover). `.perf-bar.pos/.neg` (`#86efac` / `#fca5a5`) would also glow on Night once IB data exists.
- **Why it matters:** Color currently means “today’s print” and “audit PASS” with the same paint. Night makes that paint the visual climax. MoS −75.5 has **no** sign color at all, so the unused meaning is the one the operator needs.
- **Recommendation:** Keep semantic hex (do not invent a second theme table). Split the rhymes: Live change = ink only (`color` on the `%`, no cell `background`); PASS/FAIL badges keep fills; give MoS/Downside **signed ink** (e.g. existing `#15803d` / `#b91c1c` on the number, not a cell fill) from the stored sign. On dark, optionally darken fills (`#14532d` text on `#14532d22` or similar) so they do not outrank `.decision`. Add Night tokens for `.harness-chip.is-required` if Harness is repaired. Do not restyle the theme switcher; it works.
- **Keep vs reshape:** Keep Light/Night + `theme.js`. Reshape **what** is painted. This is leftover of `2026-09-05-ui-theme-switch` + `2026-09-04-quote-chg-background`, not a request for a new theme product.

### F7 — Analyze / Compare job UI buries the action in equal fields and process copy
- **Severity:** P1
- **Pages:** `/analyze`, `/analyze/new`, `/analyze/{id}`, `/compares`, `/compares/{id}`
- **Evidence:** `/analyze/new`: h1 “Start Mode A analysis”; a long `.muted` paragraph (Yahoo existence-check, hours, slots 3, global cap 4, killing the UI); then Ticker, As-of, Optional slug, Harness, Orchestrator model, Subagent model, Notes, ingest checkbox, **then** “Start analysis”. Desktop inputs unstyled (F5). `/analyze/analyze:4516.T:2026-09-06`: complete + “Audit: PASS. This is not a buy list.” + “Open catalog run”, then `mode=new · harness=2.39.0 · pid=45876 · spawned …`, then an Artifacts `<ul class="mono">` of `charts/price_trend.png` + raw `size_bytes` (`170484`) — no FV/MoS even after complete (correct legally) but also no visual jump to the catalog run. `/compares/compare:AVGO:…`: yellow `.flash` “Compare complete. Read the synthesis first.” then h1.mono sessions, muted **compare_id**, then a property table of full `research:AVGO:…` ids and a **Windows packet path**. Next card “Headline (prediction snapshots)” is a table of snake_case fields (`asof_price`, `margin_of_safety_pct`) with **empty** `.num` cells live. Synthesis (the actual memo, with its own `<h1>`) starts after that empty table. Report-body h1 inside `.card` competes with the page h1.
- **Why it matters:** Starting work and reading a compare should feel like ticker-in, answer-out. Today both feel like job-control JSON with a CSS skin.
- **Recommendation:** `/analyze/new`: make Ticker + Harness + submit the first visual group; collapse slug/models/notes in `<details>`. Style `.stack-form` on desktop (F5). `/analyze/{id}` complete: one large “Open catalog run” `.btn` next to the status badge; move pid/path to muted one-liner. `/compares/{id}`: if `synthesis_html`, put Synthesis first (flash already asks for that); hide or populate Headline; link A/B as `AVGO 2026-09-01` not `research:AVGO:…`; drop `out_dir` from the first card (keep it in Packet files). Constrain `.report-body h1` inside job pages to `h2` size so the page h1 stays the only display title.
- **Keep vs reshape:** Keep POST forms, confirm dialogs, status badges, no-FV-until-snapshot. Reshape **priority of fields**. No SPA job board.

### F8 — Internal IDs and filesystem paths outrank human titles
- **Severity:** P1
- **Pages:** `/runs/{id}`, `/artifact`, `/analyze/{id}`, `/compares/{id}`, `/portfolio`, `/health`, `/experiments`
- **Evidence:** Run h1 is ticker·date in `.mono` (code voice for a proper name) with `research:…` as line two. Artifact live title/h1 is `reports/00_000660.KS_README.md` in `.mono`; the real title (“SK hynix Inc. — Research Session Summary”) is a **second** h1 inside `.report-body`. Primary reports list duplicates `item.rel` in `.mono.muted` beside “README”. Analyze artifacts are paths + byte sizes. Compare first table is run_id + `C:\Users\…\archive\comparisons\…`. Portfolio empty state centers the `.local` path. Health is two `<h1>`s (“Process”, “Catalog health”) dumping keys `git_sha`, `db_path`, `run_count` as a property table — 99 runs, useful, but presented as an API probe. Experiments: `<h1>` **outside** `.card`, then `<h2 class="mono">(none)</h2>`.
- **Why it matters:** The product is for the operator who runs research, not for the filesystem. Paths are recovery tools; they should not be the display title.
- **Recommendation:** Artifact `h1`: report human title from the markdown first heading (already rendered in `.report-body`) or the template `item.label`; keep `relpath` as muted subtitle + Raw source. Run h1: drop `.mono` on the ticker (keep session muted). Portfolio empty: one sentence + the copy/import commands; path in `<code>` after the sentence. Health: one h1, human labels (“Git SHA”, “Runs in catalog”), not raw keys. Experiments: put h1 inside the first card; if `eid` is empty/`(none)`, use the existing “No experiment_id” copy.
- **Keep vs reshape:** Keep allowlisted paths and raw source. Reshape **what is the heading**. Do not hide paths entirely.

### F9 — Leftover nits (merge)
- **Severity:** P2
- **Pages:** `/architecture`, `/harness`, `/calibration`, `/`, chart, header
- **Evidence:** Live `/architecture` → JSON 404 (shipped page missing from this process). `architecture.html` has no page h1; the doc’s `# Architecture — …` becomes the title inside `.report-body`. Live `/harness` empty PinError card. Calibration: “Joined rows: **0** · overall hit rate: **—**” and a colspan empty table — honest, but two cards of chrome for no data. Chart weighted line with no legend swatch (also in F4). `#price-chart` first paint empty. `.quote-kind { display:block }` (“daily close”) adds a second line in Live cells and inflates row height. `runs.html` Limit input has inline `style="min-width:4rem"`. Title pattern `{page} · Stock Research Archive` vs brand “Archive Analysis”. No skip-to-content (out of scope except that the header is tall). `.btn.secondary` `#64748b` is the same as `--muted`.
- **Why it matters:** None blocks a session alone; together they make the chrome feel unfinished.
- **Recommendation:** One pass in `app.css`/`base.html`: legend swatch; inline Limit style → class; brand string match; empty calibration stays one card. Repair Architecture/Harness as product bugs (not a visual redesign).
- **Keep vs reshape:** Keep paper mermaid, stack-table at 800px, theme toggle.

## What already works

- One chrome token table in `app.css`; Light default / Night `html[data-theme="dark"]` / no-JS `prefers-color-scheme` path in `theme.js` is coherent. Do not rebuild it.
- Cards + tables as the only layout language. 8px radius, 1px border, 1100px main — readable, not pretty-for-its-own-sake.
- Tabular nums on `.num`, uppercase column headers, PASS/FAIL pills, status badges (queued/running/complete/failed) — the right *kinds* of objects.
- Live quotes + Downside % from stored bear FV (display math, not a second FV).
- Phone leftovers that still look intended: `.disclose` Menu, 44px targets, `.stack-table` cards at 800px. Desktop density is the problem, not the phone restyle.
- Run-detail chart series (bear dashed red, base solid blue, bull dashed green, price as ink) remain distinguishable in Night on `--chart-stage`.
- Architecture figures: `--paper` does **not** invert; Reset-on-paper is the right call for mermaid “neutral”.
- Compare flash “Read the synthesis first” is the correct editorial instinct (the layout then ignores it).
- Analyze complete copy “This is not a buy list” is the right legal/visual disclaimer — it should sit next to a **large** catalog-run link, not replace the decision.
- Abort styling for unknown ticker (`form.filters.is-abort`, `.card.err`) is clear when it triggers.

## From-scratch keepers

- Server-rendered HTML, Jinja cards, no SPA.
- Catalog as the only number source; live Yahoo as a labeled print; Downside % as display math.
- Runs list with live prefix search, facet filters, column sort, two-row same-ticker Compare.
- Run sheet: decision numbers + price-vs-analysis overlay + links into allowlisted reports.
- Night/Light via one token table; semantic series colors that do not flip with chrome.
- Header Night/Light control and (on phone) Menu disclosure.
- Status and audit as badges, not as a second traffic-light dashboard.
- Harness pipeline tiles + inspector (when `workflow_spec` works) — that page is allowed to be a diagram, not a table.

## Do not do

- Do not rewrite as a React/SPA “research workspace.”
- Do not invent fair values, blend A/B, or add a second MoS.
- Do not re-propose phone `.stack-table` or the theme switch as new work; they shipped. Fix Night **leftovers** (semantic billboards, required-chip hex) only.
- Do not color Live cells and PASS badges the same and then add a third green for “cheap.”
- Do not put run_id, `out_dir`, or `pid` in the first heading.
- Do not widen `main` past ~1100px to fit 13 equal columns; rank columns instead (Harness already has a 1440px exception).
- Do not turn Valuation into sparkline widgets that recompute FV.
- Do not add marketing hero imagery or a public-SaaS marketing header; this is a localhost operator tool — it needs **rank**, not decoration.
