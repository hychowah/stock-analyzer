# Analysis Web (Mode B)

Human map of the whole system: `ARCHITECTURE.md`. Catalog UI over `packages.catalog_api` and the **live `archive/`** data plane. Research sessions stay immutable. **Analyze** schedules a Mode A Grok orchestrator (new `archive/research/` session + `archive/research_jobs/` control plane). **Compare** appends `archive/comparisons/` with a session-valuation-audit. This app does **not author** FV/MoS.

**Stack:** FastAPI + Jinja2 + static CSS (`runs.js` list search, `compares.js` two-select, SSE live reload, markdown reports).

## Install

```bash
pip install -r apps/analysis_web/requirements.txt
```

## Run

```bash
# From project root (default: replace this UI when git HEAD moves)
python3 -m apps.analysis_web
# → http://127.0.0.1:8765/

python3 -m apps.analysis_web --no-auto-restart   # freeze this process
ARCHIVE_ROOT=/path/to/archive python3 -m apps.analysis_web --port 8765
```

Or: `bash apps/analysis_web/init.sh`

## Pages

| Path | Purpose |
|------|---------|
| `/` | Run list: live prefix search, filters, column sort, optional Latest-per-ticker; Downside % is (price − bear FV) / price (as-of, then live print). Duration is the stored snapshot action; Audit is process completeness |
| `/runs/{run_id}` | Run detail (decision strip, football-field PNG + Read CIO cover when present, price vs analysis, Context; bear/base/bull/model in details) |
| `/run?run_id=…` | Redirect → `/runs/…` (bookmark compat) |
| `/artifact?run_id=…&path=reports/…` | Report view (markdown title + TOC + sibling `.md` links on `/artifact`; `raw=1` for source) |
| `/experiments` | Group by `experiment_id` |
| `/calibration` | MoS vs outcomes |
| `/portfolio` | Portfolio: IB sqlite book (or `.local/portfolio.json` fallback) joined to latest catalog runs. Header is Live NAV + day P/L (not statement period or ending NAV). One poll (`/api/portfolio/live-nav`) paints Live NAV, Live cells, live value, Downside, and a day-move heatmap (tile area is \|day P/L\| of that holding; gainers left, losers right). Does not call `/api/quotes`. Change-in-NAV waterfall + MTM bars. Sub-nav Book · What-if. |
| `/portfolio/histories` | Alternative histories (what-if). Frozen paper copies of the IB stock ledger (seed + fills); overlay chart when two or more exist. Does not call `/api/portfolio/live-nav`. Does not open the live IB book. |
| `/portfolio/histories/new` | The only IB read: copy stock trades and freeze seed lots, cash, and statement FX. A later IB re-ingest does not change the copy. |
| `/portfolio/histories/{id}` | Paper book first (lots and cash that day; names later sold on this copy are a page badge). Close/value/weight/Downside/MoS are pending until the held-table fragment (not a blank price). Header cash is today. The date control is the paper account on D: historical close, cash/stock/NAV, paper Reg-T loan/excess/buying power. One ticket: search the researched list to buy, pick a holding to sell. Marks, universe closes, and the NAV path load separately. Path JSON includes a last-point Δ breakdown (gains at top, losses at bottom). JS POST does not navigate. Header Δ is the chart end. Actual is this copy. Works if the IB file is later missing. |
| `/analyze` | Mode A jobs (`archive/research_jobs/`). List does not SSE-reload. |
| `/analyze/new` | Start analysis (ticker + as-of + harness first; advanced in details). Busy stays on the form. |
| `/architecture` | Human map: live repo `ARCHITECTURE.md` (working tree, not a pin). Diagrams are inspectable figures (pan/zoom, Reset). |
| `/harness` | Pin map: staged pipeline + briefing inspector (prompt on demand) |
| `/api/harness/spec`, `/api/harness/prompt` | JSON from `Pin.workflow_spec` / `Pin.agent_prompt` |
| `/analyze/{analyze_id}` | Wait page is resume_hint (phase hidden when hint exists); meta refresh 15s while running; complete offers Open catalog run / Read CIO cover; cancel = keep session; discard = abandon |
| `/analyze-artifact?analyze_id=…&path=…` | In-progress: handoffs/phase only; FV and report bodies 403 until snapshot |
| `/compares` | Compare packets (`archive/comparisons/`). List does not SSE-reload. |
| `/compares/new` | No-JS form to start a two-session Grok audit. Busy/Grok-missing stay on the form. |
| `/compares/{compare_id}` | Job status, headline table, README + `99_synthesis.md` when complete; Retry on failed |
| `/compare-artifact?compare_id=…&path=…` | Allowlisted packet file (markdown rendered) |
| `/api/compares` | GET list / POST start (`run_id_a`, `run_id_b`) |
| `/api/compares/{compare_id}` | JSON job status |
| `/api/portfolio` | JSON portfolio summary + positions + `ib` + `performance` (statement join; no Yahoo). `performance.mtm` rows are `{name, pl, bar_pct, sign}` (gains at top, losses at bottom) |
| `/api/portfolio/live-nav` | Statement NAV adjusted by holdings × Yahoo last print. Aggregates + `quotes` (QuotePrint JSON) + per-lot `rows` (each row has `day_pl`). Display math; FX is the statement Forex close |
| `/api/portfolio/histories` | List alternative histories + today Δ from the cash-book mark (daily close), not Live NAV |
| `/api/portfolio/histories/{id}` | History document (name, fork, fills). No holdings, no path, no Yahoo. |
| `/api/portfolio/histories/{id}/holdings` | As-of account: `held` + `account` (cash/stock/NAV, paper Reg-T loan/excess/buying power). Cash is `account.cash` as of `date`, not a top-level field. No sold-later flag. |
| `/fragments/portfolio/histories/{id}/held` | HTML as-of pane (account strip + holdings table with Weight % of quoted stock, Downside % vs the close on the row, stored MoS). Same partial as first paint (pending, then ready). Marks and cash as of that date, not cash-today. Sold-later is a page join. Not a shareable page. |
| `/fragments/portfolio/histories/{id}/fills` | HTML what-if fill timeline. Same partial as first paint. Not a shareable page. |
| `/api/portfolio/histories/{id}/universe` | Catalog snaps plus close on D (`pickable` only when quoted with FX; `block` is the English reason if not). Second fetch so 200 names do not block the as-of pane. |
| `/api/portfolio/histories/{id}/ticket` | GET preview of the persist Ticket (`mark`, `cost_base`, `currency`, `after`, `block`, `held_qty`). `POST /decisions` saves it or returns the same `block`. |
| `/api/portfolio/histories/{id}/path` | NAV walk + SVG. Last point is header Δ. `breakdown` is that point’s per-name and cash contribution (gains at top, losses at bottom). No holdings. |
| `/api/portfolio/histories/{id}/path.svg` | Same path as an SVG image (no-JS chart). |
| `/health` | Catalog health plus the git SHA this UI process booted at |
| `/fragments/runs` | HTML table fragment for live search/sort (not a shareable page) |
| `/api/health`, `/api/runs` | JSON API (`ticker` exact, `ticker_prefix` starts-with, ranges, `harness_version`, `sort`/`dir`) |
| `/api/quotes` | Last print for catalog `quote_listing` values (Runs and run detail). Chart-name repair is in `yahoo_bars`; rows stay keyed by the request. Portfolio does not call this. |
| `/api/price-history` | Daily closes for one `quote_listing` (`symbol`, `range=1m\|3m\|6m\|1y\|2y\|5y\|max`) |
| `/api/events` | SSE: `hello`, `catalog_changed`, `portfolio_changed` |
| `/api/fingerprint` | Poll fallback token for live reload |

