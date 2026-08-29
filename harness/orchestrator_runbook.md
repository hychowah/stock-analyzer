# Orchestrator runbook (checklist)

**Role:** supervisor, classifier, merger, resume owner.  
**Anti-role:** not the valuation author; do not invent missing filings; do not contaminate Agent 4 with fundamentals (earnings **date only**).

Use with `harness/RESEARCH_AGENTS.md` §8 and `harness/agent_prompts.md`. Root `AGENTS.md` is only the dual-mode router. Keep this file short — details stay in prompts/schemas.

---

## UI-scheduled runs (read this first)

Mode B Analyze already scaffolded this session. `S` is on disk. `meta/run_manifest.json` already has `orchestrator_model`.

- Do **not** run `scripts/verify_ticker.py` or `scripts/scaffold_session.py`. A same-day scaffold **auto-allocates `__r2`** and desyncs `archive/research_jobs/`. Session is **already scaffolded**.
- **First action:** confirm the Yahoo listing with tools (yfinance / Yahoo MCP). Stamp `S/meta/run_manifest.json` `quote_symbol` (folder stays `TICKER`). Then `python3 scripts/verify_listing.py --ticker T --date <session_key>`. Non-zero → `scripts/abandon_session.py` then **STOP** before classification / Phase 0. Do not invent a company.
- Work only under `S`. Do not list `archive/research/<TICKER>/` except this `session_key`. Isolation file + `run_manifest.notes` repeat this.
- `archive/research_jobs/` is Mode B control; ignore it.
- `finalize_session.py --date` is the **full session_key** (`YYYY-MM-DD__r2` / slug), not the bare date if they differ.
- Do not git commit.
- All other runbook rules still apply: preflight, `bind_library.py` before 2b, `data/price_snapshot.json` freeze, Agent 5 including 5b, spawn-or-abandon, `check_session.py --full` before claiming done.

---

## New run vs resume (read first)

| User intent | Do this | Do **not** |
|-------------|---------|------------|
| **New research** on T (default) | Scaffold new `S` for as-of date; work only under `S` | List/open `archive/research/T/*` “to see if yesterday is usable” |
| **Resume** an existing folder | Open that `session_key` only; continue `phase_status` | Start a parallel new tree unless asked |
| **Compare** to prior | After finalize of **this** run, if user asked | Pre-load prior FV/thesis into Phase 0–5 |

**Anti-pattern (forbidden):** “There’s a SOFI session from yesterday — checking if complete before starting.” That anchors the run. Scaffold today and proceed.

## Before Phase 0 (new run)

0. **Ticker check (harness ≥ 2.21.0; listing via tools ≥ 2.26.0):** `python3 scripts/verify_ticker.py --ticker T`  
   - Live Yahoo quote **or** Yahoo search listings → continue to scaffold. Session ticker is what was typed.  
   - No quote and **no** search listings → STOP. Do not scaffold, do not invent a company.  
   - Do **not** remap the folder. After scaffold, **you** confirm the Yahoo listing with tools, stamp `quote_symbol`, and run `scripts/verify_listing.py`. Non-zero or not a real issuer → abandon and STOP before Phase 0.  
   - `scaffold_session.py` runs the existence check by default. `--skip-ticker-check` is tests/offline only.
1. Scaffold: `python3 scripts/scaffold_session.py --ticker T --date D --orchestrator-model <id>`  
   - **Required:** `--orchestrator-model` (e.g. `grok-4.5`) or env `RESEARCH_ORCHESTRATOR_MODEL`. Confirm CLI prints both model fields.  
   - Note printed `session_key` (may be `D__r2` if same-day re-run).  
   - Confirm `registry/session_isolation.json` exists (`mode=isolated` default).  
   - Confirm `meta/run_manifest.json` has non-null `orchestrator_model` **before Phase 0**. Never invent it later.  
   - Set working `S` = that path only. **Skip** browsing other session keys.
