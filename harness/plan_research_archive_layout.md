# Plan: Research Archive Layout + Historical Track Record

**Status:** Phase A+B implemented (2026-08-09) — archive layout, migration, snapshots, catalog live. Phase C outcomes grading still pending.  
**Date:** 2026-08-09  
**Scope:** (1) move company research off workspace root; (2) treat every research run as an immutable historical record; (3) enable later comparison and “were we right?” calibration.  
**Out of scope for this plan:** portfolio management, live monitor, strategy simulation product code (only seams that those will need).  
**Aligned with:** `AGENTS.md` v2 harness, `harness/research/` pack (progressive disclosure, disk as system of record, MVH).

---

## 1. Goals and non-goals

### 1.1 Goals

| ID | Goal |
|----|------|
| G1 | **Clean root:** workspace root holds harness/code/tools only — not 20 ticker folders. |
| G2 | **Immutable archive:** every research session is a permanent, never-overwritten record under a single tree. |
| G3 | **Lookback / calibration:** can answer “what did we say on date D about T?” and “was FV/verdict directionally right over horizon H?” |
| G4 | **Cross-session comparison:** same ticker across dates; peers across a date; thesis drift over time. |
| G5 | **No quality regression:** same phase graph, schemas, audit, hermetic compute — only paths and indexes change. |
| G6 | **Migration safety:** existing sessions remain readable; dual-path support during transition. |

### 1.2 Non-goals (this plan)

- Building portfolio/monitor/sim products (only leave room for them later).
- Replacing the research agent graph or merging valuation into multi-agent valuers.
- Shared live market DB as a required dependency for research (optional later).
- Auto-trading or rewriting past fair values after the fact.

### 1.3 Design principles (from current harness + research pack)

1. **Runs are immutable; indexes are mutable.** Never edit a completed session’s registry/data to “fix history.” Add new sessions or a separate outcomes layer.
2. **Disk is system of record.** Chat is not memory; indexes only point into full sessions.
3. **Full session stays the deep archive.** Indexes hold *projections* for search/compare — not a second source of truth for numbers.
4. **Mechanical gates > prose.** Scaffold, check_session, and a new catalog checker enforce layout.
5. **Progressive disclosure.** Root `AGENTS.md` becomes a short map; path conventions live in this doc + small path helpers.

---

## 2. Current state (problem)

```text
/workspace-stock-research/
├── AAPL/2026-07-25/...
├── META/2026-07-30/...
├── META/2026-08-03/...
├── JPM/...
├── 000660.KS/...          # ~19 tickers at root, mixed with code
├── harness/
├── scripts/
├── templates/
├── sector_*.md
├── region_*.md
└── *-mcp/
```

**Pain:**

- Root is polluted; hard to see what is “product code” vs “user research data.”
- No global catalog of runs → hard to list all sessions or compare META Jul 30 vs Aug 3 without knowing paths.
- No frozen **prediction snapshot** optimized for later grading (FV, price-at-research, verdict live only inside deep JSON/reports).
- No **outcomes** layer to record realized prices / correctness grades without mutating the session.

**What already works (keep):**

- `<TICKER>/<YYYY-MM-DD>/` immutability and refuse-overwrite scaffold.
- Full session tree: `reports/`, `data/`, `charts/`, `registry/`.
- Hermetic compute + audit PASS gate.
- Multi-date precedent (e.g. META has two sessions).

---

## 3. Target layout

