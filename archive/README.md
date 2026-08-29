# Research Archive

All equity research **records** live under this tree. Harness code stays at the repo root.

## Layout

```text
archive/
├── library/<TICKER>/         # reusable filings/transcripts (see harness/library.md)
├── comparisons/<TICKER>/<packet>/  # session-valuation-audit packets (append-only)
├── research_jobs/<TICKER>/<SESSION_KEY>/  # Analyze control plane (job.json; not a catalog source)
├── catalog/
│   ├── runs_index.json           # thin path index (rebuildable)
│   ├── tickers_index.json        # per-ticker latest + history
│   ├── research_compare.sqlite   # comparison warehouse (rebuildable; gitignored)
│   └── migration_log.jsonl       # session moves from legacy root paths
├── research/
│   └── <TICKER>/<SESSION_KEY>/  # YYYY-MM-DD or YYYY-MM-DD__rN / __slug
│       ├── reports/
│       ├── data/
│       ├── charts/
│       ├── registry/
│       └── meta/
│           ├── run_manifest.json
│           └── prediction_snapshot.json   # frozen claims for lookback + DB export
└── outcomes/                 # optional; append-only grading (does not edit research)
    └── <TICKER>/<YYYY-MM-DD>/
```

## Rules

1. **Never overwrite** a completed research session. New analysis → new date folder.
2. **Canonical path:** `archive/research/<TICKER>/<SESSION_KEY>/` (`SESSION_KEY` = as-of date or `date__rN` / named slug). Same-day re-runs auto-allocate `__r2`, `__r3`, ….
3. **Disk is system of record.** JSON indexes + SQLite are rebuildable projections — never the only copy of numbers.
4. **Indexes are caches** — rebuild with `python3 scripts/rebuild_catalog.py`.
5. **Comparison DB** — after Phase 5, export with `python3 scripts/export_compare_db.py` (see below). Plan: `harness/plan_research_compare_db.md`.
6. **Outcomes** record whether past calls were right; they never rewrite valuation JSON.
7. Design plan (layout): `harness/plan_research_archive_layout.md`.
8. **Not in git:** `archive/research/`, `archive/outcomes/`, `archive/comparisons/`, `archive/research_jobs/`, and `*.sqlite` under catalog. Session trees are large. Commit harness code + thin catalog JSON, not full sessions, compare packets, Analyze job control, or the SQLite binary.
9. **Compares** are post-finalize audits of two named sessions. They never rewrite research folders. UI: `/compares`. CLI: `python -m packages.compare_jobs`.
10. **Analyze jobs** (`archive/research_jobs/`) are Mode B control plane (PID, prompt, status). Not rebuildable from sessions; not a catalog source; backup = disk next to archive. Grok writes `archive/research/`; FastAPI does not author FV. CLI: `python -m packages.research_jobs`.

## Common commands

```bash
# Document library (drop PDFs in archive/library/META/_inbox/ first)
python3 scripts/ingest_library.py --ticker META
python3 scripts/bind_library.py --ticker META --date $(date +%F)  # in-progress session only; refuses finalized runs

# New session (orchestrator-model required — stamped at scaffold)
python3 scripts/scaffold_session.py --ticker META --date $(date +%F) --orchestrator-model grok-4.5

# After Phase 5 (snapshot + comparison DB + thin catalog)
python3 scripts/finalize_session.py --ticker META --date 2026-08-03

# Rebuild comparison warehouse from all sessions
python3 scripts/export_compare_db.py --all --rebuild

# Experiment / replicate scaffold (same calendar date, distinct folder)
python3 scripts/scaffold_session.py --ticker META --date 2026-08-10 \
  --experiment exp-model-bakeoff --slug model-a-r1 --replicate 1 \
  --orchestrator-model grok-4.5

# Summarize variation from the compare DB
python3 scripts/compare_experiment.py --experiment exp-model-bakeoff --group-by orchestrator_model

# Outcomes (realized marks — does not edit research sessions)
yfinance-market-mcp/.venv/bin/python scripts/fetch_outcome_marks.py --ticker META --date 2026-08-03
yfinance-market-mcp/.venv/bin/python scripts/fetch_outcome_marks.py --all --horizons 1d,1w,1m
python3 scripts/compare_experiment.py --calibration --horizon 1m --pass-only

# Resolve / check (archive first, legacy fallback)
python3 scripts/check_session.py --ticker META --date 2026-08-03 --full

# Compare two runs (file-based helper)
python3 scripts/compare_runs.py --ticker META --dates 2026-07-30,2026-08-03

# Query comparison DB (example)
sqlite3 archive/catalog/research_compare.sqlite \
  "SELECT ticker, session_date, asof_price, fv_base, fv_weighted, p_bear, p_base, p_bull, tech_signal, region FROM runs ORDER BY ticker, session_date;"
```
