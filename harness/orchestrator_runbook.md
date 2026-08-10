# Orchestrator runbook (checklist)

**Role:** supervisor, classifier, merger, resume owner.  
**Anti-role:** not the valuation author; do not invent missing filings; do not contaminate Agent 4 with fundamentals (earnings **date only**).

Use with `harness/RESEARCH_AGENTS.md` §8 and `harness/agent_prompts.md`. Root `AGENTS.md` is only the dual-mode router. Keep this file short — details stay in prompts/schemas.

---

## New run vs resume (read first)

| User intent | Do this | Do **not** |
|-------------|---------|------------|
| **New research** on T (default) | Scaffold new `S` for as-of date; work only under `S` | List/open `archive/research/T/*` “to see if yesterday is usable” |
| **Resume** an existing folder | Open that `session_key` only; continue `phase_status` | Start a parallel new tree unless asked |
| **Compare** to prior | After finalize of **this** run, if user asked | Pre-load prior FV/thesis into Phase 0–5 |

**Anti-pattern (forbidden):** “There’s a SOFI session from yesterday — checking if complete before starting.” That anchors the run. Scaffold today and proceed.

## Before Phase 0 (new run)

1. Scaffold: `python3 scripts/scaffold_session.py --ticker T --date D`  
   - Note printed `session_key` (may be `D__r2` if same-day re-run).  
   - Confirm `registry/session_isolation.json` exists (`mode=isolated` default).  
   - Set working `S` = that path only. **Skip** browsing other session keys.
2. Write `registry/sector_config.json` — `module_file` is a **string** (never JSON `null`; use `""` only if documented). Use as-of **date** in JSON (`YYYY-MM-DD`), not necessarily the full session_key.
3. Write `registry/market_context.json` (intensity gate is load-bearing).
4. Write `registry/research_brief.json` (new sessions) before Phase 0.
5. **Do not** open prior session folders (valuation, reports, handoffs, snapshots) for any phase inputs. Intra-session sharing only under current `S`.

## Every agent return

6. Update `registry/phase_status.json` **before** next spawn: `status`, `artifacts[]`, `handoff` path; re-check paths on disk **under current `S` only**. Never mark phase `complete` if primary artifacts or required handoffs are missing (`check_session` FAILs complete-without-artifact).
7. Prefer specialist **subagents** with isolated prompts for parallel gather (Phase 0, 2a∥2b∥2c, 4∥5∥12, stress, reports). Quality is enforced via **artifacts** (hooks, Agent 4 purity, handoffs), not spawn API proof. If you work inline, still write the same paths + handoffs (`orchestrator_inline` is allowed; hollow shells are not).
8. Subagent spawn must include: conventions header + agent body + runtime injection (`TICKER`, `DATE`, `ROOT`, `S`, peers, benchmarks, currency, intensity, research_depth, earnings_date for Agent 4, exemplar paths, `agent_id`).

## Before Phase 2 parallel (4 ∥ 5 ∥ 12)

9. Preflight: `python3 scripts/preflight_phase.py --ticker T --date D --phase 2_parallel` — FAIL → fix upstream.
10. **Freeze once:** write `data/price_snapshot.json` (price-only):

```json
{
  "ticker": "T",
  "as_of": "YYYY-MM-DD",
  "close": 0.0,
  "currency": "USD",
  "source": "yfinance|ir|..."
}
```

   - **No** FV, MoS, WACC, peers fundamentals, or CoC in this file.  
   - Inject path into Agent 4 / 5 / 12 prompts.  
   - Do **not** re-freeze mid-Phase 2. Agents use `close` for “current price” / MoS; history series still from `prices_*.csv`.

11. Confirm `registry/filing_deep_dive.json` on disk before Agent 5 (preflight already requires it). After Agent 5: valuation must have non-empty `filing_deep_dive_hooks` before Phase 2.5 (`preflight --phase 2_5` / `2_parallel --mode complete`).

## Merges (Phase 0 / 2.5)

