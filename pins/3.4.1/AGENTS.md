# Workspace router — Stock Research Platform

Auto-loaded entrypoint. **Keep this file short.** Deep law lives in nested files.

## Mode entry (mandatory)

| Mode | When to use | Normative law (read before acting) | Data |
|------|-------------|--------------------------------------|------|
| **A — Research** | Run equity research on a ticker (Phases 0–5) | **`harness/RESEARCH_AGENTS.md`** + `harness/HARNESS_MAP.md` + `harness/agent_prompts.md` | **Write** `archive/research/<TICKER>/<DATE>/` |
| **B — Build** | Features, UI, catalog API, harness code | **`eng/AGENTS.md`** + `eng/HARNESS_MAP.md` | Immutable `archive/research` + `archive/outcomes`; append `archive/library/`; code under `eng/`, `packages/`, `apps/`, `programs/` |

### Hard rules (both modes)

1. **`archive/` is the production data plane.** Sessions under `archive/research/` and marks under `archive/outcomes/` are immutable history — never rewrite completed runs to “fix” UI or tests.  
2. Mode B home is **`eng/`** (never top-level `build/` — gitignored).  
3. Mode B does **not** run research Phases 0–5 unless the user explicitly schedules a black-box research experiment.  
4. Mode A agents **must open `harness/RESEARCH_AGENTS.md`** for the full pipeline, justification contract, and quality gates before Phase 0. Do not invent methodology from this router alone.  
5. English only for normative keys, schemas, registry fields, and reports.  
6. **No git commit without user agreement** — agents must not `git commit` / push / amend until the user explicitly asks or approves in-chat. Details: `eng/AGENTS.md` Git discipline (Mode B); Mode A same bar for any harness commits. **This checkout:** `COMMIT.md`.  
7. **Keep `ARCHITECTURE.md` current** — human map of the system. Before every commit, if the change set made that map stale, update it in the same change set (`ARCHITECTURE.md` § Keeping this document current).

## Quick commands

```bash
# Mode A — research
python3 scripts/ingest_library.py --ticker META
python3 scripts/scaffold_session.py --ticker META --date $(date +%F) --orchestrator-model grok-4.5
python3 scripts/bind_library.py --ticker META --date $(date +%F)
python3 scripts/preflight_phase.py --ticker META --date $(date +%F) --phase 2_parallel
python3 scripts/check_session.py --ticker META --date $(date +%F) --full
python3 scripts/finalize_session.py --ticker META --date $(date +%F)

# Mode B — product eng
python3 scripts/scaffold_eng_session.py --slug my-feature
python3 scripts/eng_verify.py
python3 -m packages.catalog_api health
python3 -m apps.analysis_web          # http://127.0.0.1:8765/  (Analyze + Compare)
python3 -m packages.research_jobs start --ticker COHR   # UI-scheduled Mode A (also /analyze/new)
```

## Where truth lives

| Need | Path |
|------|------|
| **Human architecture map** | `ARCHITECTURE.md` (keep current on every architecture-changing commit) |
| **Mode A full law** | `harness/RESEARCH_AGENTS.md` |
| Phase map / preflight table | `harness/HARNESS_MAP.md` |
| Subagent prompts | `harness/agent_prompts.md` |
| Orchestrator checklist | `harness/orchestrator_runbook.md` |
| Schemas | `harness/schemas/*.schema.json` |
| Sector / region modules (advisory) | `harness/modules/sector_*.md`, `harness/modules/region_*.md` |
| Valuation router (advisory, ≥ 3.0.0) | `harness/modules/valuation_router.md`, `valuation_checks.md` |
| **Mode B law** | `eng/AGENTS.md` |
| Catalog read API | `packages/catalog_api/` |
| Analysis UI | `apps/analysis_web/` |
| Live research records | `archive/research/`, `archive/catalog/`, `archive/outcomes/` |
| Ticker document library | `archive/library/` (filings/transcripts; not judgments) — `harness/library.md` |
| Offline CI fixtures | `eng/fixtures/archive/` (same shape as `archive/`) |
| Industry harness research pack | `harness/research/` (advisory) |

## Mode A one-line pipeline

Scaffold **new** `S` → listing stamp + `verify_listing` → `bind_library.py` (before `sector_config`) → classify KPI + `market_context` + `classification.json` → `research_brief` → Phase 0 ∥ 1_parallel → **preflight** 1b/1c when files exist (not after 2c); 1d after 0+1b; 1e story+3P after 0+1b+1c+1d; Agent 4/12 skip 1d/1e; Agent 5 after 1e lock; 2.5 / 4 / 5 as graph → audit → `finalize_session` (copies scaffold stamps).  
**Do not** browse prior `archive/research/<T>/` sessions before a new run (isolation). Resume only if the user names that folder.  
Details: **`harness/RESEARCH_AGENTS.md`**.

## Mode B one-line loop

Scaffold eng session → baseline `eng_verify` → implement one feature → verify → keep `ARCHITECTURE.md` true → ship note → **ask user** → commit only if agreed (`eng/AGENTS.md` Git discipline).  
Default data root: `ARCHIVE_ROOT=<project>/archive`.  
Details: **`eng/AGENTS.md`**.

## Do not

- Dump this router into a research mega-prompt and skip `RESEARCH_AGENTS.md`.  
- Put product UI state under `archive/research/`.  
- Invent fair values in Mode B — read catalog/snapshots only.  
- Use multi-agent fan-out for tightly sequential valuation writes (Mode A Agent 5 stays single-writer).  
- **Mode A new run:** open yesterday’s session “to see if it’s usable” before scaffolding — forbidden under isolation.  
- **`git commit` without the user saying so** — forbidden in both modes.  
- Ship a commit that leaves `ARCHITECTURE.md` describing the old system.
