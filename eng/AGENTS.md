# Mode B — Product Engineering Harness

**Mode:** BUILD (product eng) — not equity research.  
**Data plane:** `archive/` is system of record (read-only for Mode B).  
**This file:** normative for work under `eng/`, `packages/`, `apps/`, `programs/`.

## Purpose

Ship **features, analysis programs, UI, platform APIs, and research-runtime tooling** with mechanical verification. Do **not** run research Phases 0–5 unless explicitly scheduling a black-box research experiment.

## Orientation (every session)

1. Confirm mode = BUILD; cwd is project root.  
2. Read `eng/sessions/<slug>/progress.md` + `feature_list.json` + recent git log.  
3. Pick **one** feature with `passes: false`.  
4. Run `python3 scripts/eng_verify.py` (baseline).  
5. Implement the increment.  
6. Re-verify; only then flip `passes: true` (verifier role).  
7. Update progress; leave mergeable state.

## Work types

| ID | Type | Done means |
|----|------|------------|
| W1 | Research runtime (preflight, prompts, schemas) | pytest + research check_session/preflight tests |
| W2 | Platform / catalog API | tests + rebuild notes |
| W3 | Analysis program | deterministic CLI on archive/fixtures |
| W4 | Product UI | smoke against ARCHIVE_ROOT |
| W5 | Ops / quality | eng_verify green; no archive mutation |

## Hard constraints

1. **`archive/research/**` and `archive/outcomes/**` are immutable** — never rewrite history to make UI/tests green.  
2. **No second app DB of fair values** — read `archive/catalog` projections via `packages/catalog_api`.  
3. **Mode B home is `eng/`** — never use a top-level folder named `build/` (gitignored).  
4. **Do not produce investment FV/MoS judgments** in Mode B.  
5. **Fixtures** live at `eng/fixtures/archive/` (same shape as `archive/`).  
6. **App state** under `apps/<name>/.local/` only.  
7. **W1 changes** must run research unit tests, not only `eng_verify`.  
8. Gen ≠ eval: implementer does not mark `passes: true`.

## Key paths

| Need | Path |
|------|------|
| Map | `eng/HARNESS_MAP.md` |
| Prompts | `eng/agent_prompts.md` |
| Runbook | `eng/runbook.md` |
| Scaffold | `python3 scripts/scaffold_eng_session.py --slug <s>` |
| Verify | `python3 scripts/eng_verify.py` |
| Catalog API | `packages/catalog_api/` |
| Live data | `archive/` (default ARCHIVE_ROOT) |
| Research law | root `AGENTS.md` (Mode A) + `harness/HARNESS_MAP.md` |

## Write allowlist (default)

- `eng/`, `packages/`, `apps/`, `programs/`, `scripts/` (tooling), `templates/`, `harness/` (when W1), `sector_*.md` / `region_*.md` (when W1)  
- **Deny:** `archive/research/**`, `archive/outcomes/**` (completed history)

## Verify

```bash
python3 scripts/eng_verify.py
python3 -m pytest scripts/tests/test_reserved_names.py scripts/tests/test_catalog_api.py -q
```
