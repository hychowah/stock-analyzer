# Review: Post-compose live UI (code)

Parent: `eng/sessions/2026-09-06-ui-ux-review/`. Branch: `ui-ux-compose`. Mode B W4, read-only. Code as of Waves 1–5 (`ui-trust-p0` … `ui-a11y-phone`). No browser MCP in this pass — findings are template/CSS/JS/route evidence against `PLAN.md` north star.

## Verdict

The product is no longer a nine-peer catalog dump. Opening localhost now shows **Stock Research**, primary vs Lab, a blotter whose first columns are ticker · as-of/live · FV · MoS · Downside · Duration · Audit (process), HTML 404s, numeric compare headlines, in-place Analyze wait, football PNG + CIO link, and cards at 1100px. That is the compose the PLAN asked for. What it still is *not*: a five-second morning scan. Empty `/` is still **All** sessions (alpha, cap 50), Duration still prints the homonym **`pass`** next to a green Audit **PASS**, and the run sheet still makes you scroll past a duplicate valuation table, a tape chart, Context, and a Compare form before the cone and the CIO cover. Highest-leverage remaining change: **one blotter voice** — default Latest-per-ticker, map `decision_action` to English (“Do not initiate”), and put football + Read CIO cover immediately under the decision strip.

## Findings

### F1 — Night `.below-bear` ink is unreadable

- **Severity:** P0
- **Pages:** `/`, `/runs/{run_id}`, `/portfolio` (any row already through bear)
- **Evidence:** `apps/analysis_web/static/app.css` `.below-bear { color: #7f1d1d; background: none; }` — one Light-tuned hex, no dark table. Night card is `--card: #1e293b`. `#7f1d1d` on `#1e293b` is ~1.5:1. Wave 3 made this the **only** signed encoding for “price already below bear FV”; Wave 5 retuned `--btn-bg` and `.quote-kind` / chart ticks to `--muted` and explicitly did **not** restyle `.below-bear`. Quote chips stay pastel-on-pastel (readable). The decision number does not.
- **Why it matters:** Downside < 0 is the “already through the floor” cue. On Night it vanishes. Trust in the blotter’s most important signed cell is gone for anyone on the shipped dark theme.
- **Recommendation:** In `app.css` only, give `.below-bear` a Night color on `html[data-theme="dark"]` (and the `prefers-color-scheme` twin) that is ≥4.5:1 on `--card` — e.g. `#fecaca` or `#fca5a5` ink, still `background: none`. Do not fill the cell; do not reuse `.badge.fail`.
- **Keep vs reshape:** Keep signed ink, not a fill. Reshape the Night token. A from-scratch UI would still color “through bear”; it would not ship one Light hex for both themes.

### F2 — `aria-label` from `data-label` replaces blotter values

- **Severity:** P0
- **Pages:** `/` (also after every live swap); any `.stack-table` that `runs.js` labels
- **Evidence:** `apps/analysis_web/static/runs.js` `labelStackedCells()` sets `td.setAttribute("aria-label", label)` from `data-label` (`Ticker`, `MoS`, `Downside`, …) on every non-pick cell, on first paint **and** after `innerHTML`. ARIA accessible name of a `td` with `aria-label` **replaces** the cell text. Desktop still has a visible `thead`; the cell name becomes “MoS” instead of “−114.7”. Phone `thead` is `display: none` (`app.css` 1100px contract), so SR also loses column headers. Wave 5 chose `display:none` (not clip) so sort links are not invisible tab stops, and deferred real `.cell-label` markup. The stopgap is worse than silence: the primary list can announce labels without numbers.
- **Why it matters:** The blotter is the product. A screen-reader session cannot read cheap-vs-base / cheap-vs-bear / duration if the values are named away. This is a Wave 5 regression, not a leftover of the 09-05 phone slice.
- **Recommendation:** Delete the `aria-label` write in `runs.js`. Add a visually hidden `<span class="cell-label">` (or clip the `thead` with the existing `.disclose` recipe **and** `tabindex="-1"` on sort links when stacked). Do not `display:none` headers if they are the only name. Pick `th` already has `aria-label="Select for compare"` — keep that.
- **Keep vs reshape:** Keep `.stack-table` + `data-label` + `::before` for sighted cards. Reshape the SR name. A from-scratch phone list would still be one table; it would not aria-label the column onto the value.