```text
/workspace-stock-research/                    # REPO / HARNESS ROOT
├── AGENTS.md                                 # short map (later shrink)
├── README.md
├── .mcp.json
│
├── harness/                                  # design, prompts, research pack, this plan
├── scripts/                                  # scaffold, check, migrate, catalog, outcomes
├── templates/                                # JSON schemas (+ new catalog/outcomes schemas)
├── sector_*.md / region_*.md                 # advisory modules (or later modules/)
├── sec-edgar-mcp/ web-fetch-mcp/ yfinance-...
├── _archive/                                 # retired v1 only
│
└── archive/                                  # <<< ALL RESEARCH RECORDS (user data)
    ├── README.md                             # human + agent: how to navigate archive
    ├── catalog/
    │   ├── runs_index.json                   # every run: path, ticker, dates, audit, pointers
    │   ├── tickers_index.json                # per-ticker: latest, all run_ids, pointers
    │   └── schema_version
    │
    ├── research/                             # immutable full sessions
    │   └── <TICKER>/
    │       └── <YYYY-MM-DD>/                 # same internal layout as today
    │           ├── reports/
    │           ├── data/
    │           ├── charts/
    │           ├── registry/
    │           └── meta/                     # NEW small run-level metadata (see §5)
    │               ├── run_manifest.json     # identity, paths, git/harness version if available
    │               └── prediction_snapshot.json  # frozen claims for later grading
    │
    └── outcomes/                             # mutable *add-only* correctness layer (see §6)
        └── <TICKER>/
            └── <YYYY-MM-DD>/                 # keys to the research run being graded
                ├── price_path.json           # realized prices at +1d/+1w/+1m/+3m/+6m/+1y (as available)
                ├── scorecard.json            # human/agent grades: direction, MoS, risk hits
                └── notes.md                  # freeform retrospective
```

### 3.1 Why `archive/` not `workspace/` or `products/research/`

| Option | Pros | Cons | Choice |
|--------|------|------|--------|
| `archive/research/` | Clear “historical record”; one word for lookback | Slightly longer paths | **Chosen** — matches user intent (record + future analysis) |
| `workspace/runs/research/` | Generic multi-product | “Workspace” is vague; less archival signal | Later if multi-product ships |
| Keep root tickers | Zero migration | Fails G1 | Reject |

Harness code stays at repo root. **Only research data moves under `archive/`.**

### 3.2 Session internal layout (unchanged)

```text
archive/research/<TICKER>/<YYYY-MM-DD>/
├── reports/     00_*_README.md, 01_*_fundamental.md, 02_*_technical.md
├── data/        sp_financials, prices_*, valuation_model.json, compute/, raw_sec/, ...
├── charts/
├── registry/    sector_config, market_context, ..., audit, phase_status, handoffs/, raw/
└── meta/        run_manifest.json, prediction_snapshot.json   # NEW
```

Agents keep writing the same relative paths under session root `S`. Only `S` changes from  
`ROOT/META/2026-08-03` → `ROOT/archive/research/META/2026-08-03`.

### 3.3 Root after migration (illustrative)

```text
AGENTS.md
README.md
harness/
scripts/
templates/
sector_*.md
region_*.md
*_mcp/
_archive/
archive/          # research records only
```

No `META/`, `JPM/`, etc. at root.

---

## 4. Identity model

### 4.1 Run ID

```text
run_id = "research:{TICKER}:{YYYY-MM-DD}"
# example: research:META:2026-08-03
```

- One calendar date per ticker is the unit of work (same as today).
- Same-day re-run: **forbidden by default** (scaffold refuse). Exception: `--force` only for broken empty scaffolds — never to replace a completed audit PASS session.
- If same-day redo is ever required after PASS: use `YYYY-MM-DD_r2` suffix (optional future); prefer next day.

### 4.2 Pointers

| Pointer | Meaning | Mutability |
|---------|---------|------------|
| `archive/research/T/D/` | Full session | Immutable after audit complete (policy) |
| `archive/catalog/runs_index.json` | All runs list | Updated on each new run / migrate |
| `archive/catalog/tickers_index.json` | Per ticker latest + history | Updated on each new run |
| `archive/outcomes/T/D/` | Realized grading for that run | Append/update outcomes only — never rewrite research session |

### 4.3 “Latest” semantics

`tickers_index.json` entry:

