# Validation review — street-estimate-bind (claimed harness 2.7.0)

Reviewer: Mode B validation (read-only + tests). No implementation. No git commit. No archive/research or archive/outcomes rewrite. No official AVGO FV invented.

HEAD: `06fd91a` (`Add Phase 1d operating-path evidence before valuation (harness 2.6.0).`)

**Verdict: ALIGNED WITH GAPS**

---

## 1. Mechanical results

| Command | Exit | Notes |
|---------|------|--------|
| `python scripts/eng_verify.py` | **0** | 84 passed, 1 StarletteDeprecationWarning. Structural OK. Immutability policy listed only. VERSION bump OK: `harness/VERSION changed with 10 research-runtime path(s) vs main`. `eng_verify: PASS` |
| `python -m pytest scripts/tests/test_street_bind.py scripts/tests/test_gates_preflight.py scripts/tests/test_agent4_isolation_check.py scripts/tests/test_operating_path_1d.py scripts/tests/test_fdd_hooks_check.py scripts/tests/test_phase_graph.py scripts/tests/test_handoff_structure.py scripts/tests/test_provenance.py -q` | **0** | **74 passed** in 1.01s. No FAIL |
| `python scripts/check_session.py --ticker AVGO --date 2026-08-21 --full` | **0** | **115 passed, 0 failed, 0 warned, 1 skipped**. Skip line: `[SKIPPED] street_bind — legacy/slim (no street_estimates.json; harness_version < 2.7.0)`. Manifest still `harness_version — 2.6.0`. Session exists |

`eng_verify` does **not** treat dirty `archive/catalog/*.json` as a policy violation. `IMMUTABLE_PREFIXES` are only `archive/research/` and `archive/outcomes/`. Catalog dirt is process-only.

---

## 2. Findings table