2. Classify sector from `harness/RESEARCH_AGENTS.md` **§5 first** (no scoring algorithm; modules do not classify). If you consult a `sector_*.md` detection list, it is diagnostic only. If `cyclical` is in play: name the sub-type or cousin, or show majority revenue **realized at** spot/index/posted producer prices; otherwise do not pick cyclical. Branded CPG / Consumer Defensive food with commodity-input or price-gap beta → `standard` (optional `is_also_growth`); seed protein/feed/HPAI in the brief, do not switch the lead module. Write `registry/sector_config.json` — `module_file` is a **string** (never JSON `null`; use `""` for standard). Use as-of **date** in JSON (`YYYY-MM-DD`), not necessarily the full session_key.
3. Write `registry/market_context.json` (intensity gate is load-bearing).
4. Write `registry/research_brief.json` (new sessions) before Phase 0. Material commodity-input / protein-supply beta on a standard name must appear in `must_cover_risks`.
5. **Do not** open prior session folders (valuation, reports, handoffs, snapshots) for any phase inputs. Intra-session sharing only under current `S`.
5b. **Document library (harness ≥ 2.19.0):** after the brief (may overlap Phase 0), run `python3 scripts/bind_library.py --ticker T --date D`. Bind **refuses** completed sessions (`prediction_snapshot` or finalized `run_manifest`) — never re-bind finished history. Preflight `1_parallel` FAILs without `registry/library_bind.json`. Spawn 2b with `session_missing` from bind/index. Read `harness/library.md` (you and 2b only). Do **not** run `harvest_library.py`. Do **not** inject the live library path or `library.md` into any subagent except 2b. Year-reader paths = `S/data/raw_sec/*.txt` only.

## Phase graph + subagents (mandatory)

| Role | Who | Rule |
|------|-----|------|
| **Orchestrator** | Lead (you) | Advances phases in order; only writer of `phase_status` |
| **Subagent** | Specialist (2a, 5, 13, swarms, …) | Belongs to **one** phase; spawn only after that phase’s preflight |

```bash
python3 scripts/preflight_phase.py --ticker T --date D --phase <phase_id>
python3 scripts/preflight_phase.py --ticker T --date D --phase 2_parallel --subagent 5
```

FAIL → fix upstream; do **not** spawn a subagent for the wrong phase (e.g. valuation subagent `5` before `2_parallel`). Parallel subagents **within** a phase may run together after preflight.

## Every subagent return

6. Update `registry/phase_status.json` **before** next spawn: `status`, `artifacts[]`, `handoff` path; re-check paths on disk **under current `S` only**. Never mark phase `complete` if primary artifacts or required handoffs are missing (`check_session` FAILs complete-without-artifact).
7. **MUST spawn specialists** (isolated prompts) for Phase 0 swarm (one spawn per `registry/raw/phase0_*.json`), 2a∥2b∥2c, 2d, each 1c year-reader, 2e, 1d workers+merge, 4∥5∥12, 2.5 swarm (one spawn per `stress_*.json`), 6, 7∥8∥11, 13. Ritual: `record_spawn.py --event launch` → `spawn_subagent` → `--event return` (return without launch FAILs). Set `phase_status.agents[].execution=subagent`. Retry spawn without recording fail if the tool glitched. **`--event fail` (or `abandon_session.py`) only when you cannot launch and would otherwise work inline — then STOP.** Do **not** write that specialist’s artifacts yourself. Inline specialist work is a FAIL (`orchestrator_inline` forbidden; do not retag Agent 5 as `orchestrator_lead` at 5b). Orchestrator-lead work only: classification, brief, bind_library, price_snapshot, phase_status, Phase 0/2.5 merge, 5b reopen.
8. Subagent spawn must include: conventions header + subagent body + runtime injection (`TICKER`, `YAHOO_QUOTE_SYMBOL` from `S/meta/run_manifest.json` `quote_symbol`, `DATE`, `ROOT`, `S`, peers, benchmarks, currency, intensity, research_depth, earnings_date for technical subagent 4, exemplar paths, subagent id). On-disk `phase_status.agents[].agent_id` stores the **subagent id**.