### F3 — Duration still says `pass` beside Audit PASS

- **Severity:** P1
- **Pages:** `/`, `/runs/{run_id}`, `/portfolio`
- **Evidence:** `partials/runs_table.html` Duration is `{{ r.decision_action }}` as plain text; Audit is `verdict_badge` (green `.badge.pass` for process PASS). `run_detail.html` same pair in the strip; Duration `td` is **not** `.decision`. Stored values are `initiate|add|hold|trim|sell|short|pass|too_hard` (`harness/agent_prompts.md`). Catalog already hydrates `decision_action`; Wave 3 correctly refused `verdict_badge` on it. The homonym remains. `verdict_line` is a run-detail subhead only. List legend (`runs.html`) explains MoS vs Downside, not Duration vs Audit.
- **Why it matters:** PLAN north star #2 and original P0-E: 4516.T MoS 42.7 + Audit PASS still reads as buyable until the cover says duration `pass` = do not initiate. The column exists; the **word** still collides; the green pill still wins the saccade.
- **Recommendation:** One display map in `templating.py` (not a second FV): `pass` → “Do not initiate”, `too_hard` → “Too hard”, others title-case. Print that string in the Duration cell; keep `title`/muted original token. Add `.decision` on Duration; keep Audit as the small process pill. One legend clause on `runs.html`: “Duration = stored action · Audit = process completeness.”
- **Keep vs reshape:** Keep stored `decision_action` and a non-badge Duration column. Reshape **copy and type rank**. A from-scratch blotter would never show the same token twice with opposite force.

### F4 — Empty `/` is still a 50-row All dump

- **Severity:** P1
- **Pages:** `/`
- **Evidence:** Wave 3 implemented `RunQuery.latest` and a visible All · Latest grain (`runs.html`, `filter_href(latest=1)`). Empty `/` and Reset **omit** the key (intentional shareable-URL rule in `pages.py` `_filter_href` and README). Default order remains ticker then session (`catalog_api`). Cap 50, no pager (PLAN out of scope). Brand `<a class="brand" href="/">` always hits that All dump; header **Runs** may restore a remembered query via `runs.js`, but not Latest unless the operator already chose it.
- **Why it matters:** North star #1: “See the book and latest completed research per name.” Opening localhost still starts on 000660.KS’s oldest-sort page of 50 sessions. Latest is a control the operator must know exists. Compare-from-list (F7) is why they kept All as default; the morning scan pays for that.
- **Recommendation:** Make `/?latest=1` the **Runs nav and brand home** grain (or land `/` on Latest and keep Reset → All). Leave shareable `/?` meaning All if you must, but do not make the first paint the 89-session dump. Do not unique LIMIT 50 in Python — the SQL grain already exists.
- **Keep vs reshape:** Keep Latest as a catalog grain, All as the compare dump, query memory, Reset. Reshape **which grain is home**. A from-scratch home is one row per name.

### F5 — Run sheet still does not lead with cone + CIO cover

