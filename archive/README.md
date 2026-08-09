# Research Archive

All equity research **records** live under this tree. Harness code stays at the repo root.

## Layout

```text
archive/
├── catalog/
│   ├── runs_index.json       # every research run (rebuildable)
│   ├── tickers_index.json    # per-ticker latest + history
│   └── migration_log.jsonl   # session moves from legacy root paths
├── research/
│   └── <TICKER>/<YYYY-MM-DD>/   # immutable full session (same internals as harness v2)
│       ├── reports/
│       ├── data/
│       ├── charts/
│       ├── registry/
│       └── meta/
│           ├── run_manifest.json
│           └── prediction_snapshot.json   # frozen claims for lookback
└── outcomes/                 # optional; append-only grading (does not edit research)
    └── <TICKER>/<YYYY-MM-DD>/
```

## Rules

1. **Never overwrite** a completed research session. New analysis → new date folder.
2. **Canonical path:** `archive/research/<TICKER>/<DATE>/`.
3. **Indexes are caches** — rebuild with `python3 scripts/rebuild_catalog.py`.
4. **Outcomes** record whether past calls were right; they never rewrite valuation JSON.
5. Design plan: `harness/plan_research_archive_layout.md`.
6. **Not in git:** `archive/research/` and `archive/outcomes/` are local data only (listed in root `.gitignore`). Session trees are large (raw filings, prices, charts). Keep them on disk for the harness; commit harness code + `archive/catalog/` indexes, not full sessions.

## Common commands

```bash
# New session
python3 scripts/scaffold_session.py --ticker META --date $(date +%F)

# After Phase 5
python3 scripts/build_prediction_snapshot.py --ticker META --date 2026-08-03
python3 scripts/rebuild_catalog.py

# Resolve / check (archive first, legacy fallback)
python3 scripts/check_session.py --ticker META --date 2026-08-03 --full

# Compare two runs
python3 scripts/compare_runs.py --ticker META --dates 2026-07-30,2026-08-03
```