12. Persist each raw return under `registry/raw/` **before** merge.
13. Merge for coverage; spot-check ≥3 headline numbers; never invent merge numbers. Write swarm lead handoffs (`phase0_*.md`, `phase25_*.md`).
14. `risk_bridge.scenario_probabilities`: **only** `bear` / `base` / `bull` floats (sibling key for rationale/`_note`).
15. Before flipping Phase 0 / 1_parallel / 1c / 2_parallel / 2.5 complete: `preflight_phase.py --mode complete` for that phase.

## Before Phase 4 / 5

16. Preflight `4_parallel` / `5` as in `HARNESS_MAP.md`.
17. After audit PASS: set phase 5 complete, README audit line, `check_session.py --full`. Do not leave Phase 4 agents `pending` when reports exist.
18. **Never** ask Agent 13 to author missing FDD as a substitute for re-running 2e + 5.
19. **Finalize for lookback / comparison DB** (required for new sessions):

```bash
python3 scripts/finalize_session.py --ticker T --date D
# equivalent:
# python3 scripts/build_prediction_snapshot.py --ticker T --date D
# python3 scripts/export_compare_db.py --ticker T --date D
# python3 scripts/rebuild_catalog.py
```

    Disk session stays canonical; SQLite is a rebuildable projection for cross-run comparison and future UI (`harness/plan_research_compare_db.md`).
    Finalize refreshes `harness_version` (from `harness/VERSION`) + `harness_git_sha` / dirty into manifest + snapshot provenance — confirm printed in CLI output.
    Prefer finalize on a **clean git tree** when practical (dirty flag otherwise). Optional post-finalize: commit the finished session so the run is recoverable from git history; do not rewrite prior completed sessions.
    Pass full `session_key` to finalize when folder is `date__rN` (e.g. `--date 2026-08-10__r2`).
    Optional **compare-after** prior run: only after finalize; write a separate note — never edit this session’s valuation.

---

## Controlled experiments (model / harness / natural variation)

Use a **slug** so same-day runs never overwrite production folders.

```bash
# Production (default)
python3 scripts/scaffold_session.py --ticker META --date 2026-08-10

# Bakeoff cell: one model × one replicate
python3 scripts/scaffold_session.py --ticker META --date 2026-08-10 \
  --experiment exp-model-bakeoff --slug model-grok45-r1 --replicate 1 \
  --orchestrator-model grok-4.5 --subagent-model grok-4.5 \
  --notes "vary model only; freeze price_snapshot from production if needed"

# After Phase 5 for that folder (session_key = date__slug)
python3 scripts/finalize_session.py --ticker META --date 2026-08-10__model-grok45-r1

# Summarize experiment cells
python3 scripts/compare_experiment.py --experiment exp-model-bakeoff --group-by orchestrator_model
```

Protocol: hold ticker + as-of date + price freeze constant; vary **one** axis; ≥3 replicates for natural LLM noise. Prefer `audit_verdict=PASS` for calibration stats. See `harness/plan_research_compare_db.md`.

### Outcomes grading (separate from research)

Do **not** edit research folders. After enough calendar time has passed:

```bash
yfinance-market-mcp/.venv/bin/python scripts/fetch_outcome_marks.py --ticker T --date D
# or batch:
yfinance-market-mcp/.venv/bin/python scripts/fetch_outcome_marks.py --all --horizons 1d,1w,1m
python3 scripts/compare_experiment.py --calibration --horizon 1m --pass-only
```

Writes `archive/outcomes/<T>/<session_key>/{price_path,scorecard}.json` and upserts the compare DB `outcomes` table.

---

## Pointers

| Need | Where |
|------|--------|
| Phase graph | `harness/HARNESS_MAP.md` |
| Subagent templates | `harness/agent_prompts.md` |
| Valuation decision quality | `harness/exemplars/valuation_decision_quality.md` |
| Machine gates | `scripts/check_session.py --full`, `scripts/kd_research/gates.py` |