```json
{
  "ticker": "META",
  "latest_run_id": "research:META:2026-08-03",
  "latest_path": "archive/research/META/2026-08-03",
  "latest_audit": "PASS",
  "runs": [
    {"run_id": "research:META:2026-07-30", "path": "...", "session_date": "2026-07-30"},
    {"run_id": "research:META:2026-08-03", "path": "...", "session_date": "2026-08-03"}
  ]
}
```

“Latest” = max `session_date` with `audit == PASS` if any PASS exists; else max date (flag degraded). Document this rule in catalog README.

---

## 5. Run metadata (new, small, inside each session)

Written at **end of successful research** (Phase 5 after audit PASS; on FAIL still write snapshot with `audit: FAIL` for honesty).

### 5.1 `meta/run_manifest.json`

```json
{
  "schema_version": 1,
  "run_id": "research:META:2026-08-03",
  "product": "research",
  "ticker": "META",
  "session_date": "2026-08-03",
  "created_at": "2026-08-03T...Z",
  "completed_at": "2026-08-03T...Z",
  "harness_spec": "v2",
  "paths": {
    "session_root": "archive/research/META/2026-08-03",
    "reports": "reports/",
    "valuation": "data/valuation_model.json",
    "audit": "registry/audit.json",
    "readme": "reports/00_META_README.md"
  },
  "status": "complete",
  "audit_verdict": "PASS",
  "immutable": true
}
```

### 5.2 `meta/prediction_snapshot.json` (core of lookback)

**Purpose:** one file an outcomes grader can read without parsing entire valuation + reports.

Required fields (v1):

| Field | Source | Why |
|-------|--------|-----|
| `ticker`, `session_date`, `run_id` | session | join key |
| `asof_price` | technical / prices snapshot | price at research time |
| `currency` | valuation / market_context | units |
| `fair_value.base/bear/bull` | valuation_model | central prediction |
| `fair_value.probability_weighted` | valuation_model if present | optional |
| `margin_of_safety_pct` | valuation_model | signed MoS |
| `verdict_line` | README one-liner bull/base/bear | human label |
| `primary_sector`, `region`, `intensity` | sector + market_context | slice analysis |
| `key_risks[3]` | risk_bridge / README | did risks materialize? |
| `peers` | README required inputs | peer set used |
| `benchmark` | README / technical | relative performance |
| `data_quality` | README flags | degraded runs |
| `audit_verdict` | audit.json | quality filter for stats |
| `priced_for_perfection` | valuation if present | flag |
| `source_paths` | relative paths | rehydrate exact numbers |

**Rules:**

- Snapshot is a **projection** — canonical numbers remain in `data/valuation_model.json`.
- After `immutable: true`, **do not edit** snapshot (outcomes live under `archive/outcomes/`).
- Written by a small script `scripts/build_prediction_snapshot.py` (deterministic from session files) ± orchestrator after Phase 5 — prefer **script** so re-runs of snapshot builder from same session are hermetic.

---

## 6. Outcomes layer (were we right?)

Separate from research so history is not rewritten.

### 6.1 When to grade

| Horizon | Typical use |
|---------|-------------|
| +1 trading day | noise / event reaction |
| +1 week | short signal |
| +1 month | thesis still “fresh” |
| +3 months | primary calibration window |
| +6 months / +1 year | long thesis / FV realization |

Not every horizon is available immediately — grade **incrementally** as time passes.

### 6.2 `outcomes/.../price_path.json`

```json
{
  "run_id": "research:META:2026-08-03",
  "ticker": "META",
  "session_date": "2026-08-03",
  "asof_price": 520.0,
  "currency": "USD",
  "marks": [
    {
      "horizon": "1m",
      "asof": "2026-09-03",
      "price": 540.0,
      "total_return_pct": 3.85,
      "benchmark_return_pct": 1.2,
      "excess_return_pct": 2.65,
      "source": "yfinance_snapshot",
      "fetched_at": "2026-09-03T..."
    }
  ],
  "compute_script": "scripts/outcomes/fetch_marks.py"
}
```

