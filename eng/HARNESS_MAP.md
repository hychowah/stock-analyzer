# Eng Harness Map (Mode B)

**Product purpose:** ship analysis UI, programs, and platform over **existing `archive/` data**.  
**Not the goal:** re-run equity research phases for page loads.

## Modes

| Mode | Entry | Writes | Reads |
|------|-------|--------|-------|
| A Research | root `AGENTS.md` + research pipeline | new `archive/research/<T>/<D>/` | sources, MCP |
| B Build | `eng/AGENTS.md` | eng/packages/apps/programs/scripts | **archive/** read-only |

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
  research/   # SoR sessions
  outcomes/   # marks
  catalog/    # sqlite + indexes (rebuildable)
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

## Related

- Dual-mode plan audit: session plan §17  
- Research map: `harness/HARNESS_MAP.md`  
- Compare DB: `harness/plan_research_compare_db.md`  