Runs list (`/`): type in Ticker to filter **starts-with** (`ticker_prefix`). Sector / region / tech / harness are dropdowns of catalog values. Session date, MoS %, price, and FV base take **inclusive ranges**. All of that updates live; click headers to sort. A ticker/prefix that matches **no catalog ticker** aborts with HTTP 404 (do not treat an empty table as “keep going”). A real ticker with other filters that yield zero rows still shows **No runs** (200).

Shareable query example: `/?ticker_prefix=M&sector=growth&harness_version=2.17.0&session_date_from=2026-08-01&mos_min=0&sort=margin_of_safety_pct&dir=desc`. Default `limit=50` is omitted from the query string. Empty `/` is the catalog dump (no `latest`). `/?latest=1` is at most one row per ticker after the other filters.

Header **Runs**, the brand, and run-detail **← Runs** remember the last non-empty query (browser `localStorage`). When storage is empty, those chrome links go to `/?latest=1` (one row per ticker). Empty `/` and **Reset** stay the All dump and are not rewritten from storage. A pasted query URL becomes the new memory.

Header **Night** / **Light** switches page chrome. The choice is browser-local (`localStorage` key `analysis_web.theme`), not archive. First visit follows the OS light/dark setting until you click.

The header is two maps: **Primary** (Runs, Analyze, Compare, Portfolio) and **Lab** (Harness, Architecture, Experiments, Calibration, Health). Below 1100px (the same width as `main`) the tagline hides and each group sits behind its own **Menu** / **Lab** control (CSS checkbox; no extra JS). Wide one-entity lists (Runs, Portfolio positions, Analyze jobs, Compares, Experiments, Calibration) sit in a freeze pane: column titles and the lead identity column stay while you scroll the pane down or sideways. Secondary columns stay in the table (scroll right). The page itself does not scroll sideways. On Runs, ticker + **Apply** + **Reset** stay visible; extra filters sit behind **Filters** (same checkbox pattern; collapsed is not omitted — live search still serializes every field). Desktop (`min-width: 1101px`) hides the disclose checkboxes so they are not tab stops.