### 6.3 `outcomes/.../scorecard.json`

Judgment grades (agent or human), each with justification contract:

```json
{
  "run_id": "research:META:2026-08-03",
  "graded_at": "2026-11-03",
  "horizon_primary": "3m",
  "metrics": {
    "direction_vs_price": {
      "value": "correct",
      "rule": "MoS>0 and 3m return>0 OR MoS<0 and 3m return<0 (simplified)",
      "rationale": "...",
      "basis": "price_path + prediction_snapshot"
    },
    "fv_band_hit": {
      "value": false,
      "detail": "price never entered [bear, bull] within 3m",
      "rationale": "...",
      "basis": "..."
    },
    "relative_to_benchmark": {
      "value": "outperformed",
      "excess_return_pct": 2.65,
      "rationale": "...",
      "basis": "..."
    }
  },
  "risk_materialization": [
    {"risk": "...", "status": "did_not_occur|occurred|partial", "notes": "..."}
  ],
  "overall_label": "mostly_right|mixed|mostly_wrong",
  "grader": "human|agent_outcomes_v1",
  "notes_path": "notes.md"
}
```

**Important:** Calibration metrics are **policy choices** (define in `templates/outcomes_scorecard.schema.json` + short methodology note). Do not hardcode “truth” into the research harness valuation agent. Outcomes is a **separate thin workflow** (mostly code + occasional LLM narrative).

### 6.4 Comparison queries (enabled by this design)

| Question | How |
|----------|-----|
| All runs for META | `tickers_index` → list paths |
| What changed Jul 30 → Aug 3? | Diff `prediction_snapshot.json` + optional report diff |
| Hit rate of MoS>10% names at 3m | Join catalog PASS runs ↔ outcomes scorecards |
| Sector bias (growth vs banking) | Group snapshots by `primary_sector` |
| Did audit FAIL runs do worse? | Slice by `audit_verdict` |
| Peer set consistency | Compare `peers` across runs |

---

## 7. Catalog (global index)

### 7.1 `archive/catalog/runs_index.json`

Array (or map by `run_id`) of compact rows:

```json
{
  "schema_version": 1,
  "updated_at": "2026-08-09T07:17:35Z",
  "runs": [
    {
      "run_id": "research:META:2026-08-03",
      "ticker": "META",
      "session_date": "2026-08-03",
      "path": "archive/research/META/2026-08-03",
      "audit_verdict": "PASS",
      "asof_price": 520.0,
      "fv_base": 610.0,
      "margin_of_safety_pct": 14.8,
      "primary_sector": "growth",
      "region": "us",
      "has_prediction_snapshot": true,
      "has_outcomes": false
    }
  ]
}
```

Rebuildable anytime from disk via `scripts/rebuild_catalog.py` (scan `archive/research/**/meta/` + fallbacks for pre-meta legacy).

### 7.2 Catalog rules

- Catalog is a **cache**; full session is authority.
- Rebuild must not invent numbers — only read snapshot/manifest/valuation.
- `check_catalog.py` verifies every index path exists and reverse: every session dir appears in index (after migration).

---

## 8. Path resolution (code changes)

### 8.1 New constants / helpers (`scripts/kd_research/paths.py`)

```python
ARCHIVE_ROOT = PROJECT_ROOT / "archive"
RESEARCH_ROOT = ARCHIVE_ROOT / "research"
CATALOG_ROOT = ARCHIVE_ROOT / "catalog"
OUTCOMES_ROOT = ARCHIVE_ROOT / "outcomes"

def session_root(ticker, session_date, output_dir=None) -> Path:
    # default: archive/research/<TICKER>/<DATE>
    ...

def resolve_session(ticker, session_date) -> Path:
    """Prefer archive path; fall back to legacy ROOT/TICKER/DATE if present."""
    ...
```

