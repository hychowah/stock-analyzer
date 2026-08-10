# Analysis Web (Mode B)

Read-only UI over `packages.catalog_api` and the **live `archive/`** data plane.

## Run

```bash
# From project root
python3 -m apps.analysis_web
# → http://127.0.0.1:8765/

ARCHIVE_ROOT=/path/to/archive python3 -m apps.analysis_web --port 8765
```

Stdlib only (no FastAPI/Flask required).

## Pages

| Path | Purpose |
|------|---------|
| `/` | Filterable run list |
| `/run?run_id=…` | Run detail (FV, MoS, audit, report links) |
| `/artifact?run_id=…&path=reports/…` | Allowlisted artifact view |
| `/experiments` | Group by `experiment_id` |
| `/health` | Catalog health probe |

## Security

- Opens sqlite **readonly**
- Artifacts via `CatalogApi.open_artifact` (containment + allowlist; `raw_sec` denied)
- Does **not** run research phases or write archive
