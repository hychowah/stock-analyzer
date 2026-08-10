# Plan: Research Comparison Database (post-harness export)

**Status:** Phase A+B implemented (warehouse + provenance + experiment scaffold). Phase C partially (compare_experiment.py). D–E pending.  
**Date:** 2026-08-10  
**Goal:** After each research session finishes, export decision-grade results + provenance into a queryable SQLite DB so we can compare runs across **time**, **harness instruction changes**, **LLM model differences**, and **natural LLM variation** — and later power a UI.  
**Non-goal:** Do **not** move live research state into SQL. Full sessions under `archive/research/` remain the system of record.

---

## 1. Problem statement

| Layer | What it holds | Gap |
|-------|----------------|-----|
| `archive/research/<T>/<D>/` | Full immutable session | Too heavy to query / compare |
| `meta/prediction_snapshot.json` | Frozen claims per run | Was incomplete (probs/tech/provenance) |
| `archive/catalog/runs_index.json` | Thin path index | Not a comparison warehouse |
| `run_id = research:T:D` | One run per ticker×date | Needs slugs for same-day A/B (Phase B) |

### Comparison questions

1. **Time:** How did META FV / MoS / signal change across dates?
2. **Harness drift:** Same ticker + model, instruction/prompt hash changed — did FV band shift?
3. **Model delta:** Same harness + ticker, model A vs B — distribution of `fv_base`, MoS, bear weight?
4. **Natural variation:** Same knobs, N replicates — σ of fair value, verdict flips?
5. **Calibration (later):** MoS cohorts vs realized returns (outcomes join).

---

## 2. Design principles

1. **Disk is canonical; DB is a projection.** Rebuild anytime from `archive/research/**`.
2. **Export only after research completes** (Phase 5; PASS and FAIL both exportable).
3. **Provenance is first-class** (Phase B fills models/hashes; Phase A allows nulls).
4. **Stable metrics + `extras_json`** for schema evolution.
5. **No full filings / valuation trees in SQL** — pointers + summary numbers.

---

## 3. Architecture

```text
archive/research/<TICKER>/<SESSION_KEY>/   # system of record
        │ after Phase 5
        ▼
build_prediction_snapshot.py  → meta/prediction_snapshot.json
export_compare_db.py          → archive/catalog/research_compare.sqlite
rebuild_catalog.py            → thin JSON indexes (optional)
        │
        ▼
Future UI / notebooks / compare_experiment.py
```

**DB path:** `archive/catalog/research_compare.sqlite` (rebuildable; gitignored binary).

---

## 4. Identity model

### Production (today / Phase A)

```text
run_id = research:{TICKER}:{YYYY-MM-DD}
path   = archive/research/{TICKER}/{YYYY-MM-DD}/
```

### Experiments (Phase B)

```text
session_date = as-of date (YYYY-MM-DD)
session_key  = {session_date} | {session_date}__{run_slug}
run_id       = research:{TICKER}:{session_key}
```

Examples: `research:META:2026-08-03__model-grok45`, `...__exp-prompt-v3_r2`.

---

## 5. SQLite schema (v1)

See `scripts/kd_research/compare_db.py` (migrations embedded).

Tables:

- `schema_migrations`
- `experiments` — optional A/B grouping
- `runs` — one row per finished session (identity, provenance, market, valuation, tech)
- `run_metrics` — derived keys (`mos_vs_base`, `fv_range_pct`, …)
- `outcomes` — reserved for later calibration (empty in Phase A)

---

## 6. Commands

```bash
# After Phase 5
python3 scripts/build_prediction_snapshot.py --ticker T --date D
python3 scripts/export_compare_db.py --ticker T --date D
python3 scripts/rebuild_catalog.py

# Full rebuild from disk
python3 scripts/export_compare_db.py --all --rebuild
```

---

## 7. Implementation phases

| Phase | Status | Scope |
|-------|--------|--------|
| **A** | **done** | Schema, export, snapshot enrich, backfill, docs |
| **B** | **done** | Provenance capture, scaffold experiment flags, `session_key` paths, `finalize_session.py` |
| **C** | partial | `compare_experiment.py` + richer `runs_index` v2; more polish later |
| **D** | pending | Outcomes marks + calibration joins |
| **E** | pending | Read-only UI over SQLite |

---

## 8. Experiment protocol (for later bakeoffs)

1. Create `experiment_id` + written hypothesis.
2. Hold constant: ticker list, as-of date / price freeze, depth.
3. Vary **one** axis (model **or** prompts **or** harness commit).
4. ≥3 replicates if measuring natural LLM noise.
5. Export all; prefer `audit_verdict = 'PASS'` for calibration stats.

---

## 9. Non-goals (v1)

- Agents writing SQL mid-phase
- Remote Postgres (portable SQL if needed later)
- Storing report markdown / SEC text in DB
- Rewriting past FV after the fact