### 8.2 Scaffold

```bash
python3 scripts/scaffold_session.py --ticker META --date 2026-08-09
# creates archive/research/META/2026-08-09/{reports,data,...,meta,registry/...}
```

- Default `output_dir` → `archive/research` (via session_root).
- Still support `--output-dir` for tests.
- Create empty `meta/` in SUBDIRS.

### 8.3 check_session

- `--session-dir` already works — keep as primary for relocated paths.
- `--ticker/--date` resolve via `resolve_session` (archive first, legacy fallback).
- Optional: require `meta/prediction_snapshot.json` when `--full` and audit PASS (phase in after snapshot script exists).

### 8.4 Agent prompts / AGENTS.md

- Document: session root is `ROOT/archive/research/TICKER/DATE` (variable `S`).
- No need to rewrite every relative path inside agents (`S/registry/...` stays).
- Root AGENTS §2 session folder convention → update in same PR as path default change.

---

## 9. Migration plan (existing ~19 tickers)

### 9.1 Inventory (current)

Sessions live at `ROOT/<TICKER>/<DATE>/` (META has 2 dates). One-time inventory script lists all.

### 9.2 Steps (ordered)

| Step | Action | Risk |
|------|--------|------|
| M0 | Land path helpers + dual resolve (archive preferred, legacy fallback) — **no moves yet** | Low |
| M1 | Create `archive/{research,catalog,outcomes}/` + README | Low |
| M2 | Point scaffold default at `archive/research` | Low (new sessions only) |
| M3 | `scripts/migrate_sessions_to_archive.py`: move `TICKER/DATE` → `archive/research/TICKER/DATE` (git mv if repo tracked) | Medium |
| M4 | For each moved session: build `meta/prediction_snapshot.json` + `run_manifest.json` from existing files (best-effort; mark gaps) | Medium |
| M5 | `rebuild_catalog.py` → full indexes | Low |
| M6 | Update AGENTS.md + agent_prompts path examples | Low |
| M7 | Smoke: `check_session --full` on 2–3 moved sessions (JPM, META, one non-US) | — |
| M8 | Remove empty legacy ticker dirs; document in archive/README | Low |

### 9.3 Migration script guarantees

1. **Copy or `git mv` then verify**, never delete source until destination check_session core PASS (or filesize tree match).
2. Refuse migrate if destination non-empty.
3. Log every move to `archive/catalog/migration_log.jsonl`.
4. Dry-run flag default-on for first human review.

### 9.4 Compatibility window

- **≥1 release** of dual resolve so any in-flight agent with old path still finds legacy if move delayed.
- After M8, legacy path only if someone drops folders by hand (still resolved).

---

## 10. Lifecycle workflow (day-to-day)

### 10.1 New research run

```text
1. date=$(date +%F)   # never agent-invented
2. scaffold → archive/research/T/D/
3. Orchestrator: sector + market_context; Phases 0–5 as today
4. On complete: build_prediction_snapshot + run_manifest
5. rebuild_catalog (or incremental catalog_upsert)
6. Optional: symlink or note "latest" only in tickers_index (not a second copy of session)
```

### 10.2 Lookback / comparison (human or agent)

```text
1. Read archive/catalog/tickers_index.json for T
2. Open two prediction_snapshot.json files → structured diff
3. For deep dive, open full sessions (reports/registry)
4. Never mutate past sessions
```

### 10.3 Outcomes refresh (scheduled or on-demand later)

```text
1. Select runs older than horizon H with missing marks
2. fetch_marks.py → outcomes/T/D/price_path.json
3. Optional grade_scorecard.py or human notes
4. catalog flag has_outcomes=true
```

Outcomes automation is **Phase B** of this plan (after archive move is stable).

---

## 11. Implementation work breakdown

### Phase A — Layout + archive (do first)

