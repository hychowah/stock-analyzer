# Eng Runbook (Mode B)

## Environment

| Variable | Meaning | Default |
|----------|---------|---------|
| `ARCHIVE_ROOT` | Dir containing `research/`, `catalog/`, `outcomes/`, `library/` | `<project>/archive` |

Fixtures: set `ARCHIVE_ROOT` to the absolute path of `eng/fixtures/archive` for offline CI.

```bash
python3 scripts/sync_eng_fixtures.py   # slim copy + re-export sqlite
export ARCHIVE_ROOT=$PWD/eng/fixtures/archive
python3 -m packages.catalog_api health
```

Mode A full law: `harness/RESEARCH_AGENTS.md` (root `AGENTS.md` is router only).

## Common commands

```bash
# Scaffold Mode B work session
python3 scripts/scaffold_eng_session.py --slug catalog-api-mvp

# Verify (pytest subset + archive immutability policy checks)
python3 scripts/eng_verify.py

# Catalog health / list (live archive)
python3 -m packages.catalog_api health
python3 -m packages.catalog_api list-runs --limit 5

# Analysis UI (FastAPI + Jinja; install deps once)
# pip install -r apps/analysis_web/requirements.txt
python3 -m apps.analysis_web
# or: bash apps/analysis_web/init.sh
# → http://127.0.0.1:8765/
# Runs list: ticker_prefix, sector/region/harness dropdowns, session/MoS/price/FV ranges, column sort
# JSON: python3 -m packages.catalog_api list-runs --ticker-prefix M --harness-version 2.17.0 --mos-min 0 --session-date-from 2026-08-01
# Session compare (Grok audit → archive/comparisons/): UI /compares or
#   COMPARE_SPAWN=fake python -m packages.compare_jobs start --run-a research:META:2026-08-03 --run-b research:META:DATE2
# Mode A Analyze (Grok orchestrator → new archive/research session; control plane archive/research_jobs/):
#   AGENT_SPAWN=fake python -m packages.research_jobs start --ticker COHR --harness-version live
#   python scripts/publish_harness_release.py   # snapshot live runtime → pins/<VERSION>/
#   UI /harness — pin pipeline map + briefing inspector (prompt on demand)
#   python -m packages.research_jobs {list,get,cancel,discard,resume,reconcile}
#   UI /analyze — kill UI does not kill Grok; cancel=kill-only; discard=abandon; ANALYZE_MAX=3; GROK_JOBS_MAX defaults to kind-slot sum (set 1 to serialize)
#   Real Grok Analyze refuses non-default ARCHIVE_ROOT. Do not uvicorn --reload.

# Experiment summary program
python3 programs/experiment_summary.py

# Catalog against fixtures (after sync)
ARCHIVE_ROOT=$PWD/eng/fixtures/archive python3 -m packages.catalog_api health

# Research still uses Mode A tools
python3 scripts/scaffold_session.py --ticker META --date $(date +%F) --orchestrator-model grok-4.5
python3 scripts/check_session.py --ticker META --date 2026-08-03 --full
```

## Concurrency (Mode A write ‖ Mode B read)

1. Mode B always opens sqlite **readonly**.  
2. Writers (finalize/export) use WAL + busy_timeout (see `compare_db.connect`).  
3. Thin JSON indexes (`runs_index.json`, `tickers_index.json`) are written **atomically** (temp + `os.replace`).  
4. `finalize_session` **patches** one run into indexes by default (not full disk scan). Use `--full-catalog-rebuild` for recovery.  
5. Never run `export_compare_db --all --rebuild` under a hot UI without staging.  
6. Mode B must **not** call export with snapshot refresh on live `archive/research`.

```bash
# Default finalize (sqlite upsert + catalog patch)
python3 scripts/finalize_session.py --ticker META --date 2026-08-03

# Full catalog rebuild (archive-only)
python3 scripts/rebuild_catalog.py --archive-only
python3 scripts/finalize_session.py --ticker META --date 2026-08-03 --full-catalog-rebuild

# Calibration
python3 -m packages.catalog_api calibration --horizon 1m
```

## Fixture refresh

```bash
# Optional: slim copy + re-export (does not mutate live research meta if --no-refresh-snapshot)
python3 scripts/sync_eng_fixtures.py --tickers META,JPM --dates 2026-08-03,2026-07-25
```

## Git (Mode B)

- **No commit without user agreement** — propose message, wait for “commit” / “yes commit that”.  
- After agreement + green verify: descriptive subject (what + why).  
- W1 runtime changes: include `harness/VERSION` bump in that change set.  
- Full rules: `eng/AGENTS.md` → **Git discipline**.

## Mode A version (W1)

```bash
# Read current intentional version
python3 -c "from packages.kd_research.provenance import load_harness_identity; print(load_harness_identity())"

# After changing research runtime: edit harness/VERSION harness_version (semver),
# then eng_verify must see harness/VERSION in the same change set as runtime paths.
python3 scripts/eng_verify.py
```

Every Mode A finalize stamps `harness_version` + `harness_git_sha` into
`meta/run_manifest.json` and `meta/prediction_snapshot.json` provenance.

## Failure → harness

Record systemic fails in `eng/eval/failure_catalog.md` and open an eng session issue.
