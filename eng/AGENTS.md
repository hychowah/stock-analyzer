# Mode B — Product Engineering Harness

**Mode:** BUILD (product eng) — not equity research.  
**Data plane:** `archive/` is system of record (read-only for Mode B).  
**This file:** normative for work under `eng/`, `packages/`, `apps/`, `programs/`.

## Purpose

Ship **features, analysis programs, UI, platform APIs, and research-runtime tooling** with mechanical verification. Do **not** run research Phases 0–5 unless explicitly scheduling a black-box research experiment.

## Orientation (every session)

1. Confirm mode = BUILD; cwd is project root.  
2. Read `eng/sessions/<slug>/progress.md` + `feature_list.json` + **recent git log**.  
3. Pick **one** feature with `passes: false`.  
4. Run `python3 scripts/eng_verify.py` (baseline).  
5. Implement the increment.  
6. Re-verify; only then flip `passes: true` (verifier role).  
7. Update `progress.md`; leave a mergeable clean tree. **Do not `git commit` until the user explicitly agrees** (see Git discipline).

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
9. **Mode A version on W1 ship:** if the change set touches Mode A research-runtime paths (`harness/` except advisory `harness/research/`, `scripts/kd_research/`, research scripts, `templates/`, root `sector_*.md` / `region_*.md`), you **must bump** `harness/VERSION` → `harness_version` (semver) in the **same** change set before marking complete. `eng_verify` enforces this vs `main`. UI/catalog-only (W2–W4) work does **not** bump Mode A version.  
10. **No commit without user agreement:** never run `git commit`, `git push`, amend, or force-push unless the user has **explicitly** asked or approved in this conversation (e.g. “commit”, “yes commit that”). Preparing a message or staging when asked is fine; silent commits are forbidden.  
11. **Refactor when it pays — do not fear it.** Agentic coding makes refactors cheap; duplication, leaky workarounds, and unscalable structure are what compound. If a cleaner shape has clear long-term benefit (one home for a fact, a boundary that will scale, deleting a workaround), **do that refactor** rather than a local patch — even if the user only named the feature. Do **not** skip it to keep the diff small. Guardrails: write allowlist only; never rewrite `archive/research/**` or `archive/outcomes/**`; leave **one coherent, verify-green increment** (a large boundary move may be its own `feature_list` item, not a half-finished rewrite). Record what you refactored and why in `progress.md`.

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
| Research law (Mode A) | `harness/RESEARCH_AGENTS.md` + `harness/HARNESS_MAP.md` (root `AGENTS.md` = router) |

## Write allowlist (default)

- `eng/`, `packages/`, `apps/`, `programs/`, `scripts/` (tooling), `templates/`, `harness/` (when W1), `sector_*.md` / `region_*.md` (when W1)  
- **Deny:** `archive/research/**`, `archive/outcomes/**` (completed history)

## Verify

```bash
python3 scripts/eng_verify.py
python3 -m pytest scripts/tests/test_reserved_names.py scripts/tests/test_catalog_api.py scripts/tests/test_provenance.py -q
```

Mode A identity source of truth: **`harness/VERSION`** (stamped into every research `run_manifest` / snapshot + git SHA).

## Git discipline (Mode B)

Aligned with `harness/research/` **H9** (git as memory & recovery) — kept light; not Conventional Commits.

### Hard rule: user agreement before commit

| Allowed without asking | Requires explicit user agreement |
|------------------------|----------------------------------|
| `git status` / `git diff` / `git log` | `git commit` |
| Edit files, run tests, update `progress.md` | `git push` / force-push |
| Propose a commit message in chat | `git commit --amend` on published history |
| `git add` only when user asked to commit | Any rewrite of shared history |

**Explicit agreement** means a clear user turn such as: “commit”, “commit the changes”, “yes commit that”, “ship it to git”.  
**Not** agreement: silence, “looks good”, “continue”, “next”, or finishing a feature list item.

If ready to commit: summarize what will be committed and **ask**; only then run `git commit`.

| Rule | Detail |
|------|--------|
| **When (after agreement)** | After each **verified** feature/increment. |
| **Gate first** | `eng_verify` (and listed verify_commands) green **before** commit when claiming the feature done. |
| **Message** | One descriptive subject: **what changed + why**. Optional body for risks / follow-ups. |
| **W1** | Same commit (or same change set before ship) must include the `harness/VERSION` bump when research-runtime paths change. |
| **Do not** | Commit broken `eng_verify`, secrets, or rewrites of completed `archive/research/**` / `archive/outcomes/**` to green tests. |
| **Session end** | Clean tree preferred. If WIP must remain, note it in `progress.md` + `status.resume_hint` — still **no** unsolicited commit. |
| **Recovery** | Prefer reset/revert to last good commit only with user agreement (destructive). |

Industry context (advisory): `harness/research/01_harness_engineering.md` §3, `08_technique_catalog.md` H6/H9/H18.