| # | Deliverable | Owner type |
|---|-------------|------------|
| A1 | `paths.py`: RESEARCH_ROOT, resolve_session dual-path | code |
| A2 | `scaffold_session.py`: default under archive/research; create meta/ | code |
| A3 | `archive/README.md` conventions | docs |
| A4 | `migrate_sessions_to_archive.py` (dry-run + execute) | code |
| A5 | Migrate all existing sessions; migration log | ops |
| A6 | Update `AGENTS.md` §2 paths; agent_prompts `S` examples | docs |
| A7 | `check_session` resolve update; smoke tests | code + test |

**Exit criteria:** root has no ticker folders; all old sessions under `archive/research/`; check_session works with `--ticker/--date`.

### Phase B — Prediction snapshot + catalog

| # | Deliverable |
|---|-------------|
| B1 | `templates/prediction_snapshot.schema.json` |
| B2 | `templates/run_manifest.schema.json` |
| B3 | `scripts/build_prediction_snapshot.py` (read valuation, technical price, sector, audit, README flags) |
| B4 | Backfill snapshots for all archived sessions (degraded OK if price missing) |
| B5 | `scripts/rebuild_catalog.py` + `runs_index` / `tickers_index` schemas |
| B6 | Orchestrator note in AGENTS: after Phase 5 run snapshot + catalog upsert |
| B7 | `scripts/check_catalog.py` structural |

**Exit criteria:** every PASS session has snapshot; catalog lists all runs; can query latest META without globbing.

### Phase C — Outcomes / calibration (after A+B)

| # | Deliverable |
|---|-------------|
| C1 | `templates/outcomes_price_path.schema.json`, `outcomes_scorecard.schema.json` |
| C2 | `harness/outcomes_methodology.md` — define direction/FV-hit rules explicitly |
| C3 | `scripts/outcomes/fetch_marks.py` (hermetic: write snapshots of prices used) |
| C4 | `scripts/outcomes/grade_scorecard.py` (deterministic metrics first; LLM notes optional) |
| C5 | Example graded session + catalog `has_outcomes` |
| C6 | Simple report: `scripts/outcomes/summary_table.py` → markdown hit-rate by sector/horizon |

**Exit criteria:** can grade a 3m-old session and produce a portfolio-of-calls hit-rate table from archive only.

### Phase D — Comparison UX (light)

| # | Deliverable |
|---|-------------|
| D1 | `scripts/compare_runs.py --ticker META --dates 2026-07-30,2026-08-03` → snapshot diff |
| D2 | Optional agent prompt template: “retrospective analyst” reads snapshots + outcomes only first, then deep session if needed |
| D3 | Shrink root AGENTS.md to map + pointer to archive conventions (pack-aligned) |

---

## 12. Immutability policy (explicit)

| Allowed after audit complete | Forbidden |
|------------------------------|-----------|
| Add `archive/outcomes/T/D/*` | Edit `data/valuation_model.json` to “fix” FV |
| Rebuild catalog indexes | Delete sessions to hide bad calls |
| Add non-conflicting `meta/` only if missing (backfill) | Overwrite `prediction_snapshot` after outcomes depend on it |
| New session on new date | Scaffold `--force` on non-empty PASS session |

**Amendment protocol:** if a critical data bug is found in an old session, write `meta/errata.md` + outcomes note — do not silent-edit registry numbers. Optionally set `run_manifest.quality_flag = "errata"`.

---

## 13. Schema / check_session extensions

| Artifact | When required |
|----------|----------------|
| `meta/run_manifest.json` | New sessions after Phase A; backfill best-effort |
| `meta/prediction_snapshot.json` | After Phase B for `--full` + complete sessions |
| `archive/catalog/*.json` | After Phase B; checked by check_catalog not check_session |
| Outcomes files | Optional; never block research PASS |

Legacy sessions without `meta/`: check_session **SKIPPED** (same pattern as optional market_context), not FAIL.

