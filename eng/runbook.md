# Eng Runbook (Mode B)

## Environment

| Variable | Meaning | Default |
|----------|---------|---------|
| `ARCHIVE_ROOT` | Dir containing `research/`, `catalog/`, `outcomes/` | `<project>/archive` |

Fixtures: set `ARCHIVE_ROOT` to the absolute path of `eng/fixtures/archive` for offline CI.

## Common commands

```bash
# Scaffold Mode B work session
python3 scripts/scaffold_eng_session.py --slug catalog-api-mvp

# Verify (pytest subset + archive immutability policy checks)
python3 scripts/eng_verify.py

# Catalog health / list (live archive)
python3 -m packages.catalog_api health
python3 -m packages.catalog_api list-runs --limit 5

# Catalog against fixtures (after sync)
ARCHIVE_ROOT=$PWD/eng/fixtures/archive python3 -m packages.catalog_api health

# Research still uses Mode A tools
python3 scripts/scaffold_session.py --ticker META --date $(date +%F)
python3 scripts/check_session.py --ticker META --date 2026-08-03 --full
```

## Concurrency (Mode A write ‖ Mode B read)

1. Mode B always opens sqlite **readonly**.  
2. Writers (finalize/export) should use WAL + busy_timeout (see `compare_db.connect`).  
3. Never run `export_compare_db --all --rebuild` while expecting a hot UI without staging.  
4. Mode B must **not** call export with snapshot refresh on live `archive/research`.

## Fixture refresh

```bash
# Optional: slim copy + re-export (does not mutate live research meta if --no-refresh-snapshot)
python3 scripts/sync_eng_fixtures.py --tickers META,JPM --dates 2026-08-03,2026-07-25
```

## Failure → harness

Record systemic fails in `eng/eval/failure_catalog.md` and open an eng session issue.
