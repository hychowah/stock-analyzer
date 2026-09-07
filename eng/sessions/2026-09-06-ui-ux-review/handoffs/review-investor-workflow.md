# Review: Investor workflow (PM / equity analyst)

## Verdict

This site is a research factory console that happens to hold the numbers a capital allocator needs — MoS, Downside %, live print, CIO covers, two-session synthesis — then hides the *decision* behind catalog IDs, Audit PASS, and engineer chrome. The single highest-leverage change is to land the operator on **the book, latest PASS per name, duration action, cheap-vs-bear, and “is a run still going?”** instead of a ticker-sorted session dump and a `/portfolio` page that, live, pretends there is no book.

## Findings

### F1 — Live `/portfolio` does not show the IB book that is already on disk
- **Severity:** P0
- **Pages:** `/portfolio`, `/api/portfolio`
- **Evidence:** Live HTML (`portfolio.html` as served) is “Portfolio · default”, path `apps/analysis_web/.local/portfolio.json`, error *No book at …portfolio.json. Copy portfolio.example.json → .local/portfolio.json* plus `python -m apps.analysis_web.import_ib`. Meanwhile `.local/portfolio.sqlite` exists (69 632 bytes, imported 2026-09-05) with **21 positions** (ADYEN, HY9H/000660.KS, MC.PA, 1571, AVGO, META, 4516.T, 7203.T, …), NAV ~2.03M HKD, period 2025-10-21 → 2026-09-03. Current `active_portfolio_view` in `apps/analysis_web/services/portfolio.py` joins that sqlite: 21 names, 20 covered, 1 missing (`1008.HK`), 18 PASS. The process on `:8765` still serves the JSON-empty card. `/health` `git_sha` is `—`; `/architecture` is `{"detail":"Not Found"}`. **Regression / leftover** of shipped IB join (`2026-09-05-ib-portfolio-v1`), not a request to rebuild IB.
- **Why it matters:** Job B is “what is in my book with no recent PASS?” That is the only page that can answer it. Live, I cannot see coverage gaps, MoS, or live vs as-of without opening sqlite myself. The empty-state copy talks to an engineer, not the person who already imported the statement.
- **Recommendation:** Make the running UI load `portfolio.sqlite` the way `active_portfolio_view` already does (process identity / restart so `:8765` matches this tree). Then change `templates/portfolio.html` empty-state to “Import an IB activity statement” with a file path, not a Python module line, and put **Portfolio next to Runs** in `templates/base.html`.
- **Keep vs reshape:** Keep the sqlite book + catalog overlay. Reshape only the live binding and the empty-state voice.

### F2 — Audit PASS is the only verdict on the blotter; duration `pass` (do not initiate) is invisible
- **Severity:** P0
- **Pages:** `/`, `/runs/{run_id}`, `/artifact` README
- **Evidence:** Default runs table (`partials/runs_table.html`) shows Audit badges; live list is wall-to-wall PASS (FAIL filter: *0 shown · 0 matching*). Open `research:4516.T:2026-09-06`: MoS **42.7**, Downside **12.1**, Audit PASS. The CIO cover (`/artifact?…/reports/00_4516.T_README.md`) says **`duration.action = pass`** — do not initiate/add; cliff + wide cone; MoS is not a license to buy. AVGO `2026-09-01`: MoS **−75.5**, Downside **81.3**, Audit PASS; README: **Duration action: `pass`**. `pass`. Snapshot already stores `decision_action`, `cheap_claim`, `verdict_line` (`archive/research/4516.T/2026-09-06/meta/prediction_snapshot.json`); catalog `get_run` / the table do not show them. Run detail Context table (`run_detail.html`) repeats Audit / Harness / Exported, not duration / cheap claim / company name (Nippon Shinyaku only appears inside the README).
- **Why it matters:** “Is this cheap vs bear?” and “may I add?” are different questions. PASS in this product means *process complete*. `pass` in the cover means *do not initiate*. A morning scan of PASS + MoS 42.7 on 4516.T is a false buy cue until you open the 6.5 KB cover.
- **Recommendation:** Display-only overlay from the stored snapshot (not a second FV): on `partials/runs_table.html` and `run_detail.html`, show **Duration** (`decision_action`) and **Cheap claim** next to Audit; relabel Audit to **Audit (process)**. Pull `verdict_line` as the one-sentence subhead on run detail. Do not invent actions if the snapshot lacks them.
- **Keep vs reshape:** Keep Audit as process completeness. Keep Downside % vs stored bear. Add the already-written duration fields; do not redesign Mode A.

