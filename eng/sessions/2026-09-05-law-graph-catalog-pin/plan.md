# 2.38.0 — graph, RunQuery, thin pin

Design review of remaining C2–C5: four real homes (DAG, `RunQuery`, HTTP keys = `RunQuery`, Pin as a Mode A root). Direction is sound. The original sequence published a fat `pins/2.38.0` in C2, then changed `COPY_REL` in C5 after `force=` is gone — that cannot freeze the from-scratch pin. C2 as “derive six tables, keep the linear walk” would leave today’s gates in place.

This plan absorbs the load-bearing review items. It does **not** split C5.

## Constraints

- Mode B only. No research Phases 0–5.
- Do not rewrite `archive/research`, `archive/outcomes`, or `pins/2.27.0`–`2.37.0`.
- One slice per commit. `/smart-commit` after that slice’s verify is green. Do not push.
- Out of scope: retire `gates.py`, specialist rename, generate `HARNESS_MAP.md`, `consumptions[]` reshape, domain-out-of-scripts, mega CLI, CatalogApi class split, containment, Analyze/Compare merge, `parse_semver` home.

## Sequence (why this order)

`eng_verify` requires `pins/<live VERSION>/` in the same W1 change set as a `harness/VERSION` bump. Publish is one-shot once `force=` is deleted. `packages/harness_pin/` is not a Mode A runtime path, so C5 does not bump VERSION.

1. **C5** — Pin is a Mode A root (`COPY_REL`, resolve, scaffold, identity, no `force=`). VERSION stays 2.37.0; `pins/2.37.0` stays fat.
2. **C2** — Graph is the gate. VERSION → 2.38.0. Publish **once**: thin `pins/2.38.0` with the graph inside.
3. **C3** — Catalog `RunQuery` + listing columns. No VERSION.
4. **C4** — UI returns/passes `RunQuery`. No VERSION.

Do not publish a fat 2.38.0 and plan to replace it.

## C5 — Pin runtime (W5, no VERSION)

`packages/harness_pin/pin.py`:

- `COPY_REL` = Mode A only: `AGENTS.md`, `harness/`, `packages/__init__.py` + `packages/kd_research/`, Mode A scripts (`scaffold_session`, `preflight_phase`, `check_session`, `finalize_session`, `bind_library`, `ingest_library`, `harvest_library`, `verify_listing`, `verify_ticker`, `abandon_session`, `record_spawn`, `build_prediction_snapshot`, `export_compare_db`, `rebuild_catalog`, `requirements-research.txt`).
- Not copied: `catalog_api` / `research_jobs` / `compare_jobs` / `agent_jobs` / `harness_pin`, eng scripts (`eng_verify`, `scaffold_eng_session`, `publish_harness_release`, `sync_eng_fixtures`, `migrate*`), `**/tests`.
- `resolve`: live vs semver. Published requires `PIN.json`.
- `scaffold_research` branches on `version == live`; **both** paths run `scripts/scaffold_session.py` (drop in-process `scaffold` import).
- `identity()`: live uses provenance; published uses VERSION + `PIN.json` copy stamp (do not git-probe a published folder).
- Delete `force=` from `publish`.

Verify: `pytest packages/harness_pin/tests packages/research_jobs/tests -q` then `python scripts/eng_verify.py`.

Do **not** publish 2.38.0 in this slice.

## C2 — Phase graph (W1, VERSION → 2.38.0)

Encode the DAG once in `packages/kd_research/phase_graph.py` as `PhaseNode` objects (priors, subagents, spawn_ids, entry_required/optional, complete_paths, primary_artifacts, display_writes, entry/complete preflight).

Live edges:

```
orch → 0
orch → 1_parallel
1_parallel → 1b
1_parallel → 1c
0 + 1b + 1c → 1d
1d → 2_parallel
2_parallel → 2_5
2_5 → 3
2_5 → 4_parallel
3 + 4_parallel → 5
5 → done
```

