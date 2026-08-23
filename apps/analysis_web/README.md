# Analysis Web (Mode B)

Read-only UI over `packages.catalog_api` and the **live `archive/`** data plane.

**Stack:** FastAPI + Jinja2 + static CSS (`runs.js` list search, SSE live reload, markdown reports).

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
| `/api/portfolio` | JSON portfolio summary + positions |
| `/health` | Catalog health probe |
| `/fragments/runs` | HTML table fragment for live search/sort (not a shareable page) |
| `/api/health`, `/api/runs` | JSON API (`ticker` exact, `ticker_prefix` starts-with, ranges, `harness_version`, `sort`/`dir`) |
| `/api/events` | SSE: `hello`, `catalog_changed`, `portfolio_changed` |
| `/api/fingerprint` | Poll fallback token for live reload |

Runs list (`/`): type in Ticker to filter **starts-with** (`ticker_prefix`). Sector / region / tech / harness are dropdowns of catalog values. Session date, MoS %, price, and FV base take **inclusive ranges**. All of that updates live; click headers to sort.

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

No-JS: the GET form still submits. Invalid ranges (min > max, bad date) return HTTP 400.

Catalog live reload (`data-live-reload="1"` + `static/live.js`): SSE first, 5s fingerprint poll if SSE is unhealthy. On the runs page (`data-live-partial="1"`) a catalog change refetches `/fragments/runs` instead of a full reload, so an in-progress ticker search is not wiped.

## App-local state

- Portfolio book (optional): `apps/analysis_web/.local/portfolio.json`
- Example: `portfolio.example.json` (committed)
- **Never** store holdings under `archive/research/`

## Security

- Opens sqlite **readonly**
- Artifacts via `CatalogApi.open_artifact` (containment + allowlist; `raw_sec` denied)
- Does **not** run research phases or write archive
- Default bind `127.0.0.1`