- **Severity:** P1
- **Pages:** `/runs/{run_id}`, `/artifact` (cover itself is fine)
- **Evidence:** `run_detail.html` source order: back + ticker crumb → `h1.mono` ticker·session → `verdict_line` → `run_id` → decision strip → **full Valuation table (same numbers again)** → Price vs analysis (seven range chips + SVG) → Context → Compare form → **Valuation envelope** (`<img class="football-field">` only if `football_href`) → **Read CIO cover** → `<details>` allowlist. Wave 4a owns `football_href` / `cio_href` and one-H1 report viewer (`report.html` title + TOC + sibling `/artifact` links) — those work. They sit in the last card. Compare form (Grok, 15–40 min) sits above the cover. `h1` is still `.mono`.
- **Why it matters:** North star #4: “Open the CIO cover first, not a filesystem path.” Paths are gone; the cover is still a footer link. PLAN Session 4: know the call → see the cone → read the CIO cover. Tape chart is a good third; duplicate Valuation + Context + Compare are not.
- **Recommendation:** In `run_detail.html` only: after the strip, football `<img>` (or the muted missing line) + **Read CIO cover** as the next paragraph (`.btn`). Keep Price vs analysis under that. Move Compare and Context below. Drop or `<details>` the duplicate Valuation table (bear/base/bull/p’s can stay in one extra row of the strip or in Context). Drop `.mono` on the ticker `h1`; keep `run_id` muted.
- **Keep vs reshape:** Keep Agent 6 PNG, catalog overlay chart, allowlisted artifact route, README-as-cover. Reshape **page order**. A from-scratch run sheet is strip + cone + cover, then tape.

### F6 — Nested property tables still sideways-scroll the phone page

- **Severity:** P1
- **Pages:** `/runs/{run_id}` (decision strip, Valuation, Context); `/analyze/{id}` wait chrome; compare metadata table
- **Evidence:** Wave 5 1100px contract restyles `.stack-table` and sets `.report-body, .card > table:not(.stack-table) { overflow-x: auto }`. Decision strip is `<section class="decision-strip"><table>` — **not** a direct child of `.card`, **not** `.stack-table`. Valuation/Context same. Eight cells in two rows of four will overflow ~390px. `overflow-x` on a `display:table` often does not create a scrollport (the table grows `body`). Report matrices inside `.report-body` (a `div`) are the case that actually clips. Portfolio/Runs lists stack. Run *reading* — the job after the list — does not.
- **Why it matters:** Landscape/tablet list is fixed (800→1100). The run you open from a card still shoves the header and back link sideways. Original mobile F3 leftover, now isolated to nested tables.
- **Recommendation:** Wrap those three run-detail tables in `<div class="table-scroll">` and put `overflow-x: auto` on that class in the 1100px block (one wrapper, no second card tree). Optional: stack the strip as two definition lists / one column of `th`/`td` pairs at 1100px without cloning markup. Do not `.stack-table` property-row tables (09-05 contract).
- **Keep vs reshape:** Keep property-row tables and stack-table for entity lists. Reshape only the scrollport. A from-scratch phone run sheet would be the strip as stacked pairs, not an 8-cell grid.

### F7 — Latest grain and two-session Compare fight

- **Severity:** P1
- **Pages:** `/` (`#compare-bar`, `.compare-pick`), `/compares/new`
- **Evidence:** Compare requires two rows of the same ticker (`compares.js`). `latest=1` returns at most one row per ticker (SQL window). On Latest, the picker can never enable. Hint stays “Select two sessions of the same ticker.” `/compares/new` still dumps the full catalog into two ungrouped `<select>`s (`compare_new.html`). Run-detail Compare form only appears when `siblings` from `list_runs(..., comparable_only=True)` is non-empty — other sessions of the name are not listed as links (ticker crumb `/?ticker_prefix=` is the only hop, and that URL is All not Latest).
- **Why it matters:** If home becomes Latest (F4), Compare-from-list dies unless All is one click and obvious. Today Compare trains people to stay on All, which is why F4 is still open.
- **Recommendation:** When `latest` is on and a pick is checked, `compares.js` hint + a control: “Latest shows one row per name. Switch to All to pick two sessions” linking `filter_href(latest='')` plus `ticker_prefix`. On run detail, always list other sessions as links; keep the Grok form gated on `comparable_only`. Do not invent a ticker SPA.
- **Keep vs reshape:** Keep checkbox Compare, confirm dialog, identity URLs. Reshape the grain handoff. A from-scratch UI would compare from the run sheet, not from a unique-per-ticker home list.

