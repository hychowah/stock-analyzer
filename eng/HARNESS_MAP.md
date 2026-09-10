# Eng Harness Map (Mode B)

**Product purpose:** ship analysis UI, programs, and platform over **existing `archive/` data**.  
**Not the goal:** re-run equity research phases for page loads.

Modes, data plane, VERSION, and git: `ARCHITECTURE.md` + `eng/AGENTS.md`. This file is work-type → paths → verify.

## Work type → paths → verify

| Type | Touch | Verify |
|------|-------|--------|
| W1 Research runtime | `packages/kd_research/`, `scripts/` CLIs, `harness/` (incl. `schemas/`, `modules/`) | `pytest packages apps/analysis_web/tests scripts/tests` |
| W2 Platform | `packages/catalog_api/`, export helpers | `test_catalog_api` + live list_runs smoke |
| W3 Programs | `programs/` | CLI on ARCHIVE_ROOT |
| W4 UI | `apps/<name>/` | curl/smoke; fixtures in CI |
| W5 Ops | CI, fixtures, docs | `eng_verify.py` |

## Phase checklist (Mode B sessions)

1. `scaffold_eng_session.py --slug …`  
2. Fill `issue.json` + `feature_list.json`  
3. Baseline `eng_verify.py`  
4. Implement one feature  
5. Verify → flip passes  
6. Ship note  
7. Propose commit (message ready); **commit only after user agreement** (`eng/AGENTS.md` Git discipline)  

**Session start:** progress + feature_list + **recent git log**. W1 VERSION bump: `eng/AGENTS.md` hard constraint 9 (enforced by `eng_verify`).

## Related

- Human architecture map (keep current on architecture-changing commits): `ARCHITECTURE.md`  
- Dual-mode plan audit: session plan §17  
- Research map: `harness/HARNESS_MAP.md`  
- Compare DB: `harness/plan_research_compare_db.md`  