---

## 14. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Broken absolute paths inside old handoffs/scripts | Prefer session-relative paths; migrate script rewrites known absolute prefixes if needed |
| Agents still write to root `T/D` | Dual resolve + update prompts; CI/check warns if new root-level ticker dir appears |
| Snapshot diverges from valuation_model | Snapshot builder only; check that FV fields match valuation within epsilon |
| Catalog stale | rebuild_catalog is pure scan; run after every session; weekly rebuild in docs |
| Premature outcomes formulas game the system | Methodology doc; keep grades out of research agents |
| Large `raw_sec` disk | Accept for archive fidelity; later optional cold storage — not in Phase A |
| Git repo size | Consider git-lfs or not tracking `data/raw_sec` — separate decision; layout still holds |

---

## 15. What stays at repo root (harness)

```text
AGENTS.md, harness/, scripts/, templates/, sector_*.md, region_*.md,
*_mcp/, _archive/v1/, .mcp.json
```

Future products (portfolio, monitor) should **not** go under `archive/research/`. Suggested later:

```text
archive/research/     # equity research runs only
archive/outcomes/     # grades for research runs
# later e.g. portfolios/ or archive/portfolio_runs/ — separate plan
```

---

## 16. Success metrics

| Metric | Target |
|--------|--------|
| Ticker folders at repo root | 0 (after M8) |
| Sessions findable via catalog | 100% of dirs under archive/research |
| PASS sessions with prediction_snapshot | 100% new; ≥90% backfill |
| Time to answer “latest META research path” | Open one index file |
| Ability to diff two META runs’ FV/MoS | `compare_runs.py` or manual snapshot diff < 5 min |
| 3m calibration table | Runnable after Phase C once enough calendar time exists |

---

## 17. Suggested implementation order (concrete PRs)

1. **PR1 — Dual path + archive scaffold** (A1–A3, A6 partial): no move; new sessions can land in archive.  
2. **PR2 — Migration** (A4–A5, A7): move all historical sessions; verify.  
3. **PR3 — Snapshot + catalog** (B1–B7).  
4. **PR4 — Outcomes MVP** (C1–C6) when ready to grade.  
5. **PR5 — Compare + AGENTS map shrink** (D1–D3).

Do **not** combine PR2+PR3 with portfolio product work.

---

## 18. Open decisions (resolve before PR2)

| # | Decision | Recommendation |
|---|----------|----------------|
| O1 | Directory name `archive` vs `research_archive` vs `workspace` | **`archive`** — short, intent-clear |
| O2 | Git-track full raw_sec or ignore bulky binaries | Track text; large PDFs optional LFS — decide per disk budget |
| O3 | Same-day re-research suffix | Disallow; next date only until need proven |
| O4 | Snapshot writer: orchestrator agent vs pure script | **Pure script** from session files (hermetic, auditable) |
| O5 | Should FAIL audits enter catalog? | **Yes**, with `audit_verdict: FAIL` — failures are also records |

---

## 19. One-paragraph summary

Move all company research under `archive/research/<TICKER>/<DATE>/` (same internal harness layout), keep harness code at repo root, and add (1) per-run `meta/prediction_snapshot.json` for frozen claims, (2) a rebuildable `archive/catalog/` index, and (3) an append-only `archive/outcomes/` layer to mark realized prices and score whether calls were right — without ever overwriting historical sessions. Migrate existing root tickers with dual-path compatibility, then add comparison and calibration scripts. Portfolio/monitor products stay out of this tree until built.

---

## 20. Related docs

- Normative pipeline: `AGENTS.md` / `Agents.md`  
- Agent templates: `harness/agent_prompts.md`  
- Industry alignment: `harness/research/README.md`, especially `06_implications_for_this_harness.md`  
- This plan supersedes informal chat proposals for multi-product monorepo stubs; empty product folders are **not** required for G1–G4.
