# Wave 4 plan — destock default (harness 2.12.0)

Persona pack item 1. Tightens Wave 3 E1; does not replace it.

## Goal

Stop the harness from **teaching** destock as the bear case and printed-guide duration as base. Default: destock/quality-reset is **base** until sell-through, cash, and channel prove demand. Duration lives in **bull**, or the action is `pass`/`too_hard`.

## Why (investing)

A destock year looks like a good business (inventory down, FCF up, guide “duration”). Capitalizing that as Y1–Y8 is sell-in, not demand. Wave 3 only FAILs when the conflict is left `unresolved` and duration sits in base. Escape hatches: mark `resolved`, follow Pair 0 GOOD (destock in bear), 4e requiring the printed guide in base.

## Alignment constraints

- `eng/AGENTS.md`: W1; write allowlist `harness/` + `scripts/` + `templates/`; no archive mutation; bump `harness/VERSION` in the same change set; refactor when it pays; implementer does not flip `passes`.
- `harness/research/`: decision-grade next-phase, not token thrift; one home for a fact (destock default lives in 1d_merge + Pair 0 + Agent 5 4d/4e + the gate — they must agree).
- Agent 5 remains single-writer. No second valuer.
- **Do not fight** `check_destock_not_silent_duration` (2.11.0). Tighten toward destock-in-base / pass. **Do not re-legalize destock-only-in-bear.**
- Machine-gate synthetic JSON outcomes; prompt-only where a gate would be NLP theater. Prefer a small checker.
- Isolation: no browsing `archive/research/` for priors.

## Prompt / law (one home)

1. **`harness/agent_prompts.md` — `1d_merge`:** Cut `propose destock-fade in bear, duration/company-guide in base/bull`. Replace: if destock and duration are both evidenced, `status=unresolved`; default hint destock/quality-reset **in base**, duration **only in bull**; resolving toward duration requires sourced sell-through/RPO, DSO/inventory not destock-math, CFO–NI not WC-release disguise. Still non-binding numbers; Agent 5 decides; do not average.
2. **`harness/exemplars/hooks_quality.md` Pair 0:** Current GOOD (`Y1–Y2 keep printed duration; destock analog lives in bear only`) becomes **BAD — Wave 3/4 FAIL**. New GOOD: destock/quality-reset on the **base** path; duration only in bull; unresolved → `pass`/`too_hard` or destock-in-base.
3. **Agent 5 4d vs 4e:** If flatten-vs-destock is unresolved **or** destock is the live conflict, **4d wins 4e**. Printed EX-99.1 guide may sit in bull/range, not silent base duration. Exiling a destock/cash-quality guide from base is **not** a skill miss. Keep: do not average; destock-in-base **or** DU=low **or** pass/too_hard.
4. **Agent 13 Band 3:** Destock-in-bear + duration-in-base is major even if labeled `resolved`. Do **not** major “degraded transcripts that exile a printed outlook from base” on destock/cash-quality names.
5. **`RESEARCH_AGENTS.md` §10 two-quarter + §13:** Destock inverse (FCF up from WC release + inventory down + guide/revenue up) cannot raise Y1 (`bear_only` or reject). Add ≥2.12.0 gate row. Keep stuffing WARN from 2.11.0; destock inverse is the new check.
6. **`HARNESS_MAP.md` / `VERSION`:** 2.12.0 destock-default.

## Gates (version-gated ≥ 2.12.0; legacy SKIPPED)

Keep `check_destock_not_silent_duration` as-is for ≥2.11.0.

Add `check_destock_default` (2.12.0+):

- If a destock conflict exists (`unresolved` **or** `resolved`) in `operating_path_brief.conflicts[]`:
  - Legal (same set as E1): destock encoded in **base** hooks, **or** `decision_usefulness=low`, **or** `duration.action` in `pass`/`too_hard`.
  - **FAIL** destock-only-in-bear (hooks `applies_in`/`action` bear) unless one of those legal exits. Do **not** require `initiate`/`add` — `hold`/`trim`/`sell` with destock-in-bear is the same escape.
- If `scenario_hints` / `recommended_for_agent5` teach destock-in-bear + duration-in-base (phrases: destock-fade in bear, destock analog lives in bear) without destock-in-base: FAIL.
- Do **not** mutate `_unresolved_destock`. Resolved-toward-duration with no destock-in-bear hook is prompt/audit (sell-through), not a blanket FAIL.
- Two-quarter destock inverse **only when a destock conflict exists**: `two_quarter_rule` raise while FCF ≥ 0 and inventory/AR **down** (WC release) → WARN. Raise + destock conflict + missing FCF/WC → WARN. Do not reuse `_wc_deteriorating` (that helper is inventory **up**). Do not expand E3 globally.

Prompt-file tests (not NLP on live sessions): `1d_merge` template must not contain the old destock-in-bear hint; Pair 0 GOOD `new` must not be destock-in-bear-only.

## Files

- `harness/agent_prompts.md`, `harness/RESEARCH_AGENTS.md`, `harness/HARNESS_MAP.md`, `harness/VERSION`
- `harness/exemplars/hooks_quality.md`
- `scripts/kd_research/epistemology.py` (extend; do not fork a parallel destock story)
- `scripts/check_session.py` (wire 2.12)
- `scripts/tests/test_wave4_destock_default.py` (+ keep `test_wave3_epistemology.py` green)
- `eng/eval/failure_catalog.md` if a new F-id is warranted
- This plan + alignment note

## Non-goals

- Full cash_quality schema (Wave 7 gather).
- Decision reopen after 2.5 (Wave 6).
- Blocking `initiate` solely because `cheap_claim ≠ franchise_mos`.
- Archive rewrites; mandate pack.

## Refactor note

One destock story in `epistemology.py`: Wave 3 function stays; Wave 4 adds a stricter wrapper/check for ≥2.12.0 rather than a second module that reimplements blob matching.
