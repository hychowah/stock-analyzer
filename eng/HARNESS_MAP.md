# Eng Harness Map (Mode B)

**Product purpose:** ship analysis UI, programs, and platform over **existing `archive/` data**.  
**Not the goal:** re-run equity research phases for page loads.

## Modes

| Mode | Entry | Writes | Reads |
|------|-------|--------|-------|
| A Research | root `AGENTS.md` + research pipeline | new `archive/research/<T>/<D>/` | sources, MCP |
| B Build | `eng/AGENTS.md` | eng/packages/apps/programs/scripts; append `archive/library/`, `archive/comparisons/`, `archive/research_jobs/`; may create a new empty research session via Analyze initializer | immutable completed `archive/research` + `archive/outcomes`; catalog; library corpus |

## Work type → paths → verify

| Type | Touch | Verify |
|------|-------|--------|
| W1 Research runtime | `scripts/`, `templates/`, `harness/`, sector modules | `pytest scripts/tests` + preflight/check helpers |
| W2 Platform | `packages/catalog_api/`, export helpers | `test_catalog_api` + live list_runs smoke |
| W3 Programs | `programs/` | CLI on ARCHIVE_ROOT |
| W4 UI | `apps/<name>/` | curl/smoke; fixtures in CI |
| W5 Ops | CI, fixtures, docs | `eng_verify.py` |

## Data plane (do not invent another)

```text
archive/
  research/      # SoR sessions (immutable)
  outcomes/      # marks (immutable)
  catalog/       # sqlite + indexes (rebuildable)
  library/       # reusable primary documents (append-only)
  comparisons/   # session-valuation-audit packets (append-only)
  research_jobs/ # Analyze control plane (append-only; not a catalog source)
```

Default: `ARCHIVE_ROOT=<project>/archive`.  
CI: `eng/fixtures/archive` (same shape).

## Catalog API (summary)

- `CatalogApi(archive_root, readonly=True)`  
- Primary identity: `run_id = research:{TICKER}:{session_key}`  
- Query surface: **sqlite**; JSON indexes secondary  
- `open_artifact`: run_id + allowlist + path containment  

## Phase checklist (Mode B sessions)

1. `scaffold_eng_session.py --slug …`  
2. Fill `issue.json` + `feature_list.json`  
3. Baseline `eng_verify.py`  
4. Implement one feature  
5. Verify → flip passes  
6. Ship note  
7. Propose commit (message ready); **commit only after user agreement** (`eng/AGENTS.md` Git discipline)  

**Session start:** progress + feature_list + **recent git log**.

## Mode A version (W1 only)

| Item | Path / rule |
|------|-------------|
| Source of truth | `harness/VERSION` (`harness_version` semver + `harness_spec`) |
| Exact tree | `harness_git_sha` stamped at Mode A scaffold/finalize |
| When to bump | Research-runtime paths change (phases, schemas, gates, prompts, sector/region law, research scripts) |
| When **not** to bump | Pure UI, catalog API display, programs over existing archive |
| Gate | `python3 scripts/eng_verify.py` fails if runtime paths changed vs `main` without `harness/VERSION` in the diff |

## Related

- Dual-mode plan audit: session plan §17  
- Research map: `harness/HARNESS_MAP.md`  
- Compare DB: `harness/plan_research_compare_db.md`  