### F3 — Two-session compare hides the number strip; “did my view change?” is a 38 KB memo plus empty cells
- **Severity:** P0
- **Pages:** `/compares/{id}`, `/compares`, `/`, `/runs/{run_id}`
- **Evidence:** Complete packet `compare:AVGO:2026-09-04__2026-08-23__r3_vs_2026-09-01` flashes “Read the synthesis first” then a **Headline** table with session keys as headers and **blank** `asof_price` / `fv_base` / `MoS` cells (`templates/compare_detail.html` `{{ row.values[key] }}`). On-disk `headline.json` has the numbers (368.45 vs 370.34, FV 108.46 vs 210.99, MoS −239.7 vs −75.5). Jinja treats `.values` as `dict.values`, so the helper table is empty on complete *and* failed jobs. Synthesis then leads with filesystem paths (`archive/research/AVGO/…`, absolute `C:\Users\user\…`) before “Lead with the answer.” Compare list shows the same AVGO pair twice (complete + failed) as `compare:AVGO:…` IDs. Runs-list Compare hint (`static/compares.js`) prints full `run_id`s. Failed job: “Grok process exited before 99_synthesis.md” plus empty headline and a packet path.
- **Why it matters:** Job D is “did the latest run change my view?” I need A vs B price, FV, MoS, Downside, duration in one glance, then the synthesis sentence. Live, the glance is empty and the sentence is below a path table. I cannot tell failed vs useful without opening the job.
- **Recommendation:** In `templates/compare_detail.html` use `row['values'][key]` (and format like `fmt_num`). Lead the page with that strip + the synthesis H2 “Lead with the answer”; demote packet path / `compare_id` / README. On `/compares`, show ticker + sessions + status, hide the failed twin of a later complete packet. Keep the six-persona audit; do not blend FVs.
- **Keep vs reshape:** Keep snapshot headline + Grok synthesis. Fix the template bug; reshape the first screen to allocator, not packet.

### F4 — Home is a 50-row session dump, not “latest per ticker”
- **Severity:** P1
- **Pages:** `/`
- **Evidence:** Live `/` is “Research runs · source: catalog sqlite · 50 shown · 89 matching · max 50”. Default order is ticker then session (`packages/catalog_api/client.py` `_DEFAULT_ORDER_SQL`). First row is `000660.KS` 2026-07-29 (MoS −114.7, Downside 73.6), not the newest work (`4516.T` 2026-09-06). AVGO appears five times on a prefix filter; 02618.HK twice. HTML offset is hardcoded 0 (`routes/pages.py`); there is no Next. No watchlist, no “latest per ticker”, no “needs research”, no running-job chip. Downside % is not a sort header (`partials/runs_table.html`).
- **Why it matters:** Morning scan should be one row per name I care about, newest first, cheap-vs-bear and duration visible. I currently Excel-filter 89 sessions or type prefixes. 39 runs are below the fold with no pager.
- **Recommendation:** Default `/` (or a **Latest** toggle next to Filter) to one row per ticker, `session_date` desc, with live / MoS / Downside / Duration / Audit. Keep the current session dump behind **All sessions**. Add a visible “89 matching · show next” or raise default when Latest is on. Do not add a second FV.
- **Keep vs reshape:** Keep live search, column sort, two-checkbox Compare. Reshape the default grain from session to name.

