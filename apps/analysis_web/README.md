# Analysis Web (Mode B)

Read-only UI over `packages.catalog_api` and the **live `archive/`** data plane.

**Stack:** FastAPI + Jinja2 + static CSS (HTMX/SSE/markdown rendering phased in).

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
| `/` | Filterable run list |
| `/runs/{run_id}` | Run detail (FV, MoS, audit, report links) |
| `/run?run_id=…` | Redirect → `/runs/…` (bookmark compat) |
| `/artifact?run_id=…&path=reports/…` | Report view (markdown → sanitized HTML; `raw=1` for source) |
| `/experiments` | Group by `experiment_id` |
| `/calibration` | MoS vs outcomes |
| `/portfolio` | Portfolio: `.local/portfolio.json` joined to latest catalog runs |
| `/api/portfolio` | JSON portfolio summary + positions |
| `/health` | Catalog health probe |
| `/api/health`, `/api/runs` | JSON API for clients / HTMX |
| `/api/events` | SSE: `hello`, `catalog_changed`, `portfolio_changed` |
| `/api/fingerprint` | Poll fallback token for live reload |

Runs list page opts into live reload (`data-live-reload="1"` + `static/live.js`):
SSE first, 5s fingerprint poll if SSE is unhealthy.

## App-local state

- Portfolio book (optional): `apps/analysis_web/.local/portfolio.json`
- Example: `portfolio.example.json` (committed)
- **Never** store holdings under `archive/research/`

## Security

- Opens sqlite **readonly**
- Artifacts via `CatalogApi.open_artifact` (containment + allowlist; `raw_sec` denied)
- Does **not** run research phases or write archive
- Default bind `127.0.0.1`