Overlays (not new tables): `<2.30` add `0` as prior of `1_parallel`; `<2.6` omit `1d`. `PATH_EXTRAS` / `check_catalog` stay the when-tag dispatcher. `gates.py` stays the evidence runner.

**Edges are the gate.** After overlays, `PhaseNode.priors` is what `prerequisites_for`, `check_phase_graph_entry`, `check_phase_status_order_integrity`, and `current_phase_lag` consult. Stop `PHASE_ORDER` index walks and the `1_parallel` special case. Move `designed_phase_ids` onto the graph (`operating_path` re-exports).

Today’s linear walk is wrong on the live DAG: `1_parallel` complete while `0` is pending is legal on ≥2.30 but fails order-integrity; `3` ∥ `4_parallel` after `2_5` is legal but `4_parallel` complete while `3` is pending fails. C2 is not done if derived tables still use that walk.

Derive `PHASE_AGENTS`, `PHASE_ENTRY_*`, `PHASE_REQUIRED_SPAWNS`, `SPECIALIST_ARTIFACTS`, `DISPLAY_WRITES` from the graph (keep import aliases). `5b` is an annotation (orchestrator reopens `decision.json` after `2_5`, do not spawn agent 5), not a phase_status enum.

Point `harness/design_phase_status_and_exemplars.md` at `phase_graph.py`; kill “design only, not yet wired”. Point `phase_status.schema.json` at the graph module.

Tests in `test_phase_graph.py`:

- `1d` fails if `0` pending
- `1_parallel` on ≥2.30 does not wait on `0`; on 2.29 it does
- `1_parallel` complete while `0` pending is legal on ≥2.30 and illegal on 2.29
- `3` ∥ `4_parallel` after `2_5` does not fail integrity
- graph ids == schema enum == skeleton
- spawn ⊆ subagents
- `5b` is not a phase id

Then `pytest` the listed kd_research tests, `python scripts/eng_verify.py`, and **publish `pins/2.38.0` once** (thin allowlist from C5).

## C3 — Catalog RunQuery (W2, no VERSION)

- `RunQuery`: filters + sort/dir/limit/offset + `comparable_only` default **False**.
- `list_runs(q)` / `count_runs(q)`; kwargs facade for one cycle.
- At export/rebuild, stamp from the session tree **once**:
  - `quote_symbol` from `run_manifest` only (no ticker fallback; null if unstamped)
  - `quote_listing` / `quote_listing_source`: stamp → snapshot → ticker
- `list`/`get` read sqlite columns. Delete `_attach_quote_symbol`. Drop v1/v2 `SELECT` fallbacks. Missing schema → error pointing at `rebuild_catalog`.
- Schema bump for the listing columns (catalog is rebuildable).
- `programs/experiment_summary.py`: `comparable_only=False` and page with `count_runs`.
- CLI `--comparable-only`.
- Portfolio/compare pickers already pass `comparable_only=True` — leave them.

Verify: `pytest packages/catalog_api/tests -q` then `eng_verify`. Rebuild the live catalog after the schema bump so the UI slice is not reading a missing column.

## C4 — UI RunQuery (W4, no VERSION)

- `runs_list_q` returns `RunQuery` (same field names as the catalog, including `audit_verdict` and `comparable_only`).
- One key tuple feeds FastAPI, hrefs, and `runs.js`. Delete the `audit` alias and `catalog_filters`.
- Pages/API call `list_runs(q)` / `count_runs(q)`.
- Comparable is an explicit flag (runs list default False; compare picker `True`).
- Browser-verify: runs list, `/api/runs` keys, compare picker still FV-only, empty/invalid sort, desktop + narrow viewport.

Verify: `pytest apps/analysis_web/tests -q` plus browser.

## Later (not this session)

Retire `gates.py` as a table home (runner stays). Specialist rename. Generated `HARNESS_MAP.md`. Drop the `list_runs` kwargs facade after one cycle.