### F8 — Night Lab / tagline still use `--faint` for words

- **Severity:** P1
- **Pages:** all chrome (desktop Lab + tagline); phone Menu/Lab labels are `--header-fg` and pass
- **Evidence:** Wave 5: “Word uses (`.quote-kind`, chart ticks) → `--muted`. Leave `--faint` for non-text.” `app.css` still has `.header-tagline { color: var(--faint) }` and `.header-lab a { color: var(--faint) }`. Night `--faint: #64748b` on `--header-bg: #020617` is ~4.2:1 (fails AA normal text). Light tagline `#94a3b8` on `#0f172a` passes. `.quote-kind` / `.chart-grid text` correctly use `--muted` now. No global `:focus-visible` except `.disclose-btn`.
- **Why it matters:** Lab is quieter by design; quieter cannot mean unreadable. Wave 5’s contrast pass missed the header, the one surface every page paints.
- **Recommendation:** Point `.header-tagline` and `.header-lab a` at `--muted` or `--header-link` at reduced weight. Keep Lab smaller (`0.9rem`) and non-current. One `a:focus-visible, button:focus-visible` rule in `app.css`.
- **Keep vs reshape:** Keep Primary vs Lab grouping and Night/Light. Reshape the leftover token. Do not restyle the theme switcher.

### F9 — In-flight work is invisible on `/`; wait copy is still phase ids

- **Severity:** P1
- **Pages:** `/`, `/analyze`, `/analyze/{id}`
- **Evidence:** Home has no running/queued chip. `/analyze` is a job log (`analyze.html`) with raw `phase_current` (`orch`, …). `analyze_detail.html` shows `resume_hint` (`aria-live`) — the human sentence Wave 4c chose — **and** `phase <span id="job-phase">`. `analyze_detail.js` patches badge/phase/hint and reloads only on terminal; `<meta refresh=15>` also full-reloads while running (artifact list is server HTML by design). Complete job: “Open catalog run” is a text link, then a path+byte `<ul>`, no CIO. PLAN explicitly deferred a `phase_current` English map.
- **Why it matters:** North star #3 is start or watch an analysis. Watching still means leaving Runs. For 2–8 hours the operator either sits on a page that jumps every 15s or forgets a job is live. `resume_hint` is the right string; `orch` beside it undoes it.
- **Recommendation:** One muted line on `runs.html` when any job is running/queued (“Analyze running: TICKER — open /analyze”). On the job page, hide `#job-phase` while `resume_hint` is non-empty; keep meta refresh (no-JS + artifact growth) but that is enough. Complete: one `.btn` “Open catalog run” / “Read CIO cover”. Do not map phase ids in the UI (PLAN).
- **Keep vs reshape:** Keep JS patch + meta refresh + no FV until snapshot + cancel/resume/discard. Reshape **where** running work is visible. A from-scratch home would show in-flight names on the blotter.

### F10 — Type rank leftovers: Audit still louder than Duration; desktop start form unskinned

- **Severity:** P1
- **Pages:** `/`, `/runs/{run_id}`, `/portfolio`, `/analyze/new`, property-row tables
- **Evidence:** `.decision` exists (1.05rem/600) on ticker/FV/MoS/Downside only. Duration is body text; Audit is a filled green pill — the loudest object in the row after Live chips. Global `th` is still uppercase muted for **column** headers **and** property-row labels (`As-of price`, `MoS %`). No `--h1`/`--h2` tokens; `.price-chart h2` is 1.05rem. `tr:hover` on Valuation. `.stack-form` input/select rules live **only** inside `@media (max-width: 1100px)` (`app.css` ~961–978) — Wave 5 raised the query, it did not lift the form. Wide desktop `/analyze/new` is still UA controls. Portfolio FV/MoS/Downside omit `.decision`. Compare first card still dumps `job.compare_id` and `job.out_dir`.
- **Why it matters:** Wave 3 ranked columns; it did not finish the type scale the visual review asked for. Green PASS will keep beating `pass` even after F3’s English map if Duration stays 0.92rem.
- **Recommendation:** `.decision` on Duration cells; scope uppercase `th` to `thead th`; `.stack-form` rules to the base sheet (not only the 1100px query); drop `tr:hover` on tables without `thead`. Portfolio: add `.decision` on FV/MoS/Downside (same cells as Runs). Compare: A/B as `TICKER session_key` links; `out_dir` only under Packet files.
- **Keep vs reshape:** Keep one token table, cards, `.decision`. Reshape rank, not layout system.