| Param | Meaning |
|-------|---------|
| `ticker` | Exact ticker (legacy bookmarks) |
| `ticker_prefix` | Ticker starts-with |
| `sector`, `region`, `audit_verdict`, `tech_signal`, `harness_version`, `experiment_id` | Exact |
| `session_date_from`, `session_date_to` | Inclusive `YYYY-MM-DD` |
| `mos_min`, `mos_max` | Inclusive MoS % |
| `price_min`, `price_max` | Inclusive as-of price |
| `fv_base_min`, `fv_base_max` | Inclusive FV base |
| `sort`, `dir` | Allowlisted column + `asc`/`desc`. `asof_downside_pct` is stored as-of vs bear (not a run field, not the live cell) |
| `latest` | `1` = at most one row per ticker (newest session) after other filters; omitted on empty `/` |
| `limit` | Page size, 1–200; default 50 is omitted from the query string |

No-JS: the GET form still submits. Invalid ranges (min > max, bad date) return HTTP 400. Unknown ticker / prefix returns HTTP 404 and an abort card.

Portfolio live marks (`data-quote-poll="0"` + `static/live_nav.js`): one GET `/api/portfolio/live-nav`; `quotes.js` paints Live/Downside from `quotes-applied` and does not fetch `/api/quotes` on that page. `heatmap.js` paints the day-move map from `live-nav-applied` (same payload; no extra fetch).

Catalog live reload (`data-live-reload="1"` + `static/live.js`): SSE first, 5s fingerprint poll if SSE is unhealthy. On the runs page (`data-live-partial="1"`) a catalog change refetches `/fragments/runs` instead of a full reload, so an in-progress ticker search is not wiped. Analyze and Compare list/detail pages do not opt in; a running job patches status in JS and uses `<meta refresh=15>`.

Runs list also has checkboxes: select **exactly two** rows of the **same ticker** and **Compare**. That POSTs `/api/compares` and redirects to the job page. Headline numbers come from `prediction_snapshot.json` immediately; completion is `99_synthesis.md` on disk.