| Sev | Source | Evidence | Recommended fix (not applied) |
|-----|--------|----------|-------------------------------|
| **major** | eng | Catalog indexes dirty and outside this session’s write_allowlist. `issue.json` allowlist is `eng/`, `scripts/`, `templates/`, `harness/`. `eng/AGENTS.md` data plane: “`archive/` is system of record (read-only for Mode B)”; write deny is `archive/research/**` and `archive/outcomes/**`. `eng/HARNESS_MAP.md`: Mode B “Reads **archive/** read-only”; catalog is “rebuildable”. `eng/runbook.md`: “Mode B must **not** call export with snapshot refresh on live `archive/research`.” Diff vs `06fd91a`: `runs_index.json` 20→42 runs (`updated_at` 2026-08-10T03:03:22Z → 2026-08-21T16:10:10Z), 22 added including `research:AVGO:2026-08-21`; `tickers_index.json` 19→27 tickers. Looks like a live catalog patch/rebuild from later Mode A finalizes, not Street-bind code. | **Exclude all `archive/catalog/*` from a 2.7.0 harness commit.** Catalog refresh is a separate W2/ops change if the user wants it. |
| **major** | eng | Gen ≠ eval / session hygiene contradiction. `eng/AGENTS.md` §8: implementer does not mark `passes: true`; verifier flips after real checks. `eng/agent_prompts.md` Verifier writes `ship_note.json` only then. `feature_list.json`: orient/implement/verify all `passes: false`. `status.json`: `"status": "scaffolded"`, `resume_hint` still “implement the first feature with passes=false”, `updated_at` still scaffold timestamp. `ship_note.json` already claims `eng_verify: PASS` and pytest PASS. Implementer wrote the ship note without flipping features. | Verifier-only: run listed commands (already green), then flip `passes`, set status `complete` or `in_progress`, rewrite `resume_hint`, add `ship_note.verify_commands_run`. |
| **major** | internal consistency | `templates/street_estimates.schema.json` requires `years` with `minItems: 1`, but `unavailable` description says years may be empty. `check_street_fetch` **PASSES** `unavailable=true` with empty `years[]` (`test_street_bind.FetchTests.test_unavailable_ok`). Draft7 validation of that fixture: `[] should be non-empty`. `check_session.py` `FULL_FILES` / `CORE_FILES` do **not** include `registry/street_estimates.json`, so `--full` never schema-validates the Street file (only `check_street_fetch` parse + years). | Either (a) schema: `years.minItems` 0 when `unavailable`, or (b) gate: require a dummy year row. Wire `street_estimates` into `FULL_FILES` (or a dedicated schema check when the file exists), matching FDD. |
| **major** | harness/research + internal | Conservatism stacking and SOTP-DCF 40% are **opt-in**. `street_bind._check_conservatism_dials`: omitted → `SKIPPED`. `_check_sotp_gap`: no `multi_method_reconciliation` → `[]` (no row). `harness/VERSION` and `RESEARCH_AGENTS.md` §10c claim them as 2.7.0 law. Thesis #7: “Mechanical enforcement compounds; prose does not.” Agent 5 can silently stack volume+OM+SBC+WACC in base by omitting `conservatism_dials[]`. | Require `conservatism_dials` (four keys) on new runtime when valuation exists; or FAIL if omitted on ≥2.7.0. For SOTP, FAIL when both methods appear in `model`/`assumptions` without reconciliation — or document as audit-only. |
| **major** | internal consistency | `street_bind.street` is not identity-checked against `street_estimates.json` FY+1. `check_street_bind` uses `bind["street"]` if numeric, else file. Agent 5 can set `street = base` (delta 0) while the file is 20%+ away and skip must-respond. | Identity: if file FY+1 revenue is numeric, `bind.street` must match within `DELTA_EPS` (or require `street_unusable` + hooks). |
| **minor** | internal consistency | `PHASE_ENTRY_OPTIONAL["2_parallel"]` now lists `registry/street_estimates.json` (missing → SKIPPED “optional for legacy”). Agent 5 prompt: “REQUIRED on harness ≥ 2.7.0 unless fetch failure.” 1d analog: `operating_path_brief` is **not** optional; `session_enforces_1d` extra-requires it at 2_parallel entry. Street is dual: OPTIONAL skip **and** `session_enforces_street` → `check_street_fetch` FAIL. `PHASE_PRIMARY_ARTIFACTS["2a"]` still only `data/sp_financials.csv` — phase_status complete-without-artifact will not catch a missing Street file. `HARNESS_MAP.md` phase table 1_parallel “Must produce” still omits `street_estimates.json` (it is in the “If X missing” table and RESEARCH_AGENTS phase table). | Remove Street from `PHASE_ENTRY_OPTIONAL`; extra-require like 1d. Add `registry/street_estimates.json` to `PHASE_PRIMARY_ARTIFACTS["2a"]` (or allow fetch-fail substitute). Add the file to the HARNESS_MAP 1_parallel evidence cell. |
| **minor** | internal consistency | Path-copy is substring needles on `hook.action` only (`used_as:revenue_path`, `used_as:street_mean`, `used_as:consensus`, `used_as:copy_street`). Numeric `base == street` with a 40+ char “independent” rationale PASSES (by design for “landing near Street,” but also allows silent paste). `independent_construction` is not scanned for “consensus.” `keep_independent_vs_street` only needs 40-char `divergence_rationale` — no transmission-mechanism check. | Keep numeric equality allowed; optionally FAIL construction/rationale that matches copy language. Document that paste-without-needle is Agent 13 Band 3 (`4-street`), not machine FAIL. |
| **minor** | internal consistency | Agent 2c “do not duplicate FY+1/+2 tables” and 2d “Street must not enter `latest_quarter.guidance`” are prompt-only. No gate. Guidance-change rule in `RESEARCH_AGENTS.md` §10 is correctly updated (Street ≠ company guidance). | Optional: WARN if `news_sentiment` contains a years[]-shaped revenue table, or if `latest_quarter.guidance` cites `street_estimates`. Audit already covers substance. |
| **minor** | eng | `eng/templates/ship_note.schema.json` required `verify_commands_run` (array). Session `ship_note.json` lacks it → Draft202012 **FAIL**. `status.json` / `feature_list.json` / `issue.json` PASS their schemas. | Add `verify_commands_run` listing the two issue.json commands. |
| **minor** | harness/research (H6/H18) | Scaffold exists; `issue.json` success_criteria filled; one increment. `progress.md` updated. `resume_hint` stale. Status not `in_progress`. Mixed dirty tree (catalog + harness) not noted in progress. | Update `status.json` + `resume_hint` to: “Verifier: catalog files must be restored/unstaged before any 2.7.0 commit; then flip feature_list.” |
| **minor** | eng | Fixtures under `eng/fixtures/archive` were **not** mutated (correct for skip-on-legacy). META fixture `run_manifest` has no `harness_version`; `session_enforces_street` is false. Tests use tempdirs. If someone later stamps fixtures to 2.7.0 without a Street file, `check_session --full` would FAIL. | No fixture update required for this increment. Follow-up if fixtures are re-stamped. |

No **blocker** on the runtime increment itself: tests green, VERSION 2.6.0→2.7.0 in the same changeset, AVGO still PASS with Street SKIPPED, Agent 4 isolation covered, Agent 5 remains single-writer, no archive/research rewrite, no git commit.

---

## 3. Mode B law scores (B.1–B.12)

| # | Item | Score | Evidence |
|---|------|-------|----------|
| 1 | Write allowlist / denylist | **FAIL** (catalog) / **PASS** (research/outcomes) | Allowlist `eng/AGENTS.md`: `eng/`, `packages/`, `apps/`, `programs/`, `scripts/`, `templates/`, `harness/`. Deny `archive/research/**`, `archive/outcomes/**`. Catalog **is** rebuildable (`eng/HARNESS_MAP.md` data plane) but Mode B reads archive read-only; this session’s `issue.json` does not allow `archive/`. No `archive/research` or `archive/outcomes` diffs. |
| 2 | W1 VERSION bump | **PASS** | `harness/VERSION` `"harness_version": "2.7.0"`. `eng_verify` vs main: VERSION changed with 10 runtime paths. |
| 3 | W1 tests | **PASS** | `test_street_bind.py` untracked + run; related gates/isolation tests run; not only `eng_verify`. |
| 4 | Gen ≠ eval | **FAIL** | Features still `false`; `ship_note.json` claims PASS. Implementer must not write a passing ship note. |
| 5 | Session hygiene (H6/H18) | **WARN** | Scaffold + filled `issue.json` + progress Done list. Status `scaffolded`, stale `resume_hint`, premature ship note, mixed dirty tree. |
| 6 | Did not run Mode A 0–5 / invent AVGO FV | **PASS** | No `archive/research` diff. AVGO check_session still 2.6.0 artifacts; no new FV authored. Catalog `updated_at` 2026-08-21 is leftover index patch, not a new research run from this W1 session. |
| 7 | Did not rewrite research/outcomes history | **PASS** | `git status` / `git diff -- archive/research archive/outcomes` clean. |
| 8 | Git discipline | **WARN** | HEAD still `06fd91a` (no commit). Session-end wants a mergeable clean tree (`eng/AGENTS.md` Git discipline). Catalog+harness mixed WIP; progress does not say “leave catalog unstaged.” |
| 9 | Schema vs gates | **WARN** | `street_bind` / `street_hooks` not in valuation_model `required[]` (conditional, like FDD hooks — OK). Gate requires `street_bind` object, `base`, 40-char construction, delta identity, response enum, hooks. Schema `street_bind` does not require those properties. `unavailable` vs `years.minItems` conflict. Street file not in `check_session` CORE/FULL. Stacking/SOTP opt-in. |
| 10 | Agent 4 isolation | **PASS** | `AGENT4_FORBIDDEN_TOKENS` adds `street_estimates`, `street_bind`. `test_agent4_isolation_check.py::test_street_estimates_path_fails_full`. Prompts Agent 4 + audit 2h. |
| 11 | Fixtures | **PASS** | `eng/fixtures/archive` not mutated. Legacy skip path is the right fixture contract. |
| 12 | Session JSON vs `eng/templates/*.schema.json` | **WARN** | `issue.json`, `feature_list.json`, `status.json` PASS. `ship_note.json` FAIL missing `verify_commands_run`. |

---

## 4. harness/research technique map

| Technique | How this change maps | Mismatch |
|-----------|----------------------|----------|
| README thesis #7 mechanical enforcement | Core Street rules live in `scripts/kd_research/street_bind.py` + `gates.py` (`complete_checks` 1_parallel fetch; 2_parallel bind) + `check_session.check_street_bind_session`. Tests in `test_street_bind.py`. | Stacking, SOTP, 2c de-dupe, guidance≠Street, construction-not-copy are still mostly prose. |
| H18 MVH | Map (`HARNESS_MAP` + §10c), task list, progress, init (scaffold), git (no silent commit), fast tests, baseline `eng_verify`. | Task flags not flipped; git tree not merge-clean. |
| H6 orientation | Scaffold present; issue success_criteria filled; one W1 increment. | `resume_hint` / status not advanced after implement. |
| H9 git as memory | VERSION 2.7.0 in the changeset; no unsolicited commit. | Dirty mixed catalog+harness; catalog SHA is not harness memory. |
| C2/C3/C5 Write/Select/Isolate | Dedicated `registry/street_estimates.json` (not dumped into `news_sentiment`). Agent 4 isolated. Agent 5 single-writer. 1d may cite as conflict/hint only. | 2c duplicate tables not gated. |
| Progressive disclosure (H1/H3) | Short map line + “If X missing” row; deep law §10c; operational 4e in Agent 5; Pair 6 exemplar. | Agent 5 4e is a long paragraph; HARNESS_MAP 1_parallel evidence cell not updated. |
| 06_implications specialist quality | Same pattern as 1d / FDD: version floor, dedicated artifact, hooks not-all-`noted_only`, preflight complete/entry, Agent 5 consumes. | Street is also stuffed into `PHASE_ENTRY_OPTIONAL` unlike 1d brief. |
| 04 / 09 single-writer | 2a fetches; 1d_merge non-binding; Agent 5 writes bind. `|delta|>20%` must-respond; never auto `base=street`. | OK. |

---

## 5. 2.7.0 contract walk (law → prompts → schema → gates → tests)

Aligned:

- `RESEARCH_AGENTS.md` §10c + §10 guidance-change + quality-gate row + Agent 5 single-writer paragraph.
- Prompts: 2a write Street; 2c don’t duplicate tables; 2d company guidance only; 1d_rev/merge hint-only; Agent 4 forbid; Agent 5 4e independent-then-calibrate; Agent 13 `4-street`.
- `session_enforces_street` is analogous to `session_enforces_1d` (file present **or** semver ≥ floor).
- Legacy SKIPPED proven on AVGO 2026-08-21 (`2.6.0`).
- New runtime missing file FAILs (`test_new_runtime_enforces`); fetch-log failure PASSes fetch; `|delta|>20%` without response FAILs; copy action FAILs; all-`noted_only` FAILs; 1_parallel complete includes Street.

Mismatches:

- Prompts require Street on ≥2.7.0; `PHASE_ENTRY_OPTIONAL` still SKIPPED-optional at 2_parallel entry (FAIL still arrives via `check_street_fetch` when `session_enforces_street`).
- Schema `unavailable` empty years vs gate PASS.
- Schema does not jsonschema-validate Street in `check_session`.
- Gates do not FAIL numeric copy if hooks say `used_as:calibration_check`.
- Conservatism/SOTP implemented only if fields present (schema comments + optional code), not as required 2.7.0 artifacts.
- `PATH_COPY_NEEDLES` vs prompt `action` values: prompt forbids `used_as:revenue_path` / `used_as:street_mean`; needles also include `used_as:consensus` / `used_as:copy_street`. Test uses `used_as:revenue_path_base` (substring hit). `used_as:calibration_check` and `rejected` are the allowed prompt actions — not enum-enforced on hooks (only copy needles + not-all-noted_only).
- Agent 2c still *allowed* by machine to duplicate FY tables.
- Guidance-change cannot treat Street as company guidance **in law/prompts**; no machine check on `latest_quarter.guidance`.

---

## 6. What already aligns

- W1 runtime + tests + `harness/VERSION` 2.7.0 in one changeset; `eng_verify` version gate green.
- Mechanical Street fetch/bind/hooks, not prompt-only for the core calibration contract.
- Agent 5 remains single-writer; 2a is fetcher not a parallel valuer; harness never sets `base = street`.
- Agent 4 isolation tokens + test.
- Legacy sessions SKIPPED; live AVGO `--full` still PASS.
- Dedicated artifact (`street_estimates.json`) + valuation `street_bind` / `street_hooks` (Write/Select, FDD/1d-style).
- Progressive disclosure: map + §10c + prompts + Pair 6 exemplar.
- No `archive/research` / `archive/outcomes` rewrite; no git commit; no invented FV.
- `eng/fixtures/archive` untouched.

---

## 7. Session hygiene contradictions

- `feature_list.json` all `passes: false` **vs** `ship_note.json` verify PASS.
- `status.json` `"scaffolded"` + stale `resume_hint` **vs** `progress.md` “Done” list including VERSION and tests.
- `ship_note.json` missing schema-required `verify_commands_run`.
- Catalog dirt not mentioned in `progress.md` / `resume_hint` despite session-end “clean tree or note WIP.”
- Implementer wrote `ship_note.json` (verifier role).

---

## 8. Catalog dirty files — exclude from a 2.7.0 commit

**Yes. Exclude `archive/catalog/runs_index.json`, `archive/catalog/tickers_index.json`, and `archive/catalog/schema_version`.**

- `schema_version`: CRLF-only (`HEAD` `b'2\n'` vs worktree `b'2\r\n'`).
- Indexes: 22 added runs / 8 added tickers / 8 changed ticker records; `updated_at` 2026-08-21T16:10:10Z. Rebuild/patch of live archive, not a Street schema change. Unrelated to harness 2.7.0. Mixing it would violate this session’s allowlist and Mode B read-only data plane, and would ship a catalog bump in a research-runtime commit.

Suggested commit set (when the user agrees): `harness/**` (incl. VERSION 2.7.0), `scripts/kd_research/street_bind.py`, `scripts/kd_research/gates.py`, `scripts/check_session.py`, `scripts/tests/test_street_bind.py`, `scripts/tests/test_agent4_isolation_check.py`, `templates/street_estimates.schema.json`, `templates/valuation_model.schema.json`, `eng/sessions/2026-08-22-street-estimate-bind/` — after verifier hygiene fixes. Restore catalog files to HEAD (or leave unstaged).