## Before Phase 2 parallel (subagents 4 ∥ 5 ∥ 12)

9. Preflight: `python3 scripts/preflight_phase.py --ticker T --date D --phase 2_parallel` (optionally `--subagent 5`) — FAIL → fix upstream.
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
   - Fetch the close via `meta/run_manifest.json` `quote_symbol` (Yahoo listing), not a hardcoded suffix map. Session ticker may differ (`ADYEN` vs `ADYEN.AS`).  
   - Inject path into Agent 4 / 5 / 12 prompts.  
   - Do **not** re-freeze mid-Phase 2. Agents use `close` for “current price” / MoS; history series still from `prices_*.csv`.

11. **Phase 1c (after 2b; may overlap 2d):** list annuals (`packages/kd_research/annuals.py`). Spawn **one year-reader per annual** (isolated prompt; cleaned `.txt` path only — do not paste the filing). After `registry/raw/fdd_year_*.json` exist, run excerpt-in-source (`excerpt_check.py`) — **do not** run `--mode complete` yet (that gate needs FDD + `verify_rechecks`). Then spawn **2e merger** only. Then `preflight --phase 1c --mode complete`. Confirm `registry/filing_deep_dive.json` (plus `verify_rechecks`) before Agent 5. After Agent 5: valuation must have non-empty `filing_deep_dive_hooks` before Phase 2.5 (`preflight --phase 2_5` / `2_parallel --mode complete`). Legacy sessions without year-files: FDD alone still completes 1c.

11b. **Phase 1d (after 1b+1c; new runtime ≥ 2.6.0):** spawn `1d_rev` ∥ `1d_ind` ∥ `1d_ol` (gather only). Persist `registry/raw/oppath_*.json`. Then spawn `1d_merge` only. `preflight --phase 1d --mode complete`. Confirm `registry/operating_path_brief.json` before Agent 5. Workers must not write FV or 8-year paths. Do not average flatten vs destock. Legacy sessions without 1d: skip.

## Merges (Phase 0 / 2.5)

12. Persist each raw return under `registry/raw/` **before** merge.
13. Merge for coverage; spot-check ≥3 headline numbers; never invent merge numbers. Write swarm lead handoffs (`phase0_*.md`, `phase25_*.md`).
14. `risk_bridge.scenario_probabilities`: **only** `bear` / `base` / `bull` floats (sibling key for rationale/`_note`).
15. Before flipping Phase 0 / 1_parallel / 1c / 1d / 2_parallel / 2.5 complete: `preflight_phase.py --mode complete` for that phase.
15b. **After Phase 2.5 is complete** (harness ≥ 2.14.0): run the Agent 5 **5b** block yourself (lead). Reopen `registry/decision.json` only — do not rewrite FV, do not spawn subagent `5` in `2_5`, do not mark `2_parallel` pending. Then preflight `4_parallel`.

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
    Prefer finalize on a **clean git tree** when practical (dirty flag otherwise). **Do not `git commit` unless the user explicitly agrees** in-chat. Optional post-finalize commit only after that agreement; do not rewrite prior completed sessions.
    Pass full `session_key` to finalize when folder is `date__rN` (e.g. `--date 2026-08-10__r2`).
    Optional **compare-after** prior run: only after finalize; write a separate note — never edit this session’s valuation.

---

## Controlled experiments (model / harness / natural variation)

Use a **slug** so same-day runs never overwrite production folders.

```bash
# Production (default) — orchestrator-model required
python3 scripts/scaffold_session.py --ticker META --date 2026-08-10 --orchestrator-model grok-4.5

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
vendor/mcp/yfinance-market-mcp/.venv/bin/python scripts/fetch_outcome_marks.py --ticker T --date D
# or batch:
vendor/mcp/yfinance-market-mcp/.venv/bin/python scripts/fetch_outcome_marks.py --all --horizons 1d,1w,1m
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
| Machine gates | `scripts/check_session.py --full`, `packages/kd_research/gates.py` |