### F11 — Polish cluster (merge)

- **Severity:** P2
- **Pages:** chrome, `/`, `/compares/{id}`, `/experiments`, `/health`, `/calibration`, `/harness`, `/analyze/{id}`
- **Evidence:**
  - Runs query memory is invisible (`#nav-runs` text stays “Runs”; original IA F6).
  - Collapsed Filters have no “sector=… · mos≥…” chip (original mobile F7).
  - Compare flash says “Read the synthesis first” then paints Headline above Synthesis (`compare_detail.html`).
  - `headline_view` runs every cell through `fmt_num` (2 dp), including MoS; no Duration row (packet has no `decision_action`).
  - Experiments `h1` + lead sit outside `.card`; Health has two `h1`s.
  - Calibration empty is `—%` after `fmt_num` + a literal `%`; no bars (PLAN out of scope scatter).
  - `harness.css` still stacks at 900px with horizontal `.harness-pipeline`; inspector is JS-only; `role="tablist"` leftover (Wave 5 dropped this on purpose).
  - No `aria-sort`, no `aria-expanded` on disclose, no `:focus-visible` on cards.
  - `error.html` back label is always “← Runs” (analyze/compare 404s included). Router `_error()` copies still not unified (PLAN).
  - `fmt_num` always two decimals (`1,401,000.00`).
  - Dead `.chart-stage { height: 220px }` at 1100px: global `min-height: 260px` wins, so used height is 260 — leftover CSS, not a visual hole.
  - Phone `#nav-open` is still a clipped checkbox in the tab order; desktop `display:none` fixed original P0-D. Acceptable with the Wave 5 ring; not a new Menu product.
  - Analyze JS `catch` is empty; 15s meta refresh jumps scroll on a long wait.
- **Why it matters:** None blocks a session once F1–F10 are done.
- **Recommendation:** Ride along only when the owning file is open. Do not open harness.css for a phone restyle unless Lab is the session.

## What already works

- **Trust P0s from Sep 6:** compare headline is a Python view (`templating.headline_view` → `row.label` / `row.cells`); HTML 404 + `← Runs`; Analyze reconcile notes `.muted`; Compare abort does not also say “No packets.”
- **Nav:** Primary (Runs · Analyze · Compare · Portfolio) + Lab; `render_page` injects `nav.current`; `aria-current="page"`; skip link `#content`; brand **Stock Research**; phone Menu / Lab wrapped so one checkbox cannot open the other; desktop disclose `display:none` at 1101px (first Tab is skip-link, not `#nav-open`).
- **Blotter:** column rank Ticker · Session · As-of (currency) · Live · FV · MoS · Downside · Duration · Audit (process); `.decision` type; Downside vintage `as-of`/`live` after `fillDownside`; `.below-bear` signed ink (Light); Live is a `%` chip not a cell fill; loading `…` + `aria-busy`; first 50 of cap; `asof_downside_pct` sort is SQL on stored as-of vs bear.
- **Run reading:** strip + full-width Valuation above the chart (Context not a twin `.grid2`); football PNG when present; one Read CIO cover; allowlist in `<details>` without Path; `render_session_report` title/TOC/sibling `.md` on `/artifact`; chart `formatPoint`, off-chart status, weighted + sibling legend, `touchmove`/`touchend`, `pad.l` from ticks.
- **Jobs / book:** start form ticker + as-of + harness first; Busy/Grok-missing stay on the form; JS wait + meta 15; Cancel confirm “Kill Grok, keep the session.”; 303 `?flash=`; Compare Retry; no `data-live-reload` on analyze/compare; portfolio As-of/Live/Downside/Duration + Analyze CTA on missing/no-PASS; empty “Import an IB activity statement”; waterfall totals vs signed gutter.
- **Phone / a11y contract:** one 1100px policy; stack-table cards; 44px disclose/picks/buttons; 16px inputs; ticker `flex: 1 1 100%`; `#runs-status` live node outside the swap; `runs-table-updated`; compare hint is ticker + session_key; `#compare-bar.is-on` sticks only with a pick; Night `--btn-bg: #2563eb`; architecture frame shorter + `controlIconsEnabled: true`.
- **Identity URLs, catalog-only FV/MoS, Downside display math, no SPA.**