### F5 — Primary chrome talks to the harness author; operator jobs are last or 404
- **Severity:** P1
- **Pages:** all (`templates/base.html`), `/health`, `/harness`, `/architecture`
- **Evidence:** Header: **Archive Analysis** · *catalog + job scheduler · Analyze starts Mode A · Compare appends archive/comparisons/*. Nav order: Runs, Analyze, Architecture, Harness, Compares, Health, Experiments, Calibration, **Portfolio**. Live Architecture → JSON 404. Live Harness → *workflow_spec failed:* (empty). Health dumps `git_sha —`, `db_path` sqlite, `ARCHIVE_ROOT`. Runs subtitle is “source: catalog sqlite”. Analyze H1 is “Mode A Analyze”. Compare IDs and run_ids are the page titles.
- **Why it matters:** Nine equal links, four of them factory (Architecture, Harness, Health, Experiments). The book is last. A dead Architecture link and a blank Harness error train me not to trust the rest of the chrome.
- **Recommendation:** `base.html`: title **Research**, tagline one investor sentence (“Catalog of completed research · Analyze starts a run”). Nav: **Runs · Portfolio · Analyze · Compares**, then a **Lab** disclosure for Harness / Architecture / Health / Experiments / Calibration. Stop putting `run_id` / sqlite paths in H1; keep them in a `<details>` or muted line.
- **Keep vs reshape:** Keep all routes. Reshape information scent, not the server-rendered tree.

### F6 — Kickoff and wait are honest about hours, then leave the PM with pid and byte sizes
- **Severity:** P1
- **Pages:** `/analyze/new`, `/analyze`, `/analyze/{id}`, `/`
- **Evidence:** `/analyze/new` copy is good on wall time (hours; confirm 2–8h; UI kill does not stop Grok; cap 3/4). The form is factory: slug `__r2`, harness `live` vs 2.39.0…2.27.0, orchestrator/subagent model, “Ingest library inbox”, “Start Mode A analysis”. `/analyze` is a complete-only log (live: every job `complete`; none `running`/`queued`). Job page `analyze:4516.T:2026-09-06`: “Yahoo listing not stamped yet”, `mode=new · harness=2.39.0 · pid=45876`, then **Artifacts** as `charts/price_trend.png 170484` … JSON paths, not “Open CIO cover”. `analyze:COHR:2026-09-03`: complete, **phase orch**, error *abandon.json present on finalized session*, audit —. `analyze_detail.js` only reloads on status change; no phase ETA, no “read last session while you wait.” Home never shows in-flight work.
- **Why it matters:** Job C is “is an analysis still running?” and “what do I do for 2–8 hours?” I get confidence on duration at submit, then a process table. After complete I still hunt reports via `/runs/…` instead of a first-class README link.
- **Recommendation:** `analyze_new.html`: ticker + as-of required; harness/models/slug under **Advanced**. `analyze.html` + header: a **Running** chip when any job is `running`/`queued`. `analyze_detail.html`: human phase (“Valuation”, not `orch`), elapsed vs “typically 2–8 hours”, link to last catalog README for that ticker, and on complete put **Open CIO cover** above the byte list.
- **Keep vs reshape:** Keep confirm dialog, cancel-vs-discard, no FV until snapshot. Reshape the wait screen to operator time, not Grok pid.

### F7 — Forty-page reports have a CIO cover; the viewer starts on a filename
- **Severity:** P1
- **Pages:** `/artifact`, `/runs/{run_id}`
- **Evidence:** `templates/report.html` H1 is `reports/00_4516.T_README.md` (title tag too). The markdown H1 *4516.T — Nippon Shinyaku — CIO cover* is the second heading. No TOC, no sticky section nav (`app.css` `.report-body` is max-width 52rem, headings only). README “Full reports” links are `href="01_AVGO_fundamental.md"` — relative files, not `/artifact?run_id=…` (`services/render_markdown.py` does not rewrite session-relative hrefs). Run detail “Primary reports” is README / Fundamental / Technical plus a second identical “All reports/ (allowlisted)” table with sizes and “raw_sec denied by design.”
- **Why it matters:** Job “what should I read first in a 40-page report?” is already answered by Mode A (the 00 README). The viewer makes me read a path, then a process-PASS disclaimer, then the verdict. Clicking through to the fundamental from the cover 404s in-browser.
- **Recommendation:** `report.html`: use the first markdown H1 as page title; inject a heading TOC for h2/h3; rewrite sibling `.md` hrefs to `/artifact?run_id=&path=reports/…`. Run detail: one **Read CIO cover** button, drop the duplicate allowlist card behind details. Do not change report generation.
- **Keep vs reshape:** Keep rendered markdown + raw toggle + README-first trio. Reshape chrome around the cover.

### F8 — Portfolio template, even when the join works, is not a live blotter
- **Severity:** P1
- **Pages:** `/portfolio` (`templates/portfolio.html`, `services/portfolio.py`)
- **Evidence:** Working-tree join (not what `:8765` currently paints) already has coverage 20/21, missing `1008.HK`, COHR/CMCSA rows with no MoS, META on `2026-08-23__r3`, HY9H MoS −114.7, mean MoS ~4%. Template columns: Weight, Price (catalog **as-of**), FV base, MoS %, Audit, Session — **no Live, no Downside %, no days since session, no duration.action, no “Start analysis” on missing**. Note admits as-of snapshots, not live marks. IB close sits in a desktop-only column, unlabeled vs as-of. PASS-only is a yes/no, not “stale PASS (>14d)”.
- **Why it matters:** After F1 is fixed I still cannot see cheap-vs-bear on the book, or names that need research, without a spreadsheet. Weighted mean MoS of 4% hides AVGO −75 and 2209 +69.
- **Recommendation:** Same display math as `/`: live print + Downside % vs stored bear; **Age** from `session_key`; missing/un-PASS rows highlighted with link to `/analyze/new?ticker=`. Do not recompute FV.
- **Keep vs reshape:** Keep IB NAV/TWR/MTM bars and catalog overlay. Add the decision columns already on Runs.

### F9 — “Cheap vs bear” is on the page but not operable
- **Severity:** P1
- **Pages:** `/`, `/runs/{run_id}`
- **Evidence:** Downside % is live-recomputed (`static/quotes.js` `(price − bear) / price`) — correct display math. It is not sortable; MoS is. Negative Downside (`0762.HK` −15.4) means **already below bear** and is unlabeled. MoS is vs base FV (AVGO −75.5) while Downside is vs bear (81.3). Runs list has no currency; 000660.KS 1,401,000 sits next to ACN 189. Live cells are `—` until JS; `/api/quotes` for AVGO is 357.87 (weekend print 2026-09-04) vs as-of 370.34 — the interesting move — but only after quotes.js. Quote cap 50 unique listings (`quotes.js` `MAX_SYMBOLS`).
- **Why it matters:** The question I actually ask is Downside, not MoS. I cannot sort to “smallest cushion to bear” or “already through bear.” Sign convention is easy to misread under time pressure.
- **Recommendation:** Sortable Downside column; header tooltip stays. Color / label negatives as **Below bear**. Put a one-line legend on `/`: “MoS vs base FV · Downside vs bear FV (live print when available).”
- **Keep vs reshape:** Keep the formula and live recompute. Do not add a third valuation.

### F10 — Calibration and Experiments are lab pages in the daily nav
- **Severity:** P1
- **Pages:** `/calibration`, `/experiments`
- **Evidence:** Calibration live: *MoS direction hit vs realized outcomes (sqlite join)* · Joined rows **0** · *No outcomes joined for this horizon*. Experiments: *Grouped from catalog runs (limit 500 scan)* · one section **(none)** · **89 run(s)** — a second copy of `/`. No experiment_id is in use. Both sit in the top nav equal to Portfolio.
- **Why it matters:** An investor asking “is the process calibrated?” gets an empty join and a dump of untagged names. That is useful to the harness author once outcomes exist; it is noise every morning until then.
- **Recommendation:** Move both under Lab (see F5). On Calibration, if `n_joined == 0`, say “No marked outcomes yet — this is not a hit-rate on the book.” Do not build a fake calibration.
- **Keep vs reshape:** Keep the pages. Do not pretend they are a PM dashboard.

### F11 — Engineer leftovers (merged nits)
- **Severity:** P2
- **Pages:** `/health`, `/harness`, `/architecture`, `/analyze/{id}`, `/compares/new`, reports
- **Evidence:** Health is a sqlite/path dump. Harness `workflow_spec failed` with no recovery. Architecture 404 JSON. Compare form is two 89-option dropdowns of `run_id` + FV. Analyze artifacts listed as byte sizes. “This is not a buy list” repeats while Audit PASS still looks like a buy list (F2). Mixed JPY/HKD/USD in one MoS column with no unit.
- **Why it matters:** Polish and trust, not the blocking jobs — except where they duplicate F1/F5.
- **Recommendation:** One Lab index; compare_new filter-by-ticker first; currency on numeric cells.
- **Keep vs reshape:** Keep Health/Harness for the operator who is also the builder, off the morning path.

## What already works

- Downside % from stored bear vs as-of, then live print (`quotes.js`) — the right cheap-vs-bear math, not a second DCF.
- Live Yahoo cells and chg background on `/` and run detail (JS-filled; API confirmed AVGO 357.87).
- Run-detail **Price vs analysis** chart with bear/base/bull overlay and sibling session markers (`price_chart.js`, overlay JSON on 4516.T and AVGO).
- Two-checkbox same-ticker Compare on `/` plus run-detail sibling dropdown (`FV` + `MoS` in the option text) — the right grain for job D.
- Compare **synthesis** when complete is actually written for a capital allocator (“Pass at $368–$370. Do not average $108.46 and $210.99.”) once you scroll to “Lead with the answer.”
- Mode A CIO README (00) is the correct first read: duration, cheap claim, cone, top-3 risks. Do not rewrite those reports.
- Analyze confirm of 2–8 hours, cancel vs discard, “no FV until snapshot” — honest about cost of a run.
- Catalog 404 on unknown ticker with a link to `/analyze/new?ticker=` — right abort, not an empty table.
- IB join **in this tree** (21 names, 1008.HK missing, HY9H→000660.KS overlay) is the right book mechanism once the live process serves it.
- Phone stack-table, Menu disclosure, Night/Light — usable; not the blocker.
- Server-rendered HTML; extra JS only for quotes, chart, theme, live reload — appropriate for a localhost operator tool.

## From-scratch keepers

- One row of **ticker · session · live · FV cone · MoS · Downside · duration · audit** as the atomic blotter cell.
- Catalog as read-only index; display math only for live and Downside.
- CIO cover markdown as the first artifact; fundamental/technical behind it.
- Two-session Grok compare that **does not blend** FVs; snapshot headline + synthesis.
- IB sqlite as the book; JSON only if sqlite is absent.
- Analyze as a long job with keep-session cancel; never author FV in the UI.
- FastAPI + Jinja + small JS. No SPA.

## Do not do

- React/SPA rewrite.
- A second fair value or blended compare target in the UI.
- Rewriting Mode A phases, prompts, or report templates to “fix” the reader.
- Dropping Audit PASS (still need process completeness) or relabeling it as a buy list.
- Fake calibration hit-rates from empty outcomes.
- Watchlist as a third store of weights/FVs; the IB book + latest-per-ticker is the watchlist.
- Public SaaS marketing chrome.
- `git commit` or archive mutations as part of this review.
