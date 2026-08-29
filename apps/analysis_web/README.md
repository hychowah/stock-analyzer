# Analysis Web (Mode B)

Catalog UI over `packages.catalog_api` and the **live `archive/`** data plane. Research sessions stay immutable. **Analyze** schedules a Mode A Grok orchestrator (new `archive/research/` session + `archive/research_jobs/` control plane). **Compare** appends `archive/comparisons/` with a session-valuation-audit. This app does **not author** FV/MoS.

**Stack:** FastAPI + Jinja2 + static CSS (`runs.js` list search, `compares.js` two-select, SSE live reload, markdown reports).

## Install

```bash
pip install -r apps/analysis_web/requirements.txt
```

## Run

```bash
# From project root
python3 -m apps.analysis_web
# → http://127.0.0.1:8765/

ARCHIVE_ROOT=/path/to/archive python3 -m apps.analysis_web --port 8765
```

Or: `bash apps/analysis_web/init.sh`

## Pages

| Path | Purpose |
|------|---------|
| `/` | Run list: live prefix search, filters, column sort |
| `/runs/{run_id}` | Run detail (FV, MoS, audit, report links) |
| `/run?run_id=…` | Redirect → `/runs/…` (bookmark compat) |
| `/artifact?run_id=…&path=reports/…` | Report view (markdown → sanitized HTML; `raw=1` for source) |
| `/experiments` | Group by `experiment_id` |
| `/calibration` | MoS vs outcomes |
| `/portfolio` | Portfolio: `.local/portfolio.json` joined to latest catalog runs |
| `/analyze` | Mode A jobs (`archive/research_jobs/`) |
| `/analyze/new` | Start analysis (market ticker; catalog membership not required) |
| `/analyze/{analyze_id}` | Live phase/status; cancel = keep session; discard = abandon |
| `/analyze-artifact?analyze_id=…&path=…` | In-progress: handoffs/phase only; FV and report bodies 403 until snapshot |
| `/compares` | Compare packets (`archive/comparisons/`) |
| `/compares/new` | No-JS form to start a two-session Grok audit |
| `/compares/{compare_id}` | Job status, headline table, README + `99_synthesis.md` when complete |
| `/compare-artifact?compare_id=…&path=…` | Allowlisted packet file (markdown rendered) |
| `/api/compares` | GET list / POST start (`run_id_a`, `run_id_b`) |
| `/api/compares/{compare_id}` | JSON job status |
| `/api/portfolio` | JSON portfolio summary + positions |
| `/health` | Catalog health probe |
| `/fragments/runs` | HTML table fragment for live search/sort (not a shareable page) |
| `/api/health`, `/api/runs` | JSON API (`ticker` exact, `ticker_prefix` starts-with, ranges, `harness_version`, `sort`/`dir`) |
| `/api/events` | SSE: `hello`, `catalog_changed`, `portfolio_changed` |
| `/api/fingerprint` | Poll fallback token for live reload |

Runs list (`/`): type in Ticker to filter **starts-with** (`ticker_prefix`). Sector / region / tech / harness are dropdowns of catalog values. Session date, MoS %, price, and FV base take **inclusive ranges**. All of that updates live; click headers to sort. A ticker/prefix that matches **no catalog ticker** aborts with HTTP 404 (do not treat an empty table as “keep going”). A real ticker with other filters that yield zero rows still shows **No runs** (200).

Shareable query example: `/?ticker_prefix=M&sector=growth&harness_version=2.17.0&session_date_from=2026-08-01&mos_min=0&sort=margin_of_safety_pct&dir=desc`.

| Param | Meaning |
|-------|---------|
| `ticker` | Exact ticker (legacy bookmarks) |
| `ticker_prefix` | Ticker starts-with |
| `sector`, `region`, `audit_verdict`, `tech_signal`, `harness_version`, `experiment_id` | Exact |
| `session_date_from`, `session_date_to` | Inclusive `YYYY-MM-DD` |
| `mos_min`, `mos_max` | Inclusive MoS % |
| `price_min`, `price_max` | Inclusive as-of price |
| `fv_base_min`, `fv_base_max` | Inclusive FV base |
| `sort`, `dir` | Allowlisted column + `asc`/`desc` |

No-JS: the GET form still submits. Invalid ranges (min > max, bad date) return HTTP 400. Unknown ticker / prefix returns HTTP 404 and an abort card.

Catalog live reload (`data-live-reload="1"` + `static/live.js`): SSE first, 5s fingerprint poll if SSE is unhealthy. On the runs page (`data-live-partial="1"`) a catalog change refetches `/fragments/runs` instead of a full reload, so an in-progress ticker search is not wiped.

Runs list also has checkboxes: select **exactly two** rows of the **same ticker** and **Compare**. That POSTs `/api/compares` and redirects to the job page. Headline numbers come from `prediction_snapshot.json` immediately; completion is `99_synthesis.md` on disk.

Env: `COMPARE_SPAWN=fake` writes a stub compare packet (tests). `AGENT_SPAWN=fake` is the Analyze fake (job_dir only; never writes FV). Default spawns `grok --prompt-file … --yolo` (`GROK_BIN` to override). Caps: `ANALYZE_MAX=1`, `COMPARE_MAX=1`, `GROK_JOBS_MAX=2` (set `1` on laptops). Do **not** run with uvicorn `--reload`. Killing the UI does **not** kill Grok; startup reconciles `job.json`. Cancel is kill-only (resumable); Discard writes `abandon.json`. Before resume, confirm no leftover `grok.exe`. Real Grok Analyze refuses a non-default `ARCHIVE_ROOT` (Mode A scripts ignore it). Isolation is prompt/runbook, not an OS sandbox. OneDrive may delay SSE mtimes — pause sync on `archive/` if jobs flap.

## App-local state

- Portfolio book (optional): `apps/analysis_web/.local/portfolio.json`
- Example: `portfolio.example.json` (committed)
- **Never** store holdings under `archive/research/`
- Compare packets: `archive/comparisons/<TICKER>/<asof>__<A>_vs_<B>/` (gitignored)
- Analyze jobs: `archive/research_jobs/<TICKER>/<SESSION_KEY>/` (gitignored; not a catalog source)

## Security

- Opens sqlite **readonly**
- Artifacts via `CatalogApi.open_artifact` (containment + allowlist; `raw_sec` denied)
- Compare artifacts via `open_compare_artifact` (packet-root `.md` / `job.json` / `headline.json` only)
- Does **not** run research phases or rewrite `archive/research`
- Compare spawn is localhost-only (`127.0.0.1`) and uses `--yolo` because the skill must write the packet and fan out subagents
- Default bind `127.0.0.1`