## From-scratch keepers

- FastAPI + Jinja + small JS. Shareable GET queries. No React/SPA.
- Catalog as the only FV/MoS source. Live Yahoo and Downside % are display math.
- One chrome token table in `app.css`. Semantic greens/reds do not flip with chrome (Night must still *meet* contrast — F1).
- Phone: one table restyled as cards (`.stack-table` + `data-label`); checkbox `.disclose` for Menu/Lab/Filters. No second card tree.
- `RunQuery.latest` as a catalog grain, not a Python unique of LIMIT 50.
- Duration ≠ Audit badge. `verdict_badge` is process only.
- Agent 6 `valuation_football_field.png` as the envelope; do not JS-DCF a second cone.
- `render_session_report` ≠ sanitizer. Architecture/harness stay `render_markdown()`.
- One wait loop on the job page (patch + meta). Errors stay on the task.
- IB book + latest-per-ticker is the watchlist. No third store of weights/FVs.
- Runs query memory that does **not** replay onto empty `/` if All remains a shareable dump — but home should be Latest (F4).

## Do not do

- SPA / client router / mega-menu / icon rail / tenth peer link / `/ticker/META` hub.
- Invent live MoS, blended compare target, or a JS DCF.
- Relabel Audit PASS as a buy list.
- Re-propose Menu / stack-table / theme switch / HTML 404 / football link / CIO title as new products unless still broken (F1–F2 are regressions/leftovers of shipped work; Menu itself is not).
- Sticky site header.
- Clip `.stack-table thead` in a way that leaves sort links as invisible tab stops (fix F2 with `.cell-label` or `tabindex="-1"` on stacked sorts).
- Unify router `_error()` copies as a wave of its own.
- `git commit` until the user agrees. No `archive/research/**` or `archive/outcomes/**` rewrites.

## Wave leftovers (still open vs PLAN)

| PLAN item | Status now |
|-----------|------------|
| P0-A blank compare headline | **Done** (Python view) |
| P0-B HTML 404 | **Done** |
| P0-C Analyze red reconcile | **Done** |
| P0-D first Tab `#nav-open` on desktop | **Done**; phone clipped checkbox remains (P2) |
| P0-E Audit PASS vs duration `pass` | **Column done; English not** (F3) |
| P0-F nine equal links | **Done** (Primary / Lab) |
| North star: book + latest per name | Book on `/portfolio` **done**; Latest **opt-in** (F4, F7) |
| North star: MoS vs Downside vs Audit vs duration | Metrics and vintage **done**; Duration voice **not** (F3, F10) |
| North star: start / watch / compare | Start + wait + Retry **done**; watch not on `/` (F9) |
| North star: CIO cover first | Path gone; cover still last (F5) |
| Ticker strip `META · 5 runs · Start · Compare` | Still out of scope; crumb `/?ticker_prefix=` only |
| Real `.cell-label` | Still out of scope; Wave 5 `aria-label` stopgap is **harmful** (F2) |
| `phase_current` English map | Still out of scope; hide the id when `resume_hint` exists (F9) |
| Pagination beyond Latest | Still out of scope |
| Desktop 44px everywhere | Still out of scope |
| Unify `_error()` helpers | Still out of scope |
| Calibration scatter / outcome bars | Still out of scope (empty `—%` is P2) |
| Experiments as a real filter index | Partial (`h2` → `/?experiment_id=`) |
| Harness `workflow_spec` / 900px pipeline / fake tablist | Still out of scope (Wave 5 dropped it) |
| Night signed-ink token | **Not done** (F1) |
| Header `--faint` as words | **Not done** (F8) |
| Lift `.stack-form` out of the phone query | **Not done** (F10) |
| Default Latest vs All | Wave 3 chose opt-in; north star still wants Latest home (F4) |

