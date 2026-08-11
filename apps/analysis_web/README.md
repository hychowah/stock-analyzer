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
| `/artifact?run_id=…&path=reports/…` | Allowlisted artifact view |
| `/experiments` | Group by `experiment_id` |
| `/calibration` | MoS vs outcomes |
| `/portfolio` | Portfolio (book in `.local/`; full join later) |
| `/health` | Catalog health probe |
| `/api/health`, `/api/runs` | JSON API for clients / HTMX |

## App-local state

- Portfolio book (optional): `apps/analysis_web/.local/portfolio.json`
- Example: `portfolio.example.json` (committed)
- **Never** store holdings under `archive/research/`

## Security

- Opens sqlite **readonly**
- Artifacts via `CatalogApi.open_artifact` (containment + allowlist; `raw_sec` denied)
- Does **not** run research phases or write archive
- Default bind `127.0.0.1`
