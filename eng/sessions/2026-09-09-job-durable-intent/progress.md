# Eng session 2026-09-09-job-durable-intent

- Created: 2026-09-09T09:04:33Z
- Work type: W2
- Goal: Durable Grok job intent: ensure+worker liveness, reconcile both planes, sqlite local home

## Log

- 2026-09-09T09:04:33Z scaffolded
- Implemented Option B (durable intent + worker handle):
  - `packages.agent_jobs.store` fsync job.json; `worker` liveness (`orchestrator_alive`, `session_busy`, `apply_liveness`, `record_spawn`)
  - `ensure_analyze` writes `starting` before scaffold; Start is idempotent for live/failed/cancelled
  - `reconcile_jobs` walks Analyze + Compare; FastAPI lifespan logs failures
  - `local_home` / `catalog_sqlite_path`: production catalog sqlite off OneDrive; tests keep `archive/catalog`
  - harness 2.41.0 + `pins/2.41.0/`
  - `ARCHITECTURE.md` updated
- Refactored: one job.json writer, one liveness rule for Analyze and Compare (was PID-death in two packages)
- `python scripts/eng_verify.py` PASS (971 tests)
- Feature `passes` left false (implementer ≠ verifier)