Env: `COMPARE_SPAWN=fake` writes a stub compare packet (tests). `AGENT_SPAWN=fake` is the Analyze fake (job_dir only; never writes FV). Default spawns `grok --prompt-file … --yolo` (`GROK_BIN` to override). Caps: `ANALYZE_MAX=3`, `COMPARE_MAX=1`; unset `GROK_JOBS_MAX` is their sum. Set `GROK_JOBS_MAX=1` on laptops to serialize. `STOCK_RESEARCH_LOCAL` overrides the sqlite/lock home (`%LOCALAPPDATA%\StockResearch` or `~/.local/share/stock-research`); test `ARCHIVE_ROOT` trees keep sqlite beside that archive. Do **not** run with uvicorn `--reload`. Default `python -m apps.analysis_web` polls `git rev-parse HEAD` and replaces **only the UI** when the SHA changes (uncommitted saves do not). `--no-auto-restart` is the one-shot server (debug freeze, and the supervised child). Git unreadable → keep serving. First Ctrl+C exits within a few seconds even with live-reload tabs open. Killing or replacing the UI does **not** kill Grok; startup reconciles `job.json` (Analyze and Compare). Cancel is kill-only (resumable); Discard writes `abandon.json`. Before resume, confirm no leftover `grok.exe`. If a Store-Python wrapper leftover holds the port, `taskkill /F` the `python3.12.exe` PID. Real Grok Analyze refuses a non-default `ARCHIVE_ROOT` (Mode A scripts ignore it). Isolation is prompt/runbook, not an OS sandbox. `harness_version=live` jobs use the workspace (`prompt.md` frozen; `PYTHONPATH`/`cwd` are not) — a harness commit can affect a running live Grok on the next import whether or not the UI restarted. OneDrive may delay SSE mtimes — pause sync on `archive/` if jobs flap. SSE `hello` carries `git_sha` (process identity, not the catalog token); `live.js` reloads once when that SHA changes.

## App-local state

- IB book (preferred): app-local `portfolio.sqlite` (`STOCK_RESEARCH_LOCAL/analysis_web` or OS local home; legacy `apps/analysis_web/.local/` if that book already exists) — a trade ledger plus the latest statement snapshot. Ingest with `python -m apps.analysis_web.import_ib` (optional `--src`). Overlapping CSVs merge: new fills append, existing fills are skipped, trades are never deleted. `--rebuild` wipes sqlite and replays every `U*.csv` under the app-local `ib/statements/` folder (the only start-over). Copies `U*.csv` (and sibling `.pdf`) into that folder. **PII; gitignored. Import does not write `portfolio.json`.**
- Alternative histories: the same app-local dir, `alt_histories.sqlite` — frozen seed (lots + cash + statement FX) plus copied IB stock fills plus what-if fills. Never writes `portfolio.sqlite` trades. Live IB is read only at copy. Replay on read; NAV is not stored. Later real sells of a name you already sold in the paper book are clipped before strict replay. What-if buys may run cash negative (the loan) and are gated on paper Reg-T buying power at POST, not cash on hand. `GET /holdings` is the as-of account (lots + marks + paper Reg-T). Display math (weight, Downside vs daily close, stored MoS) is on the held fragment. JS POST `/decisions` with `Accept: application/json` does not navigate. First HTML paint does not wait on Yahoo.
- JSON fallback (only when sqlite is missing): `portfolio.json` next to the sqlite book
- Example: `portfolio.example.json` (committed)
- **Never** store holdings under `archive/research/`
- Unreadable sqlite fails `/portfolio`; it does not fall back to JSON
- Compare packets: `archive/comparisons/<TICKER>/<asof>__<A>_vs_<B>/` (gitignored)
- Analyze jobs: `archive/research_jobs/<TICKER>/<SESSION_KEY>/` (gitignored; not a catalog source)

## Security

- Opens sqlite **readonly**
- Artifacts via `CatalogApi.open_artifact` (containment + allowlist; `raw_sec` denied)
- Compare artifacts via `open_compare_artifact` (packet-root `.md` / `job.json` / `headline.json` only)
- Does **not** run research phases or rewrite `archive/research`
- Compare spawn is localhost-only (`127.0.0.1`) and uses `--yolo` because the skill must write the packet and fan out subagents
- Default bind `127.0.0.1`