## Playwright live confirmation (2026-09-07)

Browser MCP against **current tree** at `http://127.0.0.1:8877/` (git SHA `ff2077e`). Desktop 1440×900, phone 390×844, stack breakpoint 1100×800, Night theme, keyboard Tab, ticker typeahead, Latest grain, run 4516.T, Analyze COHR, Architecture, HTML 404, CIO artifact.

**Ops:** `http://127.0.0.1:8765/` is a **stale process** (`python -m apps.analysis_web --port 8765`, no `--no-auto-restart`). Lab → Architecture is JSON `{"detail":"Not Found"}`; Duration cells paint `—`; `aria-current` is missing. Do not treat that process as the product. Boot from this tree (`--no-auto-restart`).

| Check | Live |
|-------|------|
| F1 Night `.below-bear` | Confirmed. `#7f1d1d` on Night card ~**1.46:1** (0762.HK Downside −14.9). Six such cells on `/`. |
| F2 SR `aria-label` | Code-backed; not re-audited with a screen reader in this pass. |
| F3 Duration vs Audit | 4516.T strip: Duration `pass` beside green Audit **PASS**; cheap claim `franchise_mos`. Blotter: 01378.HK `pass` / PASS; 0700.HK `initiate` / PASS. |
| F4 empty `/` is All | Confirmed. 50 shown · 99 matching. Latest `/?latest=1` → 49 rows (one per name). Brand home is still All. |
| F5 CIO / cone last | 4516.T: football PNG + “Read CIO cover” exist; they sit in Valuation envelope **below** duplicate Valuation + chart. `verdict_line` paints raw markdown (`**\`duration.action = pass\`**`, `registry/decision.json`). CIO artifact title is good: “Nippon Shinyaku — CIO cover”. |
| F8 Night tagline | Header tagline `--faint` ~**3.93:1** on Night header (fails AA normal text). Lab links same token. |
| Keyboard | First Tab is **Skip to content** (visible at y=8). Then brand → Runs → Analyze… Disclose checkboxes are `display:none` on desktop. Downside sort href is `/?sort=asof_downside_pct&dir=desc`. |
| Phone 390 | Menu + Lab + Night. Extra filters collapsed. No horizontal overflow on `/`. First blotter card starts ~760px down (below Compare selected). Dual **Filter** (submit) vs **Filters** (disclose). Opening Menu shuffles Lab/Menu. |
| 1100px | Cards (`td` `display:flex`, row ~332px). Menu/Filters visible. |
| Desktop blotter | Table **125px wider than the card**; Region/Tech stick out of the white panel. |
| Live search | Typing `META` → `/?ticker_prefix=META&latest=1`, one row. |
| Architecture | HTML + mermaid (6 SVGs). `aria-current=Architecture`. |
| 404 | HTML chrome + `← Runs`. |
| Analyze COHR | `complete` + phase `orch`. Copy: “ABANDONED: specialist spawn failed…” and “abandon.json present on finalized session; not treating as abandoned”. Not a red `.err` (P0-C class fix holds; the sentences still collide). |
| Portfolio | Empty book; filesystem paths in the error (`apps/analysis_web/.local/portfolio.json`). |
| Favicon | Console 404 `/favicon.ico` on every page. |
