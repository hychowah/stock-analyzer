# Orchestrator runbook (checklist)

**Role:** supervisor, classifier, merger, resume owner.  
**Anti-role:** not the valuation author; do not invent missing filings; do not contaminate Agent 4 with fundamentals (earnings **date only**).

Use with `AGENTS.md` §8 and `harness/agent_prompts.md`. Keep this file short — details stay in prompts/schemas.

---

## Before Phase 0

1. Scaffold: `python3 scripts/scaffold_session.py --ticker T --date D`
2. Write `registry/sector_config.json` — `module_file` is a **string** (never JSON `null`; use `""` only if documented).
3. Write `registry/market_context.json` (intensity gate is load-bearing).
4. Write `registry/research_brief.json` (new sessions) before Phase 0.

## Every agent return

5. Update `registry/phase_status.json` **before** next spawn: `status`, `artifacts[]`, `handoff` path; re-check paths on disk.
6. Subagent spawn must include: conventions header + agent body + runtime injection (`TICKER`, `DATE`, `ROOT`, `S`, peers, benchmarks, currency, intensity, research_depth, earnings_date for Agent 4, exemplar paths, `agent_id`).

## Before Phase 2 parallel (4 ∥ 5 ∥ 12)

7. Preflight: `python3 scripts/preflight_phase.py --ticker T --date D --phase 2_parallel` — FAIL → fix upstream.
8. **Freeze once:** write `data/price_snapshot.json` (price-only):

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

9. Confirm `registry/filing_deep_dive.json` on disk before Agent 5 (preflight already requires it).

## Merges (Phase 0 / 2.5)

10. Persist each raw return under `registry/raw/` **before** merge.
11. Merge for coverage; spot-check ≥3 headline numbers; never invent merge numbers.
12. `risk_bridge.scenario_probabilities`: **only** `bear` / `base` / `bull` floats (sibling key for rationale/`_note`).

## Before Phase 4 / 5

13. Preflight `4_parallel` / `5` as in `HARNESS_MAP.md`.
14. After audit PASS: set phase 5 complete, README audit line, `check_session.py --full`. Do not leave Phase 4 agents `pending` when reports exist.
15. **Never** ask Agent 13 to author missing FDD as a substitute for re-running 2e + 5.
16. **Finalize for lookback / comparison DB** (required for new sessions):

```bash
python3 scripts/finalize_session.py --ticker T --date D
# equivalent:
# python3 scripts/build_prediction_snapshot.py --ticker T --date D
# python3 scripts/export_compare_db.py --ticker T --date D
# python3 scripts/rebuild_catalog.py
```

    Disk session stays canonical; SQLite is a rebuildable projection for cross-run comparison and future UI (`harness/plan_research_compare_db.md`).

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

---

## Pointers

| Need | Where |
|------|--------|
| Phase graph | `harness/HARNESS_MAP.md` |
| Subagent templates | `harness/agent_prompts.md` |
| Valuation decision quality | `harness/exemplars/valuation_decision_quality.md` |
| Machine gates | `scripts/check_session.py --full`, `scripts/kd_research/gates.py` |
